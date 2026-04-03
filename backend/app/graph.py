import uuid
from typing import TypedDict, Dict, Any
import logging

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
    return path.read_text(encoding='utf-8')


RESEARCH_PROMPT = load_prompt('research.txt')
PLANNER_PROMPT = load_prompt('planner.txt')
VERIFIER_PROMPT = load_prompt('verifier.txt')
SYNTHESIZER_PROMPT = load_prompt('synthesizer.txt')


class OrgState(TypedDict):
    case_id: str
    user_input: str
    route: Dict[str, Any]
    research: Dict[str, Any]
    planner: Dict[str, Any]
    verifier: Dict[str, Any]
    final: Dict[str, Any]


def switchboard_node(state: OrgState):
    try:
        return {'route': decide_route(state['user_input'])}
    except Exception as e:
        logger.error(f"Error in switchboard: {e}")
        return {'route': {'error': str(e)}}


def research_node(state: OrgState):
    try:
        return {'research': run_research(state['user_input'], RESEARCH_PROMPT)}
    except Exception as e:
        logger.error(f"Error in research: {e}")
        return {'research': {'agent': 'research', 'summary': f'Error: {str(e)}', 'details': {}, 'confidence': 0.0}}


def planner_node(state: OrgState):
    try:
        return {
            'planner': run_planner(
                state['user_input'],
                state['research']['summary'],
                PLANNER_PROMPT,
            )
        }
    except Exception as e:
        logger.error(f"Error in planner: {e}")
        return {'planner': {'agent': 'planner', 'summary': f'Error: {str(e)}', 'details': {}, 'confidence': 0.0}}


def verifier_node(state: OrgState):
    try:
        return {
            'verifier': run_verifier(
                state['user_input'],
                state['research']['summary'],
                state['planner']['summary'],
                VERIFIER_PROMPT,
            )
        }
    except Exception as e:
        logger.error(f"Error in verifier: {e}")
        return {'verifier': {'agent': 'verifier', 'summary': f'Error: {str(e)}', 'details': {}, 'confidence': 0.0}}


def synthesizer_node(state: OrgState):
    try:
        return {
            'final': run_synthesizer(
                state['user_input'],
                state['research']['summary'],
                state['planner']['summary'],
                state['verifier']['summary'],
                SYNTHESIZER_PROMPT,
            )
        }
    except Exception as e:
        logger.error(f"Error in synthesizer: {e}")
        return {'final': {'agent': 'synthesizer', 'summary': f'Error: {str(e)}', 'details': {}, 'confidence': 0.0}}


graph = StateGraph(OrgState)

graph.add_node('switchboard', switchboard_node)
graph.add_node('research', research_node)
graph.add_node('planner', planner_node)
graph.add_node('verifier', verifier_node)
graph.add_node('synthesizer', synthesizer_node)

graph.add_edge(START, 'switchboard')
graph.add_edge('switchboard', 'research')
graph.add_edge('research', 'planner')
graph.add_edge('planner', 'verifier')
graph.add_edge('verifier', 'synthesizer')
graph.add_edge('synthesizer', END)

compiled_graph = graph.compile()


def run_case(user_input: str):
    case_id = str(uuid.uuid4())
    logger.info(f"Starting case {case_id} for input: {user_input[:50]}...")

    try:
        result = compiled_graph.invoke({
            'case_id': case_id,
            'user_input': user_input,
            'route': {},
            'research': {},
            'planner': {},
            'verifier': {},
            'final': {},
        })
        logger.info(f"Case {case_id} completed")
        return result
    except Exception as e:
        logger.error(f"Error in case {case_id}: {e}")
        raise
