"""
Janus — LangGraph pipeline.

Deliberative graph topology:
  [switchboard]
       │
       ├─ requires_simulation=true → [mirofish] ┐
       ├─ requires_finance_data=true → [finance] ├→ [research] → [planner] → [verifier]
       └─ (default) → [research]               ┘                        │
                                                                        ├─ pass → [synthesizer] → [END]
                                                                        └─ fail once → [repair] → [planner]

Context from the context engine is injected into every LLM call.
"""

import uuid
import time
import logging
from typing import TypedDict, Dict, Any, Optional

from langgraph.graph import StateGraph, START, END

from app.agents import planner, switchboard, research, synthesizer, verifier
from app.agents import mirofish_node, finance_node

logger = logging.getLogger(__name__)


class AgentState(TypedDict, total=False):
    user_input: str
    case_id: str
    route: dict
    simulation: dict
    finance: dict
    research: dict
    planner: dict
    verifier: dict
    final: dict
    errors: list
    context: dict
    replan_count: int


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


def planner_node(state: AgentState) -> dict:
    t0 = time.perf_counter()
    result = planner.run(state)
    elapsed = time.perf_counter() - t0
    logger.info(f"[{state.get('case_id', '?')[:8]}] planner: {elapsed:.2f}s")
    return result


def verifier_node(state: AgentState) -> dict:
    t0 = time.perf_counter()
    result = verifier.run(state)
    elapsed = time.perf_counter() - t0
    verdict = result.get("verifier", {}).get("passed")
    logger.info(
        f"[{state.get('case_id', '?')[:8]}] verifier: {elapsed:.2f}s — passed={verdict}"
    )
    return result


def synthesizer_node(state: AgentState) -> dict:
    t0 = time.perf_counter()
    result = synthesizer.run(state)
    elapsed = time.perf_counter() - t0
    logger.info(f"[{state.get('case_id', '?')[:8]}] synthesizer: {elapsed:.2f}s")
    return result


def repair_node(state: AgentState) -> dict:
    next_replan = state.get("replan_count", 0) + 1
    logger.info(
        "[%s] repair: incrementing replan_count to %s",
        state.get("case_id", "?")[:8],
        next_replan,
    )
    return {**state, "replan_count": next_replan}


def after_switchboard(state: AgentState) -> str:
    route = state.get("route", {})
    # Finance is cheap/structured and should run even if simulation is also needed.
    if route.get("requires_finance_data"):
        return "finance"
    if route.get("requires_simulation"):
        return "mirofish"
    if route.get("confidence", 0.5) < 0.45 and route.get(
        "complexity", "medium"
    ) in {"medium", "high", "very_high"}:
        logger.info(
            "[%s] switchboard triggered simulation due to low confidence",
            state.get("case_id", "?")[:8],
        )
        return "mirofish"
    return "research"


def after_finance(state: AgentState) -> str:
    route = state.get("route", {})
    if route.get("requires_simulation"):
        return "mirofish"
    if route.get("confidence", 0.5) < 0.45 and route.get(
        "complexity", "medium"
    ) in {"medium", "high", "very_high"}:
        return "mirofish"
    return "research"


def after_verifier(state: AgentState) -> str:
    verifier_result = state.get("verifier", {})
    if not verifier_result.get("passed", True) and state.get("replan_count", 0) < 1:
        return "repair"
    return "synthesizer"


def build_graph():
    g = StateGraph(AgentState)

    g.add_node("switchboard", switchboard_node)
    g.add_node("research", research_node)
    g.add_node("mirofish", mirofish_node_fn)
    g.add_node("finance", finance_node_fn)
    g.add_node("planner", planner_node)
    g.add_node("verifier", verifier_node)
    g.add_node("repair", repair_node)
    g.add_node("synthesizer", synthesizer_node)

    g.set_entry_point("switchboard")

    g.add_conditional_edges(
        "switchboard",
        after_switchboard,
        {"mirofish": "mirofish", "finance": "finance", "research": "research"},
    )

    g.add_edge("mirofish", "research")
    g.add_conditional_edges(
        "finance",
        after_finance,
        {"mirofish": "mirofish", "research": "research"},
    )
    g.add_edge("research", "planner")
    g.add_edge("planner", "verifier")
    g.add_conditional_edges(
        "verifier",
        after_verifier,
        {"repair": "repair", "synthesizer": "synthesizer"},
    )
    g.add_edge("repair", "planner")
    g.add_edge("synthesizer", END)
    return g.compile()


# Lazy graph compilation — prevents import-time crash if agents fail to load
_compiled_graph = None
_graph_build_error = None


def get_compiled_graph():
    """Lazy graph compilation with error handling. Call at runtime, not import."""
    global _compiled_graph, _graph_build_error
    if _compiled_graph is not None:
        return _compiled_graph
    if _graph_build_error is not None:
        raise RuntimeError(f"Graph compilation previously failed: {_graph_build_error}")
    try:
        _compiled_graph = build_graph()
        logger.info("LangGraph pipeline compiled successfully")
        return _compiled_graph
    except Exception as e:
        _graph_build_error = str(e)
        logger.error(f"LangGraph build failed: {e}")
        raise


def graph_status():
    """Return graph compilation status without triggering compilation."""
    if _compiled_graph is not None:
        return {"status": "ready"}
    if _graph_build_error:
        return {"status": "failed", "error": _graph_build_error}
    return {"status": "not_compiled"}


def run_case(user_input: str, context: dict = None) -> dict:
    """Run the optimized agent pipeline on user input."""
    graph = get_compiled_graph()
    case_id = str(uuid.uuid4())
    t0 = time.perf_counter()
    logger.info("Starting case %s", case_id)

    initial_state = {
        "case_id": case_id,
        "user_input": user_input,
        "route": {},
        "research": {},
        "planner": {},
        "verifier": {},
        "final": {},
        "errors": [],
        "replan_count": 0,
    }
    if context:
        initial_state["context"] = context

    result = graph.invoke(initial_state)

    elapsed = time.perf_counter() - t0
    logger.info("Case %s completed in %.2fs", case_id, elapsed)
    return result
