from app.agents._model import call_model, LLMProviderError


def run_planner(user_input: str, research_output: str, prompt_template: str) -> dict:
    prompt = (
        f"{prompt_template}\n\n"
        f"User Request:\n{user_input}\n\n"
        f"Research Packet:\n{research_output}"
    )

    try:
        text = call_model(prompt, mode="chat")
        return {
            "agent": "planner",
            "summary": text,
            "details": {"model_mode": "chat"},
            "confidence": 0.75,
        }
    except LLMProviderError as e:
        return {
            "agent": "planner",
            "summary": f"Error: {str(e)}",
            "details": {"error_type": "provider_error"},
            "confidence": 0.0,
        }
