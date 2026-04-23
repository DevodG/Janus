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
                    reasons=event.metadata.get("reasons", []),
                    intent=IntentScore(**event.metadata.get("intent", {})),
                    entities=ExtractedEntities(**event.metadata.get("entities", {})),
                    # timestamp=event.created_at # Add if AnalyzeResponse schema supports it
                ) for event in events
            ]
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to fetch history: {str(e)}")

@router.get("/history/{event_id}", response_model=AnalyzeResponse)
async def get_event_detail(event_id: str):
    """Retrieve detailed information for a specific scam event."""
    async with AsyncSessionLocal() as session:
        try:
            event_uuid = uuid.UUID(event_id)
            stmt = select(ScamEvent).where(ScamEvent.id == event_uuid)
            result = await session.execute(stmt)
            event = result.scalar_one_or_none()
            
            if not event:
                raise HTTPException(status_code=404, detail="Event not found")
            
            return AnalyzeResponse(
                id=str(event.id),
                text=event.text,
                source=event.source,
                risk_score=event.risk_score,
                decision=event.decision,
                reasons=event.metadata.get("reasons", []),
                intent=IntentScore(**event.metadata.get("intent", {})),
                entities=ExtractedEntities(**event.metadata.get("entities", {})),
                similarity=None # Could fetch matches from similarity service if needed
            )
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid event ID format")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error retrieving event: {str(e)}")
