"""
Mirofish simulation node.
Calls the Mirofish local simulation service and injects results into agent state.
Mirofish handles scenario modelling, agent-based simulation, and outcome projection.
"""
import httpx, os, logging
from app.agents._model import call_model, safe_parse
from app.config import load_prompt

logger = logging.getLogger(__name__)

MIROFISH_BASE = os.getenv("MIROFISH_BASE_URL", "http://localhost:8001")


def run_simulation(scenario: dict) -> dict:
    r = httpx.post(f"{MIROFISH_BASE}/simulate", json=scenario, timeout=60)
    r.raise_for_status()
    return r.json()


def run(state: dict) -> dict:
    route = state.get("route", {})
    intent = route.get("intent", "")
    sub_tasks = route.get("sub_tasks", [])

    scenario = {
        "intent": intent,
        "tasks": sub_tasks,
        "complexity": route.get("complexity", "medium"),
        "domain": route.get("domain", "general"),
    }

    try:
        sim_result = run_simulation(scenario)
    except Exception as e:
        logger.warning(f"Mirofish unavailable: {e}")
        sim_result = {"error": str(e), "note": "Mirofish unavailable, continuing without simulation"}

    prompt = load_prompt("simulation")
    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": (
            f"Simulation results from Mirofish:\n{sim_result}\n\n"
            f"Original intent: {intent}\n\n"
            "Interpret these simulation results. Return ONLY valid JSON with: "
            "key_findings, confidence, scenarios_run, recommended_path, caveats."
        )},
    ]
    try:
        result = safe_parse(call_model(messages))
    except RuntimeError as e:
        logger.error(f"[AGENT ERROR] mirofish_node: {e}")
        result = {"status": "error", "reason": str(e)}

    return {**state, "simulation": result}
