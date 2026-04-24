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


def _deterministic_plan(state: dict) -> dict:
    route = state.get("route", {})
    research = state.get("research", {})
    deep_web = research.get("deep_web", {}) if isinstance(research, dict) else {}
    simulation = state.get("simulation", {}) or {}
    finance = state.get("finance", {}) or {}

    intent = route.get("intent") or state.get("user_input", "the request")
    steps = [f"Clarify the objective: {intent}."]
    resources = []
    dependencies = []

    key_facts = research.get("key_facts", []) if isinstance(research.get("key_facts"), list) else []
    if deep_web.get("top_sources"):
        top_source = deep_web.get("top_sources", [])[0]
        steps.append(
            f"Anchor the answer in the highest-credibility source: {top_source.get('title', top_source.get('url', 'source'))}."
        )
        resources.append("deep_web_bundle")
    elif key_facts:
        steps.append("Use the strongest retrieved facts as the primary evidence base.")

    if route.get("domain") == "finance":
        steps.append("Separate factual market/company evidence from interpretation or advice.")
        dependencies.append("credible source review")
        resources.append("finance_domain_pack")

    if finance:
        steps.append("Incorporate the structured market data into the answer and note any stale or missing fields.")
        resources.append("market_data")

    if simulation:
        steps.append("Compare the main evidence against the scenario view and explain what remains uncertain.")
        resources.append("simulation_engine")

    gaps = research.get("gaps", []) if isinstance(research.get("gaps"), list) else []
    if gaps:
        steps.append("Call out the most important gaps so the user knows what could change the conclusion.")
        dependencies.append("gap disclosure")

    steps.append("Return a decisive answer with confidence and next steps.")

    confidence = float(research.get("confidence", 0.0) or 0.0)
    if confidence >= 0.75:
        risk_level = "low"
    elif confidence >= 0.45:
        risk_level = "medium"
    else:
        risk_level = "high"

    return {
        "plan_steps": steps,
        "resources_needed": list(dict.fromkeys(resources)),
        "dependencies": list(dict.fromkeys(dependencies)),
        "risk_level": risk_level,
        "estimated_output": f"A grounded answer for: {intent}",
        "replan_reason": "deterministic fallback due to unavailable model synthesis",
    }


def run(state: dict) -> dict:
    route = state.get("route", {})
    research = state.get("research", {})
    simulation = state.get("simulation", {})
    finance = state.get("finance", {})
    replan_count = state.get("replan_count", 0)
    verifier = state.get("verifier", {})
    context = state.get("context", {})

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
    similar_cases = context.get("memory", {}).get("similar_cases", [])
    if similar_cases:
        context_parts.append(f"Similar cases: {similar_cases[:3]}")
    known_gaps = context.get("self_reflection", {}).get("gaps", [])
    if known_gaps:
        context_parts.append(f"Known gaps: {known_gaps[:3]}")

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
        adaptive = context.get("adaptive_intelligence", {})
        personality = adaptive.get("system_personality", {})
        raw_response = call_model(messages, personality=personality)
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
        result = _deterministic_plan(state)

    if "error" in result:
        logger.warning(f"[AGENT ERROR] planner: {result.get('error')}")
        result = _deterministic_plan(state)

    return {**state, "planner": result}
