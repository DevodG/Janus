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


def _clean_text_block(text: str, limit: int = 320) -> str:
    cleaned = re.sub(r"\s+", " ", str(text or "")).strip()
    return cleaned[:limit]


def _format_evidence_point(point: dict) -> str:
    statement = _clean_text_block(point.get("point", ""), 220)
    source = _clean_text_block(point.get("source", "source"), 80)
    credibility = float(point.get("credibility_score", 0.0) or 0.0)
    return f"- {statement} (Source: {source}, credibility {credibility:.2f})"


def _fallback_key_insight(state: dict) -> str:
    route = state.get("route", {})
    research = state.get("research", {})
    deep_web = research.get("deep_web", {}) if isinstance(research, dict) else {}
    key_points = deep_web.get("key_points", []) if isinstance(deep_web.get("key_points"), list) else []
    top_sources = deep_web.get("top_sources", []) if isinstance(deep_web.get("top_sources"), list) else []

    if key_points:
        lead = _clean_text_block(key_points[0].get("point", ""), 260)
        credibility = key_points[0].get("credibility_score", 0.0)
        return (
            f"The strongest evidence Janus found points to this: {lead}. "
            f"That lead source carried a credibility score of {credibility:.2f}."
        )

    summary = _clean_text_block(research.get("summary", ""), 260)
    if summary:
        return summary

    if top_sources:
        source = top_sources[0]
        return (
            f"Janus found source-backed evidence from {source.get('title', source.get('url', 'a top source'))} "
            f"with credibility {source.get('credibility_score', 0.0):.2f}."
        )

    return f"Janus assembled the best grounded fallback it could for this {route.get('domain', 'general')} request."


def _fallback_bottom_line(state: dict) -> str:
    route = state.get("route", {})
    intent = route.get("intent") or state.get("user_input", "this request")
    research = state.get("research", {})
    deep_web = research.get("deep_web", {}) if isinstance(research, dict) else {}
    avg_credibility = float(deep_web.get("avg_credibility", 0.0) or 0.0)

    if route.get("domain") == "finance":
        if avg_credibility >= 0.8:
            return (
                f"For {intent}, Janus found enough credible evidence to support a useful market brief, "
                "but not enough live structured market data to treat it as a trading signal."
            )
        return (
            f"For {intent}, Janus found directional evidence, but the conclusion should be treated as provisional "
            "until it is checked against fresher market data."
        )

    if avg_credibility >= 0.8:
        return f"For {intent}, the strongest retrieved evidence points in a fairly consistent direction."
    if avg_credibility >= 0.6:
        return f"For {intent}, Janus found some credible evidence, but the picture is still incomplete."
    return f"For {intent}, Janus found only limited high-confidence evidence, so this brief should be treated cautiously."


def _fallback_implication(state: dict) -> str:
    route = state.get("route", {})
    simulation = state.get("simulation", {}) or {}
    synthesis = simulation.get("synthesis", {}) if isinstance(simulation, dict) else {}
    deep_web = (state.get("research", {}) or {}).get("deep_web", {})
    avg_credibility = deep_web.get("avg_credibility", 0.0) if isinstance(deep_web, dict) else 0.0
    finance = state.get("finance", {}) or {}
    metrics = finance.get("key_metrics", {}) if isinstance(finance.get("key_metrics"), dict) else {}

    if route.get("domain") == "finance":
        base = "For a finance question, the key implication is that evidence quality and freshness matter more than a single headline."
    else:
        base = "The implication is that Janus found directional evidence, but the strength of the conclusion depends on source quality."

    if metrics.get("price") is not None:
        base += f" The latest structured price Janus saw was {metrics.get('price')}."
    if metrics.get("market_cap"):
        base += f" Reported market cap was {metrics.get('market_cap')}."

    if synthesis.get("most_likely"):
        base += f" The scenario view still leans toward: {synthesis.get('most_likely', '')}."
    if avg_credibility:
        base += f" The average credibility of the best web bundle was {avg_credibility:.2f}."
    return base


def _fallback_confidence_and_limits(state: dict) -> str:
    research = state.get("research", {})
    deep_web = research.get("deep_web", {}) if isinstance(research, dict) else {}
    avg_credibility = float(deep_web.get("avg_credibility", 0.0) or 0.0)
    confidence = float(research.get("confidence", 0.0) or 0.0)
    gaps = research.get("gaps", []) if isinstance(research.get("gaps"), list) else []

    note = f"Janus confidence in this fallback brief is {confidence:.2f}."
    if avg_credibility:
        note += f" The retrieved deep-web bundle averaged {avg_credibility:.2f} credibility."
    if gaps:
        note += " Main limitations: " + "; ".join(_clean_text_block(g, 120) for g in gaps[:3]) + "."
    return note


def _deterministic_fallback_response(state: dict) -> dict:
    route = state.get("route", {})
    research = state.get("research", {})
    simulation = state.get("simulation", {}) or {}
    finance = state.get("finance", {}) or {}
    deep_web = research.get("deep_web", {}) if isinstance(research, dict) else {}
    deep_points = deep_web.get("key_points", []) if isinstance(deep_web.get("key_points"), list) else []

    sections = [f"## Bottom Line\n{_fallback_bottom_line(state)}"]
    sections.append(f"## Key Insight\n{_fallback_key_insight(state)}")
    sections.append(f"## Why It Matters\n{_fallback_implication(state)}")

    key_facts = research.get("key_facts", []) if isinstance(research.get("key_facts"), list) else []
    if deep_points:
        bullets = "\n".join(_format_evidence_point(point) for point in deep_points[:4])
        sections.append(f"## Evidence\n{bullets}")
    elif key_facts:
        bullets = "\n".join(f"- {_clean_text_block(fact, 240)}" for fact in key_facts[:5])
        sections.append(f"## Evidence\n{bullets}")

    top_sources = deep_web.get("top_sources", []) if isinstance(deep_web.get("top_sources"), list) else []
    if top_sources:
        bullets = "\n".join(
            f"- {item.get('title', item.get('url', 'source'))} [{item.get('credibility_score', 0.0):.2f}]"
            for item in top_sources[:4]
        )
        sections.append(f"## Top Sources\n{bullets}")

    if finance:
        price = finance.get("quote", {}).get("05. price") if isinstance(finance.get("quote"), dict) else None
        metrics = finance.get("key_metrics", {}) if isinstance(finance.get("key_metrics"), dict) else {}
        if price is None and isinstance(finance, dict):
            price = finance.get("05. price")
        if price is None:
            price = metrics.get("price")
        market_cap = None
        if isinstance(finance.get("overview"), dict):
            market_cap = finance.get("overview", {}).get("market_cap")
        if market_cap is None:
            market_cap = metrics.get("market_cap")
        pe_ratio = metrics.get("pe_ratio")
        sector = metrics.get("sector")
        if price is not None or market_cap or pe_ratio or sector:
            finance_lines = []
            if price is not None:
                finance_lines.append(f"- Price: {price}")
            if market_cap:
                finance_lines.append(f"- Market cap: {market_cap}")
            if pe_ratio is not None:
                finance_lines.append(f"- PE ratio: {pe_ratio}")
            if sector:
                finance_lines.append(f"- Sector: {sector}")
            finance_str = '\n'.join(finance_lines)
            sections.append(f"## Market Data\n{finance_str}")

    synthesis = simulation.get("synthesis", {}) if isinstance(simulation, dict) else {}
    if synthesis.get("most_likely"):
        sections.append(
            f"## Simulation View\nMost likely outcome: {synthesis.get('most_likely', '')}"
        )

    sections.append(f"## Confidence & Limits\n{_fallback_confidence_and_limits(state)}")

    next_steps_preview = []
    if route.get("requires_simulation"):
        next_steps_preview.append("stress test the conclusion with a deeper scenario run")
    if route.get("domain") == "finance":
        next_steps_preview.append("check fresh market data before acting")
    if next_steps_preview:
        sections.append(
            "## Recommended Action\n" + "\n".join(f"- {step}" for step in next_steps_preview[:3])
        )

    if not sections:
        sections.append(
            "## Status\nJanus could not complete a model-based synthesis and there was not enough structured evidence to build a grounded fallback answer."
        )

    caveats = []
    if research.get("gaps"):
        caveats.extend(research.get("gaps", [])[:3])
    caveats.append("final answer was assembled deterministically because model synthesis was unavailable")

    sources = research.get("sources", []) if isinstance(research.get("sources"), list) else []
    next_steps = []
    if route.get("requires_simulation"):
        next_steps.append("run a deeper follow-up simulation if you want scenario planning")
    if route.get("domain") == "finance":
        next_steps.append("verify with fresh market data before making capital-allocation decisions")
    if not next_steps:
        next_steps.append("retry with a model provider configured for a richer final synthesis")

    return {
        "response": "\n\n".join(sections),
        "confidence": max(float(research.get("confidence", 0.0) or 0.0), 0.35 if sections else 0.0),
        "data_sources": sources[:8],
        "caveats": caveats[:5],
        "next_steps": next_steps[:4],
    }


def run(state: dict) -> dict:
    route = state.get("route", {})
    research = state.get("research", {})
    planner = state.get("planner", {})
    verifier = state.get("verifier", {})
    simulation = state.get("simulation", {})
    finance = state.get("finance", {})
    replan_count = state.get("replan_count", 0)
    context = state.get("context", {})

    prompt = load_prompt("synthesizer")

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
    similar_cases = context.get("memory", {}).get("similar_cases", []) if context else []
    if similar_cases:
        context_parts.append(f"Similar cases: {json.dumps(similar_cases[:3], indent=2)}")
    adaptive = context.get("adaptive_intelligence", {}) if context else {}
    if adaptive:
        context_parts.append(f"Adaptive intelligence: {json.dumps(adaptive, indent=2)}")
    if not verifier.get("passed", True) and replan_count >= 1:
        context_parts.append(
            "NOTE: Verifier did not fully pass and replan limit was reached. Acknowledge limitations."
        )

    # Inject system context into the synthesizer
    system_context = ""
    if context:
        system_self = context.get("system_self", {})
        pending = system_self.get("pending_thoughts", [])
        discoveries = system_self.get("recent_discoveries", [])
        user_ctx = context.get("user", {})

        if pending:
            thoughts = [t.get("thought", "") for t in pending[:3] if t.get("thought")]
            if thoughts:
                system_context += "\n\nTHINGS YOU'VE BEEN THINKING ABOUT:\n"
                system_context += "\n".join(f"- {t}" for t in thoughts)

        if discoveries:
            system_context += "\n\nRECENT DISCOVERIES:\n"
            for d in discoveries[:3]:
                system_context += f"- {d.get('discovery', '')}\n"

        if user_ctx.get("is_returning"):
            system_context += f"\n\nThis user has had {user_ctx.get('conversation_count', 0)} conversations with you."
            if user_ctx.get("last_topic"):
                system_context += f" Last topic: {user_ctx['last_topic']}."
            if user_ctx.get("time_away"):
                system_context += f" They've been away for {user_ctx['time_away']}."

        if user_ctx.get("recurring_interests"):
            system_context += f"\nTheir recurring interests: {', '.join(user_ctx['recurring_interests'][:3])}."

        # Self-reflection context
        reflection = context.get("self_reflection", {})
        if reflection:
            corrections = reflection.get("corrections", [])
            if corrections:
                system_context += "\n\nTHINGS YOU WERE WRONG ABOUT AND CORRECTED ON:"
                for c in corrections[:3]:
                    system_context += f"\n- You said: {c.get('original', '')[:100]}"
                    system_context += f"\n  Correction: {c.get('correction', '')[:100]}"

            gaps = reflection.get("gaps", [])
            if gaps:
                system_context += "\n\nTHINGS YOU KNOW YOU'RE WEAK AT:"
                for g in gaps[:3]:
                    system_context += (
                        f"\n- {g.get('topic', '')}: {g.get('reason', '')[:100]}"
                    )

            opinions = reflection.get("opinions", [])
            if opinions:
                system_context += "\n\nVIEWS YOU'VE FORMED:"
                for op in opinions[:3]:
                    system_context += f"\n- On {op.get('topic', '')}: {op.get('statement', '')[:150]} (confidence: {op.get('confidence', 0)})"

    messages = [
        {"role": "system", "content": prompt},
        {
            "role": "user",
            "content": (
                f"User request: {state.get('user_input', route.get('intent', ''))}\n\n"
                + "\n\n".join(context_parts)
                + (f"\n\n{system_context}" if system_context else "")
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
        # Try manual JSON extraction (prompt already defines the schema)
        extracted = _extract_json_from_text(raw_response)
        if extracted and "response" in extracted:
            result = extracted
            result.setdefault("confidence", 0.5)
            result.setdefault("data_sources", [])
            result.setdefault("caveats", [])
            result.setdefault("next_steps", [])
        else:
            # Last resort: use raw text as the response
            logger.warning("[AGENT PARSE FALLBACK] synthesizer: using raw text as response")
            result = {
                "response": raw_response,
                "confidence": 0.5,
                "data_sources": [],
                "caveats": ["response format could not be parsed"],
                "next_steps": ["retry for formatted response"],
            }

    if result is None:
        result = _deterministic_fallback_response(state)

    if "error" in result:
        logger.warning(f"[AGENT ERROR] synthesizer: {result.get('error')}")
        result = _deterministic_fallback_response(state)

    return {**state, "final": result}
