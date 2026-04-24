from datetime import datetime
import uuid
from fastapi import APIRouter, Depends, HTTPException
from app.schemas.request import AnalyzeRequest
from app.schemas.response import AnalyzeResponse, IntentScore, ExtractedEntities
from app.services.input_processor import input_processor
from app.services.intent_service import intent_service
from app.services.entity_service import entity_service
from app.services.risk_service import risk_service
from app.services.similarity_service import similarity_service
from app.services.memory_service import memory_service

from app.services.live_intel_service import live_intel_service

router = APIRouter(tags=["scam-guardian"])

def _decision_from_risk(risk: float) -> str:
    if risk >= 85:
        return "BLOCK"
    if risk >= 50:
        return "WARN"
    return "ALLOW"

@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_scam(request: AnalyzeRequest):
    # 1. Normalize Input
    processed = await input_processor.process(request)
    
    # 2. Extract Intent
    intent = await intent_service.detect(processed["text"])
    
    # 3. Extract Entities
    entities = await entity_service.extract(processed["text"])
    
    # 4. Memory & Similarity (Optional/Resilient)
    matches = []
    embedding = None
    try:
        embedding = await similarity_service.get_embedding(processed["text"])
        matches = await similarity_service.find_matches(embedding)
    except Exception as e:
        print(f"Similarity search failed: {e}")
    
    # 5. Risk Scoring & Decisions
    risk_result = await risk_service.score(processed, intent, entities)
    
    # 6. Live Evidence (Hackathon Upgrade)
    live_intel = await live_intel_service.analyze(
        urls=entities.domains, # Assuming extraction gives raw domains/urls
        domains=entities.domains,
        brands=entities.brands
    )
    
    # Check for infrastructure overlap in memory graph
    try:
        memory_overlaps = await memory_service.check_overlap(
            entities.phones, entities.upi_ids, entities.domains
        )
        if memory_overlaps:
            live_intel["evidence"].extend(memory_overlaps)
            live_intel["risk_boost"] = min(60, live_intel["risk_boost"] + 30)
            live_intel["reasons"].append("Detected reuse of known scam infrastructure.")
            live_intel["breadcrumbs"].append("Infrastructure REUSE detected via Janus Graph!")
    except Exception as e:
        print(f"Memory overlap check failed: {e}")
    
    final_risk = min(100.0, float(risk_result["score"]) + float(live_intel["risk_boost"]))
    final_reasons = list(dict.fromkeys([*risk_result["reasons"], *live_intel["reasons"]]))
    final_decision = _decision_from_risk(final_risk)

    # 5. Generate Depth Synthesis (AI summary of flags)
    synthesis = f"Investigation found {len(live_intel.get('evidence', []))} forensic markers. "
    if final_risk > 70:
        synthesis += f"High-confidence {final_decision} suggested due to {final_reasons[0] if final_reasons else 'critical risk tokens'}. "
    if live_intel.get("claimed_brand"):
        synthesis += f"Active impersonation of {live_intel.get('claimed_brand')} detected. "
    if memory_overlaps:
        synthesis += "Recidivism detected: Infrastructure reuse across multiple reports."

    response = AnalyzeResponse(
        id=str(uuid.uuid4()),
        text=processed["text"],
        source=processed["source"],
        risk_score=final_risk,
        decision=final_decision,
        reasons=final_reasons,
        intent=intent,
        entities=entities,
        verdict_synthesis=synthesis,
        evidence=live_intel.get("evidence", []),
        claimed_brand=live_intel.get("claimed_brand"),
        official_verify=live_intel.get("official_verify"),
        next_steps=live_intel.get("next_steps", []),
        breadcrumbs=live_intel.get("breadcrumbs", []),
        similarity={"matches": matches} if matches else {"matches": []}
    )
    
    # 6. Persist to DB (Fail-safe)
    try:
        await memory_service.save_event(response, processed["metadata"], embedding)
    except Exception as e:
        print(f"Event persistence failed: {e}. Using JSON fallback.")
        try:
            from app.services.fallback_store import append_event
            # Enhance response with timestamp for history display
            data = response.dict()
            data["created_at"] = datetime.utcnow().isoformat()
            append_event(data)
        except Exception as fe:
            print(f"Fallback storage also failed: {fe}")
    
    # 7. Real-time Broadcast (Optimization for live demo)
    try:
        from app.routers.websocket import manager as ws_manager
        await ws_manager.broadcast({
            "type": "NEW_SCAM_EVENT",
            "event_id": response.id,
            "source": response.source,
            "risk_score": response.risk_score,
            "decision": response.decision,
            "reasons": response.reasons
        })
    except Exception:
        pass # Don't fail the primary request if broadcast fails
    
    return response
