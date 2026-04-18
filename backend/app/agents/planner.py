"""
Planner agent — MiroOrg v2.
Accepts Switchboard route + Research output + (optionally) Simulation and Finance outputs.
Produces a structured plan with steps, dependencies, and risk assessment.
"""

import logging
from app.agents._model import call_model, safe_parse
from app.config import load_prompt
from pydantic import BaseModel, Field
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.exceptions import OutputParserException
from typing import List, Optional


class PlannerOutput(BaseModel):
    plan_steps: List[str] = Field(
        description="Sequential list of steps to execute the plan"
    )
    resources_needed: List[str] = Field(description="Necessary tools or APIs")
    dependencies: List[str] = Field(description="Prerequisites or sequence locks")
    risk_level: str = Field(description="Risk assessment: low, medium, or high")
    estimated_output: str = Field(
        description="Brief outline of the expected final result"
    )
    replan_reason: Optional[str] = Field(
        None, description="Why we are replanning, if applicable"
    )


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
        {
            "role": "user",
            "content": (
                f"User request: {state.get('user_input', route.get('intent', ''))}\n\n"
                + "\n\n".join(context_parts)
            ),
        },
    ]

    result = None
    raw_response = None

    try:
        raw_response = call_model(messages)
    except Exception as e:
        logger.error(f"[AGENT ERROR] planner: {e}")
        raw_response = None
        result = {"status": "error", "reason": str(e), "error": "model_failed"}

    if raw_response:
        result = safe_parse(raw_response)
        if "error" in result:
            logger.warning(f"[AGENT PARSE FALLBACK] planner: using safe_parse fallback")
            result = None

    if result is None:
        result = {
            "plan_steps": ["Unable to generate plan due to error"],
            "resources_needed": [],
            "dependencies": [],
            "risk_level": "high",
            "estimated_output": "Error in planning phase",
        }

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
