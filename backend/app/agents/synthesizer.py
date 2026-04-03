from app.agents._model import call_model


def run_synthesizer(
    user_input: str,
    research_output: str,
    planner_output: str,
    verifier_output: str,
    prompt_template: str
) -> dict:
    prompt = (
        f"{prompt_template}\n\n"
        f"User Request:\n{user_input}\n\n"
        f"Research Packet:\n{research_output}\n\n"
        f"Planner Output:\n{planner_output}\n\n"
        f"Verifier Output:\n{verifier_output}"
    )

    text = call_model(prompt)

    return {
        "agent": "synthesizer",
        "summary": text,
        "details": {},
        "confidence": 0.80,
    }
