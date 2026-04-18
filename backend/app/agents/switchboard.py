"""
Switchboard — intelligence router for MiroOrg v2.
Classifies user input and produces structured routing decisions using LLM.
"""

import logging
from app.agents._model import call_model, safe_parse
from app.config import load_prompt
from pydantic import BaseModel, Field
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.exceptions import OutputParserException
from typing import List


class RouteDecision(BaseModel):
    domain: str = Field(
        description="Domain of the request (e.g. general, finance, technology, simulation)"
    )
    complexity: str = Field(description="Complexity: low, medium, or high")
    intent: str = Field(description="Summarized intent of the user")
    sub_tasks: List[str] = Field(description="List of isolated sub-tasks required")
    requires_simulation: bool = Field(description="True if scenario/simulation needed")
    requires_finance_data: bool = Field(description="True if stock/finance data needed")
    requires_news: bool = Field(description="True if current news needed")
    confidence: float = Field(description="Confidence of routing decision (0.0 - 1.0)")


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
        raw_response = call_model(messages)
    except Exception as e:
        logger.error(f"[AGENT ERROR] switchboard: {e}")
        raw_response = None
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

    if raw_response:
        result = safe_parse(raw_response)
        if "error" in result:
            logger.warning(f"[AGENT PARSE FALLBACK] switchboard: parse failed, using defaults")
            result = None

    # Ensure all required fields exist with defaults
    if result is None:
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
