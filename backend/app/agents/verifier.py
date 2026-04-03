from app.agents._model import call_model


def run_verifier(user_input: str, research_output: str, planner_output: str, prompt_template: str) -> dict:
    prompt = (
        f"{prompt_template}\n\n"
        f"User Request:\n{user_input}\n\n"
        f"Research Packet:\n{research_output}\n\n"
        f"Planner Output:\n{planner_output}"
    )

    text = call_model(prompt)

    return {
        "agent": "verifier",
        "summary": text,
        "details": {},
        "confidence": 0.75,
    }
