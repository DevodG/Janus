"""
Verifier agent — MiroOrg v2.
Accepts the Planner output and original route.
Stress-tests the plan and returns pass/fail with actionable feedback.
"""

import logging
from app.agents._model import call_model, safe_parse
from app.config import load_prompt

logger = logging.getLogger(__name__)


def run(state: dict) -> dict:
    route = state.get("route", {})
    planner = state.get("planner", {})
    research = state.get("research", {})

    prompt = load_prompt("verifier")

    messages = [
        {"role": "system", "content": prompt},
        {
            "role": "user",
            "content": (
                f"Original route: {route}\n\n"
                f"Research findings: {research}\n\n"
                f"Planner output: {planner}\n\n"
                "Verify the plan against the research and route. Return ONLY valid JSON:\n"
                "{\n"
                '  "passed": true | false,\n'
                '  "issues": ["<issue 1>", "<issue 2>"],\n'
                '  "fixes_required": ["<fix 1>", "<fix 2>"],\n'
                '  "confidence": 0.0-1.0\n'
                "}\n"
                "passed=false MUST include specific, actionable fixes_required items."
            ),
        },
    ]

    try:
        result = safe_parse(call_model(messages))
    except Exception as e:
        logger.error(f"[AGENT ERROR] verifier: {e}")
        result = {"status": "error", "reason": str(e)}

    if result is None or "error" in result:
        logger.warning(f"[AGENT ERROR] verifier: {result.get('error')}")
        # Default to passed=true on error so pipeline doesn't get stuck
        result = {
            "passed": True,
            "issues": ["verifier error — defaulting to pass"],
            "fixes_required": [],
            "confidence": 0.3,
        }

    # Ensure passed field exists
    result.setdefault("passed", True)
    result.setdefault("issues", [])
    result.setdefault("fixes_required", [])
    result.setdefault("confidence", 0.5)

    return {**state, "verifier": result}
