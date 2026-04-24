"""
Native Simulation Router — replaces MiroFish dependency.

Provides REST API for the built-in simulation engine.
"""

import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.services.simulation_engine import simulation_engine

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/simulation", tags=["simulation"])


class SimulationRunRequest(BaseModel):
    user_input: str
    context: Optional[dict] = None


class SimulationChatRequest(BaseModel):
    message: str


@router.get("/health")
def simulation_health():
    """Native simulation engine health check."""
    return {
        "status": "ok",
        "type": "native",
        "simulations_count": len(simulation_engine.simulations),
    }


@router.get("/list")
def simulation_list():
    """List all simulations."""
    return simulation_engine.list_simulations()


@router.post("/run")
def simulation_run(payload: SimulationRunRequest):
    """Run a native simulation."""
    try:
        logger.info(f"Running native simulation: {payload.user_input[:100]}")
        result = simulation_engine.run_simulation(
            user_input=payload.user_input,
            context=payload.context,
        )
        return result
    except Exception as e:
        logger.error(f"Simulation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Simulation failed: {str(e)}")


@router.get("/{simulation_id}")
def simulation_status(simulation_id: str):
    """Get simulation details."""
    sim = simulation_engine.get_simulation(simulation_id)
    if not sim:
        raise HTTPException(status_code=404, detail="Simulation not found")
    return sim


@router.get("/{simulation_id}/report")
def simulation_report(simulation_id: str):
    """Get simulation report (synthesis)."""
    sim = simulation_engine.get_simulation(simulation_id)
    if not sim:
        raise HTTPException(status_code=404, detail="Simulation not found")
    return {
        "simulation_id": simulation_id,
        "user_input": sim.get("user_input", ""),
        "synthesis": sim.get("synthesis", {}),
        "perspectives": sim.get("perspectives", []),
    }


@router.post("/{simulation_id}/chat")
def simulation_chat(simulation_id: str, payload: SimulationChatRequest):
    """Chat with a completed simulation."""
    sim = simulation_engine.get_simulation(simulation_id)
    if not sim:
        raise HTTPException(status_code=404, detail="Simulation not found")
    return simulation_engine.chat_with_simulation(simulation_id, payload.message)
