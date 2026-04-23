"""
ZeroTrust Guardian Interceptor — Active intervention layer for Janus.
Monitors the signal queue and proactively squashes or alerts on scam journeys.
"""

import logging
from typing import List, Dict, Any, Tuple
from app.services.guardian_sensory import guardian_sensory
from app.services.scam_graph import scam_graph

logger = logging.getLogger(__name__)

class GuardianInterceptor:
    def __init__(self, intervention_threshold: float = 70.0):
        self.guardian = guardian_sensory
        self.scam_memory = scam_graph
        self.intervention_threshold = intervention_threshold
        self.active_interventions = []

    def process_signals(self, signals: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Intercept and audit a batch of signals.
        Returns (CleanedSignals, Interventions).
        """
        clean_signals = []
        interventions = []

        for signal in signals:
            risk_report = self._audit_signal(signal)
            
            if risk_report["score"] >= self.intervention_threshold:
                # ACTIVE INTERVENTION: Squash the signal and create an alert
                logger.warning(f"[GUARDIAN-INTERCEPTOR] INTERVENING on signal: {signal.get('headline', 'Untitled')}")
                intervention_event = {
                    "type": "GUARDIAN_INTERVENTION",
                    "original_signal": signal,
                    "risk_report": risk_report,
                    "action": "BLOCKED",
                    "reason": risk_report["reasons"][0] if risk_report["reasons"] else "High-risk scam journey detected."
                }
                interventions.append(intervention_event)
                self.active_interventions.append(intervention_event)
            else:
                clean_signals.append(signal)

        return clean_signals, interventions

    def _audit_signal(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        """Deep audit of a single signal for scam markers."""
        text = signal.get("headline", "") + " " + signal.get("summary", "") + " " + signal.get("content", "")
        url = signal.get("url", "")
        
        # 1. URL Analysis
        url_report = {"risk_score": 0, "reasons": []}
        if url:
            url_report = self.guardian.analyze_url(url)
            
        # 2. Intent Analysis
        intent_signals = self.guardian._detect_signals(text)
        entities = self.guardian._extract_entities(text)
        
        # 3. Graph Retrieval (Journey Score)
        journey_report = self.scam_memory.get_journey_score(entities)
        
        # 4. Global Fusion
        final_score = max(url_report["risk_score"], journey_report["score"])
        # Cross-channel escalation
        if url_report["risk_score"] > 30 and journey_report["event_count"] > 0:
            final_score = min(100, final_score + 25)
            
        # Record the observation in the graph autonomously
        if intent_signals or entities.get("links") or entities.get("phones"):
            self.scam_memory.add_event(f"daemon_{signal.get('source', 'unknown')}", entities, intent_signals)

        return {
            "score": final_score,
            "reasons": url_report.get("reasons", []) + journey_report.get("channels", []),
            "journey": journey_report,
            "intent": intent_signals
        }

guardian_interceptor = GuardianInterceptor()
