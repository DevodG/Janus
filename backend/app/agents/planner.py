"""
Planner agent — MiroOrg v2.
Accepts Switchboard route + Research output + (optionally) Simulation and Finance outputs.
Produces a structured plan with steps, dependencies, and risk assessment.
"""
import logging
from app.agents._model import call_model, safe_parse
from app.config import load_prompt

logger = logging.getLogger(__name__)


def run(state: dict) -> dict:
    route = state.get("route", {})
    research = state.get("research", {})
    simulation = state.get("simulation", {})
    finance = state.get("finance", {})
    replan_count = state.get("replan_count", 0)
    verifier = state.get("verifier", {})

    prompt = load_prompt("planner")

    # Build context with all available upstream data
    context_parts = [
        f"Route: {route}",
        f"Research findings: {research}",
    ]
    if simulation:
        context_parts.append(f"Simulation results: {simulation}")
    if finance:
        context_parts.append(f"Finance data: {finance}")
    if replan_count > 0 and verifier:
        context_parts.append(f"REPLAN #{replan_count} — Verifier feedback: {verifier}")

    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": (
            f"User request: {state.get('user_input', route.get('intent', ''))}\n\n"
            + "\n\n".join(context_parts)
            + "\n\nProduce structured JSON output:\n"
            "{\n"
            "  \"plan_steps\": [\"<step 1>\", \"<step 2>\"],\n"
            "  \"resources_needed\": [\"<resource 1>\"],\n"
            "  \"dependencies\": [\"<dependency 1>\"],\n"
            "  \"risk_level\": \"low | medium | high\",\n"
            "  \"estimated_output\": \"<brief description of expected output>\""
            + (",\n  \"replan_reason\": \"<why replanning>\"" if replan_count > 0 else "")
            + "\n}\n"
        )},
    ]

    try:
        result = safe_parse(call_model(messages))
    except RuntimeError as e:
        logger.error(f"[AGENT ERROR] planner: {e}")
        result = {"status": "error", "reason": str(e)}

    if "error" in result:
        logger.warning(f"[AGENT ERROR] planner: {result.get('error')}")
        result = {
            "plan_steps": ["Unable to generate plan due to error"],
            "resources_needed": [],
            "dependencies": [],
            "risk_level": "high",
            "estimated_output": "Error in planning phase",
        }

    return {**state, "planner": result}
