"""
Native MiroFish simulation node.
Replaces external MiroFish dependency with built-in simulation engine.
"""

import logging
from app.services.simulation_engine import simulation_engine

logger = logging.getLogger(__name__)


def run(state: dict) -> dict:
    """Run native simulation and inject results into agent state."""
    route = state.get("route", {})
    intent = route.get("intent", state.get("user_input", ""))

    try:
        logger.info(f"Running native simulation for: {intent[:100]}")
        sim_result = simulation_engine.run_simulation(
            user_input=intent,
            context={
                "case_id": state.get("case_id"),
                "domain": route.get("domain", "general"),
                "complexity": route.get("complexity", "medium"),
            },
        )
        return {**state, "simulation": sim_result}
    except Exception as e:
        logger.warning(f"Native simulation failed: {e}")
        return {
            **state,
            "simulation": {
                "error": str(e),
                "note": "Simulation unavailable, continuing without simulation",
            },
        }
