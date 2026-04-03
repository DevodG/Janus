import uuid
from fastapi import APIRouter, HTTPException

from app.config import MIROFISH_ENABLED
from app.schemas import SimulationRunRequest, SimulationChatRequest
from app.services.mirofish_client import (
    mirofish_health,
    run_simulation,
    simulation_status,
    simulation_report,
    simulation_chat,
    MiroFishError,
)
from app.services.simulation_store import save_simulation, get_simulation

router = APIRouter(prefix="/simulation", tags=["simulation"])


@router.get("/health")
def simulation_health():
    return mirofish_health()


@router.post("/run")
def simulation_run(payload: SimulationRunRequest):
    if not MIROFISH_ENABLED:
        raise HTTPException(status_code=400, detail="MiroFish integration is disabled")

    try:
        remote = run_simulation(payload.model_dump())
    except MiroFishError as e:
        raise HTTPException(status_code=502, detail=str(e))

    simulation_id = (
        remote.get("simulation_id")
        or remote.get("job_id")
        or remote.get("id")
        or str(uuid.uuid4())
    )

    record = {
        "simulation_id": simulation_id,
        "status": remote.get("status", "submitted"),
        "title": payload.title,
        "prediction_goal": payload.prediction_goal,
        "remote_payload": remote,
    }
    save_simulation(simulation_id, record)
    return record


@router.get("/{simulation_id}")
def simulation_status_endpoint(simulation_id: str):
    if not MIROFISH_ENABLED:
        raise HTTPException(status_code=400, detail="MiroFish integration is disabled")

    try:
        remote = simulation_status(simulation_id)
    except MiroFishError as e:
        raise HTTPException(status_code=502, detail=str(e))

    local = get_simulation(simulation_id) or {}
    merged = {**local, **remote, "simulation_id": simulation_id}
    save_simulation(simulation_id, merged)
    return merged


@router.get("/{simulation_id}/report")
def simulation_report_endpoint(simulation_id: str):
    if not MIROFISH_ENABLED:
        raise HTTPException(status_code=400, detail="MiroFish integration is disabled")

    try:
        report = simulation_report(simulation_id)
    except MiroFishError as e:
        raise HTTPException(status_code=502, detail=str(e))

    local = get_simulation(simulation_id) or {}
    merged = {**local, "report": report, "simulation_id": simulation_id}
    save_simulation(simulation_id, merged)
    return merged


@router.post("/{simulation_id}/chat")
def simulation_chat_endpoint(simulation_id: str, payload: SimulationChatRequest):
    if not MIROFISH_ENABLED:
        raise HTTPException(status_code=400, detail="MiroFish integration is disabled")

    try:
        result = simulation_chat(simulation_id, payload.message)
    except MiroFishError as e:
        raise HTTPException(status_code=502, detail=str(e))

    return {
        "simulation_id": simulation_id,
        "message": payload.message,
        "response": result,
    }