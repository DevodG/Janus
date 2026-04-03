from app.agents._model import call_model, LLMProviderError


def run_verifier(user_input: str, research_output: str, planner_output: str, prompt_template: str) -> dict:
    prompt = (
        f"{prompt_template}\n\n"
        f"User Request:\n{user_input}\n\n"
        f"Research Packet:\n{research_output}\n\n"
        f"Planner Output:\n{planner_output}"
    )

    try:
        text = call_model(prompt, mode="reasoner")
        return {
            "agent": "verifier",
            "summary": text,
            "details": {"model_mode": "reasoner"},
            "confidence": 0.79,
        }
    except LLMProviderError as e:
        return {
            "agent": "verifier",
            "summary": f"Error: {str(e)}",
            "details": {"error_type": "provider_error"},
            "confidence": 0.0,
        }
