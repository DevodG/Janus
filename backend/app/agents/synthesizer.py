"""
Synthesizer agent — MiroOrg v2.
Final voice in the pipeline. Accepts all upstream outputs and produces
the definitive response the user sees.
"""
import logging
from app.agents._model import call_model, safe_parse
from app.config import load_prompt

logger = logging.getLogger(__name__)


def run(state: dict) -> dict:
    route = state.get("route", {})
    research = state.get("research", {})
    planner = state.get("planner", {})
    verifier = state.get("verifier", {})
    simulation = state.get("simulation", {})
    finance = state.get("finance", {})
    replan_count = state.get("replan_count", 0)

    prompt = load_prompt("synthesizer")

    # Build comprehensive context
    context_parts = [
        f"Route: {route}",
        f"Research: {research}",
        f"Planner: {planner}",
        f"Verifier: {verifier}",
    ]
    if simulation:
        context_parts.append(f"Simulation: {simulation}")
    if finance:
        context_parts.append(f"Finance: {finance}")
    if not verifier.get("passed", True) and replan_count >= 2:
        context_parts.append("NOTE: Verifier did not fully pass and replan limit was reached. Acknowledge limitations.")

    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": (
            f"User request: {state.get('user_input', route.get('intent', ''))}\n\n"
            + "\n\n".join(context_parts)
            + "\n\nProduce the final structured JSON output:\n"
            "{\n"
            "  \"response\": \"<comprehensive, direct final answer>\",\n"
            "  \"confidence\": 0.0-1.0,\n"
            "  \"data_sources\": [\"<source 1>\", \"<source 2>\"],\n"
            "  \"caveats\": [\"<caveat 1>\"],\n"
            "  \"next_steps\": [\"<action 1>\", \"<action 2>\"]\n"
            "}\n"
        )},
    ]

    try:
        result = safe_parse(call_model(messages))
    except RuntimeError as e:
        logger.error(f"[AGENT ERROR] synthesizer: {e}")
        result = {"status": "error", "reason": str(e)}

    if "error" in result:
        logger.warning(f"[AGENT ERROR] synthesizer: {result.get('error')}")
        result = {
            "response": "I encountered an error while synthesizing the analysis. Please try again.",
            "confidence": 0.0,
            "data_sources": [],
            "caveats": ["synthesis failed"],
            "next_steps": ["retry the query"],
        }

    return {**state, "final": result}
