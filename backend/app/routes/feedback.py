from fastapi import APIRouter, Depends
from app.schemas.request import FeedbackRequest

router = APIRouter(prefix="/feedback", tags=["scam-guardian"])

@router.post("/")
async def submit_feedback(request: FeedbackRequest):
    # Placeholder for DB save
    return {"status": "success", "message": "Feedback recorded."}
