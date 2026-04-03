from app.agents._model import call_model


def run_research(user_input: str, prompt_template: str) -> dict:
    prompt = f"{prompt_template}\n\nUser Request:\n{user_input}"
    text = call_model(prompt)

    return {
        "agent": "research",
        "summary": text,
        "details": {},
        "confidence": 0.70,
    }
