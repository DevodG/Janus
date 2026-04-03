from typing import Dict, Any, List

from app.config import PROMPTS_DIR
from app.agents.switchboard import decide_route
from app.agents.research import run_research
from app.agents.planner import run_planner
from app.agents.verifier import run_verifier
from app.agents.synthesizer import run_synthesizer


AGENTS = {
    "switchboard": {
        "purpose": "Route and classify the incoming user request.",
        "prompt_name": None,
        "inputs_required": ["user_input"],
    },
    "research": {
        "purpose": "Extract facts, assumptions, and open questions.",
        "prompt_name": "research",
        "inputs_required": ["user_input"],
    },
    "planner": {
        "purpose": "Create a practical plan from the research packet.",
        "prompt_name": "planner",
        "inputs_required": ["user_input", "research_output"],
    },
    "verifier": {
        "purpose": "Critique the planner output and find weak spots.",
        "prompt_name": "verifier",
        "inputs_required": ["user_input", "research_output", "planner_output"],
    },
    "synthesizer": {
        "purpose": "Combine all previous outputs into one final answer.",
        "prompt_name": "synthesizer",
        "inputs_required": ["user_input", "research_output", "planner_output", "verifier_output"],
    },
}


def _load_prompt(name: str) -> str:
    path = PROMPTS_DIR / f"{name}.txt"
    return path.read_text(encoding="utf-8")


def list_agents() -> List[Dict[str, Any]]:
    return [
        {
            "name": name,
            "purpose": meta["purpose"],
            "prompt_name": meta["prompt_name"],
            "inputs_required": meta["inputs_required"],
        }
        for name, meta in AGENTS.items()
    ]


def get_agent(name: str) -> Dict[str, Any] | None:
    meta = AGENTS.get(name)
    if not meta:
        return None

    return {
        "name": name,
        "purpose": meta["purpose"],
        "prompt_name": meta["prompt_name"],
        "inputs_required": meta["inputs_required"],
    }


def run_single_agent(
    agent: str,
    user_input: str,
    research_output: str | None = None,
    planner_output: str | None = None,
    verifier_output: str | None = None,
) -> Dict[str, Any]:
    if agent == "switchboard":
        route = decide_route(user_input)
        return {
            "agent": "switchboard",
            "summary": str(route),
            "details": route,
            "confidence": 1.0,
        }

    if agent == "research":
        return run_research(user_input, _load_prompt("research"))

    if agent == "planner":
        if not research_output:
            raise ValueError("planner requires research_output")
        return run_planner(user_input, research_output, _load_prompt("planner"))

    if agent == "verifier":
        if not research_output or not planner_output:
            raise ValueError("verifier requires research_output and planner_output")
        return run_verifier(
            user_input,
            research_output,
            planner_output,
            _load_prompt("verifier"),
        )

    if agent == "synthesizer":
        if not research_output or not planner_output or not verifier_output:
            raise ValueError("synthesizer requires research_output, planner_output, and verifier_output")
        return run_synthesizer(
            user_input,
            research_output,
            planner_output,
            verifier_output,
            _load_prompt("synthesizer"),
        )

    raise ValueError(f"Unknown agent: {agent}")
