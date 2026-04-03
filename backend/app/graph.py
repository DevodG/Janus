import uuid
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


def load_prompt(filename: str) -> str:
    path = PROMPTS_DIR / filename
    return path.read_text(encoding="utf-8")


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


def switchboard_node(state: OrgState):
    return {"route": decide_route(state["user_input"])}


def research_node(state: OrgState):
    if state["route"].get("execution_mode") == "solo":
        return {"research": empty_output("research")}
    return {"research": run_research(state["user_input"], RESEARCH_PROMPT)}


def planner_node(state: OrgState):
    if state["route"].get("execution_mode") == "solo":
        return {"planner": empty_output("planner")}
    return {
        "planner": run_planner(
            state["user_input"],
            state["research"]["summary"],
            PLANNER_PROMPT,
        )
    }


def verifier_node(state: OrgState):
    if state["route"].get("execution_mode") != "deep":
        return {"verifier": empty_output("verifier")}
    return {
        "verifier": run_verifier(
            state["user_input"],
            state["research"]["summary"],
            state["planner"]["summary"],
            VERIFIER_PROMPT,
        )
    }


def synthesizer_node(state: OrgState):
    return {
        "final": run_synthesizer(
            state["user_input"],
            state["research"]["summary"],
            state["planner"]["summary"],
            state["verifier"]["summary"],
            SYNTHESIZER_PROMPT,
        )
    }


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

    logger.info("Case %s completed", case_id)
    return result
