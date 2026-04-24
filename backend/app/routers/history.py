import uuid
from fastapi import APIRouter, Depends, HTTPException
from typing import List
from sqlalchemy import select, desc
from app.schemas.response import AnalyzeResponse, IntentScore, ExtractedEntities
from app.db.session import AsyncSessionLocal
from app.db.models import ScamEvent

router = APIRouter(tags=["scam-guardian"])

@router.get("/history", response_model=List[AnalyzeResponse])
async def get_scam_history(limit: int = 50):
    """Retrieve recent scam analysis events."""
    from app.core.runtime_state import runtime_state
    from app.services.fallback_store import list_events

    if not runtime_state.db_ready:
        return list_events()

    async with AsyncSessionLocal() as session:
        try:
            stmt = select(ScamEvent).order_by(desc(ScamEvent.created_at)).limit(limit)
            result = await session.execute(stmt)
            events = result.scalars().all()
            
            return [
                AnalyzeResponse(
                    id=str(event.id),
                    text=event.text,
                    source=event.source,
                    risk_score=event.risk_score,
                    decision=event.decision,
                    reasons=event.event_metadata.get("reasons", []),
                    intent=IntentScore(**event.event_metadata.get("intent", {})),
                    entities=ExtractedEntities(**event.event_metadata.get("entities", {})),
                    evidence=event.event_metadata.get("live_intel", {}).get("evidence", []) if "live_intel" in event.event_metadata else [],
                    claimed_brand=event.event_metadata.get("live_intel", {}).get("claimed_brand") if "live_intel" in event.event_metadata else None,
                    official_verify=event.event_metadata.get("live_intel", {}).get("official_verify") if "live_intel" in event.event_metadata else None,
                    next_steps=event.event_metadata.get("live_intel", {}).get("next_steps", []) if "live_intel" in event.event_metadata else [],
                    verdict_synthesis=event.event_metadata.get("live_intel", {}).get("verdict_synthesis") if "live_intel" in event.event_metadata else None,
                    breadcrumbs=event.event_metadata.get("live_intel", {}).get("breadcrumbs", []) if "live_intel" in event.event_metadata else [],
                    similarity=event.event_metadata.get("live_intel", {}).get("similarity") if "live_intel" in event.event_metadata else None
                ) for event in events
            ]
        except Exception as e:
            # Fallback on exception too
            return list_events()

@router.get("/history/{event_id}", response_model=AnalyzeResponse)
async def get_event_detail(event_id: str):
    """Retrieve detailed information for a specific scam event."""
    from app.core.runtime_state import runtime_state
    from app.services.fallback_store import get_event

    if not runtime_state.db_ready:
        item = get_event(event_id)
        if not item:
            raise HTTPException(status_code=404, detail="Event not found in fallback")
        return item

    async with AsyncSessionLocal() as session:
        try:
            event_uuid = uuid.UUID(event_id)
            stmt = select(ScamEvent).where(ScamEvent.id == event_uuid)
            result = await session.execute(stmt)
            event = result.scalar_one_or_none()
            
            if not event:
                item = get_event(event_id)
                if not item:
                    raise HTTPException(status_code=404, detail="Event not found")
                return item
            
            return AnalyzeResponse(
                id=str(event.id),
                text=event.text,
                source=event.source,
                risk_score=event.risk_score,
                decision=event.decision,
                reasons=event.event_metadata.get("reasons", []),
                intent=IntentScore(**event.event_metadata.get("intent", {})),
                entities=ExtractedEntities(**event.event_metadata.get("entities", {})),
                evidence=event.event_metadata.get("live_intel", {}).get("evidence", []) if "live_intel" in event.event_metadata else [],
                claimed_brand=event.event_metadata.get("live_intel", {}).get("claimed_brand") if "live_intel" in event.event_metadata else None,
                official_verify=event.event_metadata.get("live_intel", {}).get("official_verify") if "live_intel" in event.event_metadata else None,
                next_steps=event.event_metadata.get("live_intel", {}).get("next_steps", []) if "live_intel" in event.event_metadata else [],
                verdict_synthesis=event.event_metadata.get("live_intel", {}).get("verdict_synthesis") if "live_intel" in event.event_metadata else None,
                breadcrumbs=event.event_metadata.get("live_intel", {}).get("breadcrumbs", []) if "live_intel" in event.event_metadata else [],
                similarity=event.event_metadata.get("live_intel", {}).get("similarity") if "live_intel" in event.event_metadata else None
            )
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid event ID format")
        except Exception as e:
            item = get_event(event_id)
            if item: return item
            raise HTTPException(status_code=500, detail=f"Error retrieving event: {str(e)}")
