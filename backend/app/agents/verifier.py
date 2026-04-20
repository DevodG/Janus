"""
Verifier agent — MiroOrg v2.
Accepts the Planner output and original route.
Stress-tests the plan and returns pass/fail with actionable feedback.
"""

import logging
from app.agents._model import call_model, safe_parse
from app.config import load_prompt

logger = logging.getLogger(__name__)


def _deterministic_verdict(state: dict) -> dict:
    route = state.get("route", {})
    planner = state.get("planner", {})
    research = state.get("research", {})
    simulation = state.get("simulation", {}) or {}
    finance = state.get("finance", {}) or {}

    issues = []
    fixes_required = []
    confidence = float(research.get("confidence", 0.0) or 0.0)

    plan_steps = planner.get("plan_steps", []) if isinstance(planner.get("plan_steps"), list) else []
    if not plan_steps:
        issues.append("planner produced no actionable steps")
        fixes_required.append("build a stepwise plan anchored in retrieved evidence")

    deep_web = research.get("deep_web", {}) if isinstance(research, dict) else {}
    sources = research.get("sources", []) if isinstance(research.get("sources"), list) else []
    if not sources and not deep_web.get("top_sources"):
        issues.append("no explicit sources were retained in the research output")
        fixes_required.append("retain at least one named source in the final analysis")

    if route.get("requires_finance_data") and not finance and route.get("domain") == "finance":
        issues.append("finance route requested structured finance data but none was available")
        fixes_required.append("state clearly that the answer relies on web evidence rather than live market APIs")

    if route.get("requires_simulation") and not simulation:
        issues.append("simulation was requested but no simulation output was attached")
        fixes_required.append("either run simulation or remove scenario claims")

    minor_only = all(
        issue
        in {
            "finance route requested structured finance data but none was available",
        }
        for issue in issues
    )
    passed = not issues or minor_only or bool(deep_web.get("top_sources") or sources)
    if not passed and not fixes_required:
        fixes_required.append("rewrite the answer so it only uses supported evidence")

    return {
        "passed": passed,
        "issues": issues,
        "fixes_required": fixes_required,
        "confidence": max(confidence, 0.45 if passed else 0.3),
        "mode": "deterministic_fallback",
    }


def run(state: dict) -> dict:
    route = state.get("route", {})
    planner = state.get("planner", {})
    research = state.get("research", {})
    context = state.get("context", {})

    prompt = load_prompt("verifier")

    try:
        adaptive = context.get("adaptive_intelligence", {})
        personality = adaptive.get("system_personality", {})
        socratic_depth = personality.get("socratic_depth", 0.4)
        
        socratic_instruction = ""
        if socratic_depth > 0.6:
            socratic_instruction = (
                "\nCRITICAL Socratic AUDIT REQUIRED:\n"
                "- Challenge the evidence. Is it current? Is it biased?\n"
                "- Look for logical gaps. Does the plan jump to conclusions?\n"
                "- Search for contradictions. Does one fact undermine another?"
            )

        messages = [
            {"role": "system", "content": prompt + socratic_instruction},
            {
                "role": "user",
                "content": (
                    f"Original route: {route}\n\n"
                    f"Research findings: {research}\n\n"
                    f"Planner output: {planner}\n\n"
                    f"Runtime context: {context}\n\n"
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
        
        result = safe_parse(call_model(messages, personality=personality))
    except Exception as e:
        logger.error(f"[AGENT ERROR] verifier: {e}")
        result = {"status": "error", "reason": str(e)}

    if result is None or "error" in result or result.get("status") == "error":
        logger.warning(
            f"[AGENT ERROR] verifier: {result.get('error') if isinstance(result, dict) else 'result is None'}"
        )
        result = _deterministic_verdict(state)

    # Ensure passed field exists
    result.setdefault("passed", True)
    result.setdefault("issues", [])
    result.setdefault("fixes_required", [])
    result.setdefault("confidence", 0.5)

    return {**state, "verifier": result}
