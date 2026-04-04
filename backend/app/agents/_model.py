"""
Unified model client for MiroOrg v2.
Priority: OpenRouter free → Ollama fallback → raise with diagnostics.
All tiers use the OpenAI-compatible messages format.
"""

import os, json, re, logging
import httpx
from typing import Any

logger = logging.getLogger(__name__)

OPENROUTER_BASE   = "https://openrouter.ai/api/v1"
OPENROUTER_KEY    = os.getenv("OPENROUTER_API_KEY", "")

# Pinned free models in preference order (all have :free suffix = zero cost)
FREE_MODEL_LADDER = [
    "nvidia/llama-3.1-nemotron-ultra-253b:free",   # best reasoning, large context
    "meta-llama/llama-3.3-70b-instruct:free",       # reliable, GPT-4 class
    "deepseek/deepseek-r1:free",                    # strong chain-of-thought
    "openrouter/free",                              # random free as last resort
]

OLLAMA_BASE       = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL      = os.getenv("OLLAMA_MODEL", "llama3.2")   # user configures
TIMEOUT           = 120


def _openrouter_call(messages: list[dict], model: str, **kwargs) -> str:
    """Single call to OpenRouter. Raises on non-200."""
    headers = {
        "Authorization": f"Bearer {OPENROUTER_KEY}",
        "HTTP-Referer": "https://miroorg.local",
        "X-Title": "MiroOrg v2",
        "Content-Type": "application/json",
    }
    body = {"model": model, "messages": messages, "max_tokens": 2048, **kwargs}
    r = httpx.post(f"{OPENROUTER_BASE}/chat/completions",
                   headers=headers, json=body, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]


def _ollama_call(messages: list[dict], **kwargs) -> str:
    """Fallback: Ollama local via OpenAI-compatible endpoint."""
    body = {"model": OLLAMA_MODEL, "messages": messages, "stream": False}
    r = httpx.post(f"{OLLAMA_BASE}/v1/chat/completions",
                   json=body, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]


def call_model(messages: list[dict], **kwargs) -> str:
    """
    Try OpenRouter free models in ladder order, then Ollama.
    Returns raw text. Never returns None — raises RuntimeError with full diagnostics
    so the caller can write a structured error dict instead of silently propagating None.
    """
    errors = []
    for model in FREE_MODEL_LADDER:
        try:
            result = _openrouter_call(messages, model, **kwargs)
            logger.info(f"Model call succeeded: {model}")
            return result
        except Exception as e:
            errors.append(f"OpenRouter [{model}]: {e}")
            logger.warning(f"OpenRouter [{model}] failed: {e}")

    # Ollama fallback
    try:
        result = _ollama_call(messages, **kwargs)
        logger.info(f"Ollama fallback succeeded: {OLLAMA_MODEL}")
        return result
    except Exception as e:
        errors.append(f"Ollama [{OLLAMA_MODEL}]: {e}")
        logger.error(f"Ollama fallback failed: {e}")

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
