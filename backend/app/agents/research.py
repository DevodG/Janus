from app.agents._model import call_model, LLMProviderError


def run_research(user_input: str, prompt_template: str) -> dict:
    prompt = f"{prompt_template}\n\nUser Request:\n{user_input}"

    try:
        text = call_model(prompt, mode="chat")
        return {
            "agent": "research",
            "summary": text,
            "details": {"model_mode": "chat"},
            "confidence": 0.70,
        }
    except LLMProviderError as e:
        return {
            "agent": "research",
            "summary": f"Error: {str(e)}",
            "details": {"error_type": "provider_error"},
            "confidence": 0.0,
        }
