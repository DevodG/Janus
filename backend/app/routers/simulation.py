import uuid
import logging
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
from app.services.simulation_store import save_simulation, get_simulation, list_simulations

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/simulation", tags=["simulation"])


@router.get("/health")
def simulation_health():
    return mirofish_health()


@router.get("/list")
def simulation_list():
    """
    List all simulations.
    
    Returns a list of all stored simulations with their status.
    """
    simulations = list_simulations()
    return simulations


@router.post("/run")
def simulation_run(payload: SimulationRunRequest):
    """
    Submit a simulation request to MiroFish.
    
    This endpoint creates a case-linked simulation that can be tracked
    and referenced from case execution records.
    """
    if not MIROFISH_ENABLED:
        logger.warning("Simulation request rejected: MiroFish is disabled")
        raise HTTPException(
            status_code=400, 
            detail="MiroFish simulation service is not enabled. Please enable MIROFISH_ENABLED in configuration."
        )

    try:
        logger.info(f"Submitting simulation: {payload.title}")
        remote = run_simulation(payload.model_dump())
        logger.info(f"Simulation submitted successfully")
    except MiroFishError as e:
        logger.error(f"MiroFish simulation submission failed: {e}")
        raise HTTPException(
            status_code=502, 
            detail=f"MiroFish service error: {str(e)}. Please check if MiroFish service is running at the configured endpoint."
        )

    simulation_id = (
        remote.get("simulation_id")
        or remote.get("job_id")
        or remote.get("id")
        or str(uuid.uuid4())
    )

    # Store simulation with case linking support
    record = {
        "simulation_id": simulation_id,
        "status": remote.get("status", "submitted"),
        "title": payload.title,
        "prediction_goal": payload.prediction_goal,
        "remote_payload": remote,
        "case_id": payload.metadata.get("case_id") if payload.metadata else None,  # Link to case if provided
    }
    save_simulation(simulation_id, record)
    logger.info(f"Simulation {simulation_id} saved locally with case_id: {record.get('case_id')}")
    return record


@router.get("/{simulation_id}")
def simulation_status_endpoint(simulation_id: str):
    """
    Get the current status of a simulation.
    
    Returns merged local and remote status information.
    """
    if not MIROFISH_ENABLED:
        logger.warning(f"Simulation status request rejected for {simulation_id}: MiroFish is disabled")
        raise HTTPException(
            status_code=400, 
            detail="MiroFish simulation service is not enabled."
        )

    try:
        logger.info(f"Fetching status for simulation {simulation_id}")
        remote = simulation_status(simulation_id)
    except MiroFishError as e:
        logger.error(f"Failed to fetch simulation status for {simulation_id}: {e}")
        raise HTTPException(
            status_code=502, 
            detail=f"Failed to retrieve simulation status from MiroFish: {str(e)}"
        )

    local = get_simulation(simulation_id) or {}
    merged = {**local, **remote, "simulation_id": simulation_id}
    save_simulation(simulation_id, merged)
    logger.info(f"Simulation {simulation_id} status: {merged.get('status', 'unknown')}")
    return merged


@router.get("/{simulation_id}/report")
def simulation_report_endpoint(simulation_id: str):
    """
    Get the final report for a completed simulation.
    
    Returns the simulation report with analysis and insights.
    """
    if not MIROFISH_ENABLED:
        logger.warning(f"Simulation report request rejected for {simulation_id}: MiroFish is disabled")
        raise HTTPException(
            status_code=400, 
            detail="MiroFish simulation service is not enabled."
        )

    try:
        logger.info(f"Fetching report for simulation {simulation_id}")
        report = simulation_report(simulation_id)
    except MiroFishError as e:
        logger.error(f"Failed to fetch simulation report for {simulation_id}: {e}")
        raise HTTPException(
            status_code=502, 
            detail=f"Failed to retrieve simulation report from MiroFish: {str(e)}"
        )

    local = get_simulation(simulation_id) or {}
    merged = {**local, "report": report, "simulation_id": simulation_id}
    save_simulation(simulation_id, merged)
    logger.info(f"Simulation {simulation_id} report retrieved successfully")
    return merged


@router.post("/{simulation_id}/chat")
def simulation_chat_endpoint(simulation_id: str, payload: SimulationChatRequest):
    """
    Ask follow-up questions about a completed simulation.
    
    Enables deep interaction with simulation results.
    """
    if not MIROFISH_ENABLED:
        logger.warning(f"Simulation chat request rejected for {simulation_id}: MiroFish is disabled")
        raise HTTPException(
            status_code=400, 
            detail="MiroFish simulation service is not enabled."
        )

    try:
        logger.info(f"Simulation chat for {simulation_id}: {payload.message[:50]}...")
        result = simulation_chat(simulation_id, payload.message)
    except MiroFishError as e:
        logger.error(f"Simulation chat failed for {simulation_id}: {e}")
        raise HTTPException(
            status_code=502, 
            detail=f"Failed to chat with simulation: {str(e)}"
        )

    logger.info(f"Simulation chat response received for {simulation_id}")
    return {
        "simulation_id": simulation_id,
        "message": payload.message,
        "response": result,
    }