"""
MiroOrg v2 — Optimized LangGraph pipeline.

Optimized graph topology (2-3 model calls instead of 5):
  [switchboard]
       │
       ├─ requires_simulation=true → [mirofish] → [research]
       ├─ requires_finance_data=true → [finance] → [research]
       └─ (default) → [research]
                            │
                       [synthesizer]
                            │
                          [END]

The synthesizer now handles planning, verification, and synthesis in one call.
This reduces latency from 5 model calls (3-6 min) to 2-3 calls (1-2 min).
"""

import uuid
import time
import logging
from typing import TypedDict, Dict, Any, Optional

from langgraph.graph import StateGraph, START, END

from app.agents import switchboard, research, synthesizer
from app.agents import mirofish_node, finance_node

logger = logging.getLogger(__name__)


# ── State Type ────────────────────────────────────────────────────────────────


class AgentState(TypedDict, total=False):
    # Input
    user_input: str
    case_id: str

    # Pipeline state
    route: dict  # switchboard output
    simulation: dict  # mirofish output (optional)
    finance: dict  # finance_node output (optional)
    research: dict  # research output
    final: dict  # synthesizer output

    # Control
    errors: list


# ── Node wrappers with timing ────────────────────────────────────────────────


def switchboard_node(state: AgentState) -> dict:
    t0 = time.perf_counter()
    result = switchboard.run(state)
    elapsed = time.perf_counter() - t0
    logger.info(
        f"[{state.get('case_id', '?')[:8]}] switchboard: {elapsed:.2f}s — domain={result.get('route', {}).get('domain')}"
    )
    return result


def mirofish_node_fn(state: AgentState) -> dict:
    t0 = time.perf_counter()
    result = mirofish_node.run(state)
    elapsed = time.perf_counter() - t0
    logger.info(f"[{state.get('case_id', '?')[:8]}] mirofish: {elapsed:.2f}s")
    return result


def finance_node_fn(state: AgentState) -> dict:
    t0 = time.perf_counter()
    result = finance_node.run(state)
    elapsed = time.perf_counter() - t0
    logger.info(f"[{state.get('case_id', '?')[:8]}] finance: {elapsed:.2f}s")
    return result


def research_node(state: AgentState) -> dict:
    t0 = time.perf_counter()
    result = research.run(state)
    elapsed = time.perf_counter() - t0
    logger.info(f"[{state.get('case_id', '?')[:8]}] research: {elapsed:.2f}s")
    return result


def synthesizer_node(state: AgentState) -> dict:
    t0 = time.perf_counter()
    result = synthesizer.run(state)
    elapsed = time.perf_counter() - t0
    logger.info(f"[{state.get('case_id', '?')[:8]}] synthesizer: {elapsed:.2f}s")
    return result


# ── Routing functions ─────────────────────────────────────────────────────────


def after_switchboard(state: AgentState) -> str:
    """Route based on switchboard flags."""
    route = state.get("route", {})
    if route.get("requires_simulation"):
        return "mirofish"
    if route.get("requires_finance_data"):
        return "finance"
    return "research"


# ── Build graph ───────────────────────────────────────────────────────────────


def build_graph():
    g = StateGraph(AgentState)

    g.add_node("switchboard", switchboard_node)
    g.add_node("research", research_node)
    g.add_node("mirofish", mirofish_node_fn)
    g.add_node("finance", finance_node_fn)
    g.add_node("synthesizer", synthesizer_node)

    g.set_entry_point("switchboard")

    # After switchboard: fork based on flags
    g.add_conditional_edges(
        "switchboard",
        after_switchboard,
        {"mirofish": "mirofish", "finance": "finance", "research": "research"},
    )

    # mirofish and finance both merge into research
    g.add_edge("mirofish", "research")
    g.add_edge("finance", "research")

    # Research goes directly to synthesizer (no planner/verifier loop)
    g.add_edge("research", "synthesizer")

    g.add_edge("synthesizer", END)
    return g.compile()


compiled_graph = build_graph()


def run_case(user_input: str) -> dict:
    """Run the optimized agent pipeline on user input."""
    case_id = str(uuid.uuid4())
    t0 = time.perf_counter()
    logger.info("Starting case %s", case_id)

    result = compiled_graph.invoke(
        {
            "case_id": case_id,
            "user_input": user_input,
            "route": {},
            "research": {},
            "final": {},
            "errors": [],
        }
    )

    elapsed = time.perf_counter() - t0
    logger.info("Case %s completed in %.2fs", case_id, elapsed)
    return result
