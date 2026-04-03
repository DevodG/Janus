from app.agents._model import call_model, LLMProviderError
from app.services.external_sources import build_external_context


def run_research(user_input: str, prompt_template: str) -> dict:
    external_context = build_external_context(user_input)

    prompt = (
        f"{prompt_template}\n\n"
        f"User Request:\n{user_input}\n\n"
        f"External Context:\n{external_context}"
    )

    try:
        text = call_model(prompt, mode="chat")
        return {
            "agent": "research",
            "summary": text,
            "details": {"external_context_used": external_context != "No external API context available."},
            "confidence": 0.72,
        }
    except LLMProviderError as e:
        return {
            "agent": "research",
            "summary": f"Error: {str(e)}",
            "details": {"error_type": "provider_error"},
            "confidence": 0.0,
        }
