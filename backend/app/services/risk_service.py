import re
from typing import Dict, Any, List
from app.schemas.response import IntentScore, ExtractedEntities

from app.services.scam_graph import scam_graph
from app.services.market_watcher import MarketWatcher

# Assuming a global instance exists or create a light one for lookup
market_watcher = MarketWatcher()

class RiskService:
    async def score(self, processed: Dict[str, Any], intent: IntentScore, entities: ExtractedEntities) -> Dict[str, Any]:
        risk_score = 0
        reasons = []

        # 1. Intent Rules (Base Heuristics)
        risk_score += intent.urgency * 40
        risk_score += intent.impersonation * 40
        risk_score += intent.payment * 30
        
        if intent.urgency > 0.6: 
            risk_score += 20
            reasons.append("Aggressive urgency detected (Psychological Trigger)")
        if intent.impersonation > 0.6: 
            risk_score += 25
            reasons.append("Possible high-authority impersonation detected")
        if intent.fear > 0.6:
            risk_score += 20
            reasons.append("Fear-based manipulation detected (Coercive Trigger)")

        # 2. Entity Rules (Depth: Cross-Entity Matching)
        if entities.upi_ids and entities.domains:
            risk_score += 30
            reasons.append("Suspicious combination of Payment ID and External Link")
            
        if entities.phones and intent.payment > 0.5:
            risk_score += 20
            reasons.append("Payment request associated with an unverified phone number")

        # 3. Depth: Scam Journey Graph Integration
        # Convert entities to the format expected by scam_graph
        graph_entities = {
            "phones": entities.phones,
            "upi_ids": entities.upi_ids,
            "links": entities.domains
        }
        journey_report = scam_graph.get_journey_score(graph_entities)
        
        if journey_report["score"] > 0:
            risk_score += journey_report["score"]
            reasons.append(f"Linked Journey Found: {journey_report['event_count']} previous events involving these entities")
            if "BLOCKED" in journey_report["status"]:
                risk_score = max(risk_score, 100)
                reasons.append("Entities are associated with a PREVIOUSLY BLOCKED scam journey")

        # 4. Depth: MMSA Dissonance (If multimodal metadata present)
        # Assuming metadata might contain dissonance info if processed by deeper sensors
        dissonance = processed.get("metadata", {}).get("mmsa", {}).get("dissonance_score", 0)
        if dissonance > 0.5:
            risk_score += (dissonance * 40)
            reasons.append("Emotional Dissonance: Content conflicts with emotional tone")

        # 5. Optimization: Market & Brand Factual Dissonance
        for brand in entities.brands:
            # Brand-Domain Mismatch (ZeroTrust Core)
            if entities.domains:
                brand_lower = brand.lower()
                for domain in entities.domains:
                    domain_lower = domain.lower()
                    # If brand mentioned but domain doesn't match official brand domain
                    # Very simple check for now
                    if brand_lower in ["sbi", "hdfc", "icici", "axis", "paytm", "amazon", "flipkart"]:
                        if brand_lower not in domain_lower:
                            risk_score += 40
                            reasons.append(f"Brand Mismatch: Claimed brand '{brand}' does not match link destination '{domain}'")

            status = market_watcher.get_watchlist_status()
            match = next((s for s in status if s["symbol"] == brand.upper()), None)
            if match and match["price"]:
                # If the content mentions a price (naive regex check)
                prices_in_text = re.findall(r'\$\d+', processed["text"])
                for p in prices_in_text:
                    p_val = float(p.replace('$', ''))
                    if abs(p_val - match["price"]) / match["price"] > 0.5:
                        risk_score += 30
                        reasons.append(f"Factual Dissonance: Claimed price for {brand} (${p_val}) deviates significantly from market (${match['price']})")

        # Final normalization
        final_score = min(risk_score, 100)
        
        decision = "ALLOW"
        if final_score >= 85:
            decision = "BLOCK"
        elif final_score >= 50:
            decision = "WARN"

        return {
            "score": final_score,
            "decision": decision,
            "reasons": reasons,
            "journey": journey_report
        }

risk_service = RiskService()
