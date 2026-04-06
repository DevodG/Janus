"""
Unified model client for Janus.
Uses smart router: Gemini → Groq → OpenRouter → Cloudflare → Ollama.
All tiers use the OpenAI-compatible messages format.
Includes retry-with-backoff for 429 rate limits.
"""

import os, json, re, logging, time
import httpx
from typing import Any

logger = logging.getLogger(__name__)

OPENROUTER_BASE = "https://openrouter.ai/api/v1"

FREE_MODEL_LADDER = [
    "qwen/qwen3.6-plus:free",
    "nvidia/nemotron-3-super-120b-a12b:free",
    "minimax/minimax-m2.5:free",
    "stepfun/step-3.5-flash:free",
    "arcee-ai/trinity-mini:free",
]

OLLAMA_BASE = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
TIMEOUT = 90
OLLAMA_TIMEOUT = 30
MAX_RETRIES_PER_MODEL = 2
BASE_BACKOFF = 3


def _huggingface_call(messages: list[dict], **kwargs) -> str:
    """Call HuggingFace Inference API."""
    from app.agents.huggingface import hf_client

    return hf_client.chat(messages, **kwargs)


def _openrouter_call(messages: list[dict], model: str, **kwargs) -> str:
    """Single call to OpenRouter. Raises on non-200."""
    api_key = os.getenv("OPENROUTER_API_KEY", "")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY is not set in .env")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "HTTP-Referer": "https://huggingface.co",
        "X-Title": "Janus",
        "Content-Type": "application/json",
    }
    body = {"model": model, "messages": messages, "max_tokens": 4096, **kwargs}
    r = httpx.post(
        f"{OPENROUTER_BASE}/chat/completions",
        headers=headers,
        json=body,
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]


def _ollama_call(messages: list[dict], **kwargs) -> str:
    """Fallback: Ollama local via OpenAI-compatible endpoint."""
    base = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    if base.endswith("/api"):
        base = base[:-4]

    ollama_model = os.getenv(
        "OLLAMA_CHAT_MODEL", os.getenv("OLLAMA_MODEL", "qwen2.5-coder:3b")
    )
    body = {"model": ollama_model, "messages": messages, "stream": False}
    r = httpx.post(f"{base}/v1/chat/completions", json=body, timeout=OLLAMA_TIMEOUT)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]


def _call_with_retry(messages: list[dict], model: str, **kwargs) -> str:
    """
    Call OpenRouter with retry-on-429 backoff.
    Retries up to MAX_RETRIES_PER_MODEL times for rate limits,
    respecting the Retry-After header when present.
    """
    for attempt in range(MAX_RETRIES_PER_MODEL + 1):
        try:
            return _openrouter_call(messages, model, **kwargs)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                if attempt >= MAX_RETRIES_PER_MODEL:
                    raise  # Out of retries for this model

                # Respect Retry-After header, otherwise use exponential backoff
                retry_after = e.response.headers.get("retry-after")
                if retry_after:
                    try:
                        wait = min(float(retry_after), 30)  # Cap at 30s
                    except ValueError:
                        wait = BASE_BACKOFF * (2**attempt)
                else:
                    wait = BASE_BACKOFF * (2**attempt)

                logger.warning(
                    f"Rate limited on {model} (attempt {attempt + 1}/{MAX_RETRIES_PER_MODEL + 1}), "
                    f"waiting {wait:.1f}s..."
                )
                time.sleep(wait)
            else:
                raise  # Non-429 error, don't retry
    # Should not reach here, but just in case
    return _openrouter_call(messages, model, **kwargs)


def call_model(messages: list[dict], **kwargs) -> str:
    """
    Smart router: Gemini → Groq → OpenRouter → Cloudflare → Ollama.
    Uses unified router with rate limit tracking and automatic failover.
    Returns raw text. Never returns None.
    """
    try:
        from app.agents.smart_router import call_model as smart_call

        return smart_call(messages, **kwargs)
    except Exception as e:
        logger.error(f"Smart router failed: {e}")
        # Direct OpenRouter fallback if smart router fails
        errors = []
        for model in FREE_MODEL_LADDER:
            try:
                result = _call_with_retry(messages, model, **kwargs)
                logger.info(f"OpenRouter direct succeeded: {model}")
                return result
            except Exception as e2:
                errors.append(f"OpenRouter [{model}]: {e2}")

        # Ollama last resort
        try:
            return _ollama_call(messages, **kwargs)
        except Exception as e3:
            errors.append(f"Ollama: {e3}")

        raise RuntimeError("All model tiers failed:\n" + "\n".join(errors))


def safe_parse(text: str) -> dict:
    """
    Strip markdown fences, attempt JSON parse.
    On failure returns a structured error dict — NEVER returns None.
    Callers must check for 'error' key in the result.
    """
    cleaned = re.sub(r"```(?:json)?|```", "", text).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # Try extracting the first JSON-like block
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
    return {"error": "parse_failed", "raw": text[:800]}
