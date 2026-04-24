from fastapi import APIRouter
from app.core.runtime_state import runtime_state

router = APIRouter(tags=["guardian-status"])

@router.get("/guardian/status")
async def guardian_status():
    return {
        "db_mode": runtime_state.db_mode,
        "db_ready": runtime_state.db_ready,
        "reason": runtime_state.reason,
    }
