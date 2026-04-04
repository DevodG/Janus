"""
Switchboard — intelligence router for MiroOrg v2.
Classifies user input and produces structured routing decisions using LLM.
"""
import logging
from app.agents._model import call_model, safe_parse
from app.config import load_prompt

logger = logging.getLogger(__name__)


def run(state: dict) -> dict:
    """
    Analyse the user's input and produce a routing structure.
    Uses LLM for intent classification with structured JSON output.
    """
    user_input = state.get("user_input", "")
    prompt = load_prompt("switchboard")

    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": user_input},
    ]

    try:
        result = safe_parse(call_model(messages))
    except RuntimeError as e:
        logger.error(f"[AGENT ERROR] switchboard: {e}")
        result = {"status": "error", "reason": str(e)}

    # Ensure all required fields exist with defaults
    if "error" in result:
        logger.warning(f"[AGENT ERROR] switchboard: {result.get('error')}")
        result = {
            "domain": "general",
            "complexity": "medium",
            "intent": user_input[:200],
            "sub_tasks": [user_input[:200]],
            "requires_simulation": False,
            "requires_finance_data": False,
            "requires_news": False,
            "confidence": 0.3,
        }
    else:
        # Fill in any missing fields with safe defaults
        result.setdefault("domain", "general")
        result.setdefault("complexity", "medium")
        result.setdefault("intent", user_input[:200])
        result.setdefault("sub_tasks", [user_input[:200]])
        result.setdefault("requires_simulation", False)
        result.setdefault("requires_finance_data", False)
        result.setdefault("requires_news", False)
        result.setdefault("confidence", 0.5)

    return {**state, "route": result}
