from openai import OpenAI

from app.config import (
    LLM_PROVIDER,
    DEEPSEEK_API_KEY,
    DEEPSEEK_BASE_URL,
    DEEPSEEK_CHAT_MODEL,
    DEEPSEEK_REASONER_MODEL,
)


class LLMProviderError(Exception):
    pass


def _get_client() -> OpenAI:
    if LLM_PROVIDER != "deepseek":
        raise LLMProviderError(f"Unsupported LLM_PROVIDER: {LLM_PROVIDER}")

    if not DEEPSEEK_API_KEY:
        raise LLMProviderError("DEEPSEEK_API_KEY is missing. Please add it in backend/.env.")

    return OpenAI(
        api_key=DEEPSEEK_API_KEY,
        base_url=DEEPSEEK_BASE_URL,
    )


def _pick_model(mode: str) -> str:
    if mode == "reasoner":
        return DEEPSEEK_REASONER_MODEL
    return DEEPSEEK_CHAT_MODEL


def call_model(
    prompt: str,
    mode: str = "chat",
    system_prompt: str | None = None,
    max_tokens: int = 1200,
) -> str:
    client = _get_client()
    model = _pick_model(mode)

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
        )
    except Exception as e:
        raise LLMProviderError(str(e))

    if not getattr(response, "choices", None):
        return "No response generated."

    message = response.choices[0].message
    content = getattr(message, "content", "") or ""

    if isinstance(content, list):
        try:
            return "\n".join(
                item.get("text", "") if isinstance(item, dict) else str(item)
                for item in content
            ).strip()
        except Exception:
            return str(content).strip()

    return str(content).strip()
