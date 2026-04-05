"""
Synthesizer agent — MiroOrg v2.
Final voice in the pipeline. Accepts all upstream outputs and produces
the definitive response the user sees.
"""

import json
import re
import logging
from app.agents._model import call_model, safe_parse
from app.config import load_prompt
from pydantic import BaseModel, Field
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.exceptions import OutputParserException
from typing import List, Optional


class SynthesizerOutput(BaseModel):
    response: str = Field(
        description="Comprehensive, direct final answer directed at the user"
    )
    confidence: float = Field(description="Confidence score between 0.0 and 1.0")
    data_sources: List[str] = Field(
        description="List of sources used (APIs, URLs, etc)"
    )
    caveats: List[str] = Field(
        description="List of caveats or limitations in this answer"
    )
    next_steps: List[str] = Field(description="Suggested next actions for the user")


logger = logging.getLogger(__name__)


def _extract_json_from_text(text: str) -> dict | None:
    """Extract JSON object from text that may contain markdown or prose."""
    # Try direct parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try stripping markdown code fences
    cleaned = re.sub(r"```(?:json)?\s*\n?", "", text).strip()
    cleaned = re.sub(r"\n?```\s*$", "", cleaned).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Try finding JSON object in text
    # Find the first { and last }
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidate = text[start : end + 1]
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    return None


def run(state: dict) -> dict:
    route = state.get("route", {})
    research = state.get("research", {})
    planner = state.get("planner", {})
    verifier = state.get("verifier", {})
    simulation = state.get("simulation", {})
    finance = state.get("finance", {})
    replan_count = state.get("replan_count", 0)

    prompt = load_prompt("synthesizer")
    parser = PydanticOutputParser(pydantic_object=SynthesizerOutput)

    # Build comprehensive context
    context_parts = [
        f"Route: {json.dumps(route, indent=2)}",
        f"Research: {json.dumps(research, indent=2)}",
        f"Planner: {json.dumps(planner, indent=2)}",
        f"Verifier: {json.dumps(verifier, indent=2)}",
    ]
    if simulation:
        context_parts.append(f"Simulation: {json.dumps(simulation, indent=2)}")
    if finance:
        context_parts.append(f"Finance: {json.dumps(finance, indent=2)}")
    if not verifier.get("passed", True) and replan_count >= 1:
        context_parts.append(
            "NOTE: Verifier did not fully pass and replan limit was reached. Acknowledge limitations."
        )

    messages = [
        {"role": "system", "content": prompt},
        {
            "role": "user",
            "content": (
                f"User request: {state.get('user_input', route.get('intent', ''))}\n\n"
                + "\n\n".join(context_parts)
                + "\n\n"
                + parser.get_format_instructions()
            ),
        },
    ]

    result = None
    raw_response = None

    try:
        raw_response = call_model(messages)
    except Exception as e:
        logger.error(f"[AGENT ERROR] synthesizer: {e}")
        raw_response = None
        result = {"status": "error", "reason": str(e), "error": "model_failed"}

    if raw_response:
        # Try Pydantic parser first
        try:
            parsed = parser.invoke(raw_response)
            result = parsed.dict()
        except OutputParserException:
            # Try manual JSON extraction
            extracted = _extract_json_from_text(raw_response)
            if extracted and "response" in extracted:
                result = extracted
                # Ensure required fields
                result.setdefault("confidence", 0.5)
                result.setdefault("data_sources", [])
                result.setdefault("caveats", [])
                result.setdefault("next_steps", [])
            else:
                # Last resort: use raw text as the response
                logger.warning(
                    f"[AGENT PARSE FALLBACK] synthesizer: using raw text as response"
                )
                result = {
                    "response": raw_response,
                    "confidence": 0.5,
                    "data_sources": [],
                    "caveats": ["response format could not be parsed"],
                    "next_steps": ["retry for formatted response"],
                }

    if result is None:
        result = {
            "response": "I encountered an error while synthesizing the analysis. Please try again.",
            "confidence": 0.0,
            "data_sources": [],
            "caveats": ["synthesis failed"],
            "next_steps": ["retry the query"],
        }

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
