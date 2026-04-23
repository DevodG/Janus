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

router = APIRouter(tags=["scam-guardian"])

@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_scam(request: AnalyzeRequest):
    # 1. Normalize Input
    processed = await input_processor.process(request)
    
    # 2. Extract Intent
    intent = await intent_service.detect(processed["text"])
    
    # 3. Extract Entities
    entities = await entity_service.extract(processed["text"])
    
    # 4. Memory & Similarity
    embedding = await similarity_service.get_embedding(processed["text"])
    matches = await similarity_service.find_matches(embedding)
    
    # 5. Risk Scoring & Decisions
    risk_result = await risk_service.score(processed, intent, entities)
    
    response = AnalyzeResponse(
        id=str(uuid.uuid4()),
        text=processed["text"],
        source=processed["source"],
        risk_score=risk_result["score"],
        decision=risk_result["decision"],
        reasons=risk_result["reasons"],
        intent=intent,
        entities=entities,
        similarity={"matches": matches} if matches else None
    )
    
    # 6. Persist to DB (Background or async)
    await memory_service.save_event(response, processed["metadata"], embedding)
    
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
