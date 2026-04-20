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

from app.services.domain_classifier import domain_classifier
from app.services.query_classifier import QueryClassifier, QueryType


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
query_classifier = QueryClassifier()


def _apply_deterministic_fallback(user_input: str, route: dict) -> dict:
    """Strengthen routing when the LLM route is weak or unavailable."""
    fallback = dict(route)

    domain_guess = "general"
    domain_confidence = 0.5
    query_type = None
    query_type_confidence = 0.0
    query_metadata = {}

    try:
        domain_result = domain_classifier.classify(user_input)
        domain_guess = domain_result.domain.value
        domain_confidence = domain_result.confidence
    except Exception as e:
        logger.debug("switchboard domain fallback failed: %s", e)

    try:
        query_type, query_type_confidence, query_metadata = query_classifier.classify(
            user_input
        )
    except Exception as e:
        logger.debug("switchboard query fallback failed: %s", e)

    detected_domain = query_metadata.get("detected_domain", "general")
    current_confidence = float(fallback.get("confidence", 0.0) or 0.0)
    current_domain = fallback.get("domain", "general")

    if current_domain == "general" or current_confidence < 0.6:
        if domain_guess != "general":
            fallback["domain"] = domain_guess
            fallback["confidence"] = max(current_confidence, domain_confidence)
        elif detected_domain != "general":
            fallback["domain"] = detected_domain
            fallback["confidence"] = max(current_confidence, query_type_confidence)

    if fallback.get("domain") == "finance" or detected_domain == "finance":
        fallback["requires_finance_data"] = True

    effective_confidence = float(fallback.get("confidence", current_confidence) or 0.0)
    scenario_terms = [
        "what if",
        "scenario",
        "simulate",
        "would happen",
        "impact",
        "forecast",
    ]

    if any(term in user_input.lower() for term in scenario_terms):
        fallback["requires_simulation"] = True
    elif query_type in {QueryType.SPECIFIC, QueryType.HYBRID} and effective_confidence < 0.45:
        fallback["requires_simulation"] = True
        if fallback.get("complexity") == "low":
            fallback["complexity"] = "medium"

    fallback["classifier_hint"] = {
        "domain_guess": domain_guess,
        "domain_confidence": round(domain_confidence, 3),
        "query_type": getattr(query_type, "value", None),
        "query_type_confidence": round(query_type_confidence, 3),
        "detected_domain": detected_domain,
    }
    return fallback


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
        logger.warning("[AGENT ERROR] switchboard: using default route")
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

    result = _apply_deterministic_fallback(user_input, result)

    return {**state, "route": result}
