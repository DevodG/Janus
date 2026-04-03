import uuid
import time
import logging
from typing import TypedDict, Dict, Any

from langgraph.graph import StateGraph, START, END

from app.config import PROMPTS_DIR
from app.agents.switchboard import decide_route
from app.agents.research import run_research
from app.agents.planner import run_planner
from app.agents.verifier import run_verifier
from app.agents.synthesizer import run_synthesizer

logger = logging.getLogger(__name__)


# ── Prompt Loading with Production Version Support ────────────────────────────

_prompt_cache: Dict[str, str] = {}


def load_prompt(filename: str) -> str:
    """Load prompt from file, with caching."""
    if filename not in _prompt_cache:
        path = PROMPTS_DIR / filename
        _prompt_cache[filename] = path.read_text(encoding="utf-8")
    return _prompt_cache[filename]


def get_active_prompt(prompt_name: str, filename: str) -> str:
    """
    Get the active prompt, preferring a promoted production version.
    Falls back to the file-based prompt if none is promoted.
    """
    try:
        from app.routers.learning import learning_engine
        if learning_engine:
            production = learning_engine.get_active_prompt(prompt_name)
            if production:
                logger.debug(f"Using production prompt version for {prompt_name}")
                return production
    except Exception:
        pass

    return load_prompt(filename)


RESEARCH_PROMPT = load_prompt("research.txt")
PLANNER_PROMPT = load_prompt("planner.txt")
VERIFIER_PROMPT = load_prompt("verifier.txt")
SYNTHESIZER_PROMPT = load_prompt("synthesizer.txt")


class OrgState(TypedDict):
    case_id: str
    user_input: str
    route: Dict[str, Any]
    research: Dict[str, Any]
    planner: Dict[str, Any]
    verifier: Dict[str, Any]
    final: Dict[str, Any]


def empty_output(agent_name: str) -> Dict[str, Any]:
    return {
        "agent": agent_name,
        "summary": "",
        "details": {},
        "confidence": 0.0,
    }


# ── Node Functions with Timing ───────────────────────────────────────────────

def switchboard_node(state: OrgState):
    t0 = time.perf_counter()
    result = {"route": decide_route(state["user_input"])}
    elapsed = time.perf_counter() - t0
    logger.info(f"[{state['case_id'][:8]}] switchboard: {elapsed:.2f}s — mode={result['route'].get('execution_mode')}")
    return result


def research_node(state: OrgState):
    if state["route"].get("execution_mode") == "solo":
        return {"research": empty_output("research")}

    t0 = time.perf_counter()
    prompt = get_active_prompt("research", "research.txt")
    result = {"research": run_research(state["user_input"], prompt)}
    elapsed = time.perf_counter() - t0
    logger.info(f"[{state['case_id'][:8]}] research: {elapsed:.2f}s")
    return result


def planner_node(state: OrgState):
    if state["route"].get("execution_mode") == "solo":
        return {"planner": empty_output("planner")}

    t0 = time.perf_counter()
    prompt = get_active_prompt("planner", "planner.txt")
    result = {
        "planner": run_planner(
            state["user_input"],
            state["research"]["summary"],
            prompt,
        )
    }
    elapsed = time.perf_counter() - t0
    logger.info(f"[{state['case_id'][:8]}] planner: {elapsed:.2f}s")
    return result


def verifier_node(state: OrgState):
    if state["route"].get("execution_mode") != "deep":
        return {"verifier": empty_output("verifier")}

    t0 = time.perf_counter()
    prompt = get_active_prompt("verifier", "verifier.txt")
    result = {
        "verifier": run_verifier(
            state["user_input"],
            state["research"]["summary"],
            state["planner"]["summary"],
            prompt,
        )
    }
    elapsed = time.perf_counter() - t0
    logger.info(f"[{state['case_id'][:8]}] verifier: {elapsed:.2f}s")
    return result


def synthesizer_node(state: OrgState):
    t0 = time.perf_counter()
    prompt = get_active_prompt("synthesizer", "synthesizer.txt")
    result = {
        "final": run_synthesizer(
            state["user_input"],
            state["research"]["summary"],
            state["planner"]["summary"],
            state["verifier"]["summary"],
            prompt,
        )
    }
    elapsed = time.perf_counter() - t0
    logger.info(f"[{state['case_id'][:8]}] synthesizer: {elapsed:.2f}s")
    return result


graph = StateGraph(OrgState)
graph.add_node("switchboard", switchboard_node)
graph.add_node("research", research_node)
graph.add_node("planner", planner_node)
graph.add_node("verifier", verifier_node)
graph.add_node("synthesizer", synthesizer_node)

graph.add_edge(START, "switchboard")
graph.add_edge("switchboard", "research")
graph.add_edge("research", "planner")
graph.add_edge("planner", "verifier")
graph.add_edge("verifier", "synthesizer")
graph.add_edge("synthesizer", END)

compiled_graph = graph.compile()


def run_case(user_input: str):
    case_id = str(uuid.uuid4())
    t0 = time.perf_counter()
    logger.info("Starting case %s", case_id)

    result = compiled_graph.invoke(
        {
            "case_id": case_id,
            "user_input": user_input,
            "route": {},
            "research": {},
            "planner": {},
            "verifier": {},
            "final": {},
        }
    )

    elapsed = time.perf_counter() - t0
    logger.info("Case %s completed in %.2fs", case_id, elapsed)
    return result
