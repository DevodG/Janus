from app.config import SIMULATION_TRIGGER_KEYWORDS


def decide_route(user_input: str) -> dict:
    text = user_input.strip()
    lower = text.lower()
    words = len(text.split())

    task_family = "simulation" if any(k in lower for k in SIMULATION_TRIGGER_KEYWORDS) else "normal"

    if task_family == "simulation":
        execution_mode = "deep"
        complexity = "complex"
    elif words <= 5:
        execution_mode = "solo"
        complexity = "simple"
    elif words <= 25:
        execution_mode = "standard"
        complexity = "medium"
    else:
        execution_mode = "deep"
        complexity = "complex"

    return {
        "task_family": task_family,
        "complexity": complexity,
        "execution_mode": execution_mode,
        "risk_level": "medium" if execution_mode == "deep" else "low",
    }
