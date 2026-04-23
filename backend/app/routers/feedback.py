import uuid
from fastapi import APIRouter, Depends, HTTPException
from app.schemas.request import FeedbackRequest
from app.db.session import AsyncSessionLocal
from app.db.models import Feedback

router = APIRouter(tags=["scam-guardian"])

@router.post("/feedback")
async def submit_feedback(request: FeedbackRequest):
    """Persist user feedback on a scam detection event."""
    async with AsyncSessionLocal() as session:
        try:
            feedback = Feedback(
                id=uuid.uuid4(),
                event_id=uuid.UUID(request.analyze_id),
                is_scam=request.is_scam,
                correct_category=request.correct_category,
                notes=request.notes
            )
            session.add(feedback)
            await session.commit()
            
            return {
                "status": "success", 
                "feedback_id": str(feedback.id),
                "event_id": request.analyze_id
            }
        except Exception as e:
            await session.rollback()
            raise HTTPException(status_code=500, detail=f"Failed to save feedback: {str(e)}")
