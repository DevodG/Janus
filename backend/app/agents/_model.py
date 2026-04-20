"""
Unified model client for Janus.
Smart router: Gemini → Groq → OpenRouter → Cloudflare → Ollama.
All tiers use the OpenAI-compatible messages format.
Includes retry-with-backoff for 429 rate limits.
"""

import os, json, re, logging, time
import httpx
from typing import Any

logger = logging.getLogger(__name__)

OPENROUTER_BASE = "https://openrouter.ai/api/v1"

# FIXED: replaced dead/renamed model IDs (all were returning HTTP 400)
FREE_MODEL_LADDER = [
    "meta-llama/llama-3.3-70b-instruct:free",
    "deepseek/deepseek-chat-v3-0324:free",
    "qwen/qwen-2.5-72b-instruct:free",
    "google/gemma-3-27b-it:free",
    "mistralai/mistral-7b-instruct:free",
]

OLLAMA_BASE = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
TIMEOUT = 90
OLLAMA_TIMEOUT = 30
MAX_RETRIES_PER_MODEL = 2
BASE_BACKOFF = 3
OLLAMA_REACHABILITY_TIMEOUT = 1.5


def _ollama_is_reachable() -> bool:
    base = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    if base.endswith("/api"):
        probe_url = f"{base}/tags"
    else:
        probe_url = f"{base}/api/tags"
    try:
        with httpx.Client(timeout=OLLAMA_REACHABILITY_TIMEOUT) as client:
            response = client.get(probe_url)
            return response.status_code < 500
    except Exception:
        return False


def _huggingface_call(messages: list[dict], **kwargs) -> str:
    """Call HuggingFace Inference API."""
    from app.agents.huggingface import hf_client
    return hf_client.chat(messages, **kwargs)


def _openrouter_call(messages: list[dict], model: str, **kwargs) -> str:
    """Single call to OpenRouter. Raises on non-200."""
    api_key = os.getenv("OPENROUTER_API_KEY", "")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY is not set")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "HTTP-Referer": "https://huggingface.co/spaces/DevodG/Janus-backend",
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
    data = r.json()
    content = data["choices"][0]["message"]["content"]
    if not content:
        raise ValueError(f"Empty response from {model}")
    return content


def _ollama_call(messages: list[dict], **kwargs) -> str:
    """Fallback: Ollama local via OpenAI-compatible endpoint."""
    if not _ollama_is_reachable():
        raise RuntimeError("Ollama server is not reachable")

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
    Retries up to MAX_RETRIES_PER_MODEL times for rate limits.
    """
    for attempt in range(MAX_RETRIES_PER_MODEL + 1):
        try:
            return _openrouter_call(messages, model, **kwargs)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                if attempt >= MAX_RETRIES_PER_MODEL:
                    raise
                retry_after = e.response.headers.get("retry-after")
                if retry_after:
                    try:
                        wait = min(float(retry_after), 30)
                    except ValueError:
                        wait = BASE_BACKOFF * (2 ** attempt)
                else:
                    wait = BASE_BACKOFF * (2 ** attempt)
                logger.warning(
                    f"Rate limited on {model} (attempt {attempt + 1}/{MAX_RETRIES_PER_MODEL + 1}), "
                    f"waiting {wait:.1f}s..."
                )
                time.sleep(wait)
            else:
                raise
    return _openrouter_call(messages, model, **kwargs)


def call_model(messages: list[dict], **kwargs) -> str:
    """
    Smart router: Gemini → Groq → OpenRouter → Cloudflare → Ollama.
    Returns raw text. Never returns None.
    """
    try:
        from app.agents.smart_router import call_model as smart_call
        return smart_call(messages, **kwargs)
    except Exception as e:
        logger.error(f"Smart router failed: {e}")

    # Direct OpenRouter fallback with fixed model list
    errors = []
    if os.getenv("OPENROUTER_API_KEY", ""):
        for model in FREE_MODEL_LADDER:
            try:
                result = _call_with_retry(messages, model, **kwargs)
                logger.info(f"OpenRouter direct succeeded: {model}")
                return result
            except Exception as e2:
                errors.append(f"OpenRouter [{model}]: {e2}")
    else:
        errors.append("OpenRouter: OPENROUTER_API_KEY is not set")

    # Ollama last resort
    if os.getenv("OLLAMA_ENABLED", "true").lower() == "true":
        try:
            return _ollama_call(messages, **kwargs)
        except Exception as e3:
            errors.append(f"Ollama: {e3}")
    else:
        errors.append("Ollama: disabled")

    raise RuntimeError("All model tiers failed:\n" + "\n".join(errors))


def safe_parse(text: str) -> dict:
    """
    Strip markdown fences, attempt JSON parse.
    On failure returns a structured error dict — NEVER returns None.
    """
    cleaned = re.sub(r"```(?:json)?|```", "", text).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
    return {"error": "parse_failed", "raw": text[:800]}
