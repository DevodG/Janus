from fastapi import APIRouter, Depends
from typing import List
from app.schemas.response import AnalyzeResponse
# from backend.app.db.session import get_db
# from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/history", tags=["scam-guardian"])

@router.get("/", response_model=List[AnalyzeResponse])
async def get_scam_history():
    # Placeholder for actual DB query
    return []

@router.get("/{event_id}", response_model=AnalyzeResponse)
async def get_event_detail(event_id: str):
    # Placeholder for actual DB query
    return None
