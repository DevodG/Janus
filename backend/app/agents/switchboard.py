def decide_route(user_input: str) -> dict:
    return {
        "use_research": True,
        "use_planner": True,
        "use_verifier": True,
        "use_synthesizer": True,
        "risk_level": "low",
        "task_type": "general",
    }
