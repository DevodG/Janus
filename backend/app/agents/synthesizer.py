from app.agents._model import call_model, LLMProviderError


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

    try:
        text = call_model(prompt, mode="chat")
        return {
            "agent": "synthesizer",
            "summary": text,
            "details": {"model_mode": "chat"},
            "confidence": 0.82,
        }
    except LLMProviderError as e:
        return {
            "agent": "synthesizer",
            "summary": f"Error: {str(e)}",
            "details": {"error_type": "provider_error"},
            "confidence": 0.0,
        }
