from __future__ import annotations
from typing import Dict, Any, List, Optional

from app.config import PROMPTS_DIR
from app.agents import switchboard
from app.agents import research
from app.agents import planner
from app.agents import verifier
from app.agents import synthesizer


AGENTS = {
    "switchboard": {
        "purpose": "Route and classify incoming work into normal or simulation flows.",
        "prompt_name": None,
        "inputs_required": ["user_input"],
    },
    "research": {
        "purpose": "Use prompts plus external APIs to gather facts and assumptions.",
        "prompt_name": "research",
        "inputs_required": ["user_input"],
    },
    "planner": {
        "purpose": "Build the working plan from the research packet.",
        "prompt_name": "planner",
        "inputs_required": ["user_input", "research_output"],
    },
    "verifier": {
        "purpose": "Challenge the plan and look for weak reasoning or gaps.",
        "prompt_name": "verifier",
        "inputs_required": ["user_input", "research_output", "planner_output"],
    },
    "synthesizer": {
        "purpose": "Merge outputs into one final answer.",
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


def get_agent(name: str) -> Optional[Dict[str, Any]]:
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
    research_output: Optional[str] = None,
    planner_output: Optional[str] = None,
    verifier_output: Optional[str] = None,
) -> Dict[str, Any]:
    state = {
        "user_input": user_input,
        "research": research_output or {},
        "planner": planner_output or {},
        "verifier": verifier_output or {}
    }

    if agent == "switchboard":
        route = switchboard.run(state).get("route", {})
        return {
            "agent": "switchboard",
            "summary": "Router completed",
            "details": route,
            "confidence": 1.0,
        }

    if agent == "research":
        return research.run(state).get("research", {})

    if agent == "planner":
        return planner.run(state).get("planner", {})

    if agent == "verifier":
        return verifier.run(state).get("verifier", {})

    if agent == "synthesizer":
        return synthesizer.run(state).get("final", {})

    raise ValueError(f"Unknown agent: {agent}")
