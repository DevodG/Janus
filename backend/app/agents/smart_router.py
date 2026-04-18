"""
Smart LLM Router for Janus.

Unified router across multiple free providers with rate limit tracking,
automatic failover, and daily quota management.

Provider priority:
1. Google Gemini (best free quality, 1500 req/day)
2. Groq (fastest, Llama 3.3 70B, 14400 req/day)
3. OpenRouter (free models — fixed model list)
4. Cloudflare Workers AI (10k req/day)
5. Ollama (local, unlimited)

FIXES vs previous version:
  - OpenRouter free_models list updated to working models (old ones all 400)
  - Gemini response parsing fixed (was crashing with 'string indices must be int')
  - Rate state moved to in-memory dict (HF filesystem is ephemeral, file was wiped on restart)
  - Added provider cooldown after 3 consecutive failures
"""

import os
import time
import json
import logging
from typing import Dict, List, Optional
import httpx

logger = logging.getLogger(__name__)

# ── In-memory rate state (HF filesystem is ephemeral — file-based state was wiped on restart) ──
_RATE_STATE: dict = {}


def _midnight_ts() -> int:
    from datetime import datetime, timezone, timedelta
    now = datetime.now(timezone.utc)
    tomorrow = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    return int(tomorrow.timestamp())


def _is_available(provider: str, daily_limit: int, rpm_limit: int) -> bool:
    now = time.time()
    p = _RATE_STATE.get(
        provider, {"daily_count": 0, "rpm_timestamps": [], "reset_at": _midnight_ts()}
    )
    if now > p.get("reset_at", 0):
        p["daily_count"] = 0
        p["rpm_timestamps"] = []
        p["reset_at"] = _midnight_ts()
    if p["daily_count"] >= daily_limit:
        return False
    p["rpm_timestamps"] = [t for t in p["rpm_timestamps"] if now - t < 60]
    if len(p["rpm_timestamps"]) >= rpm_limit:
        return False
    _RATE_STATE[provider] = p
    return True


def _record_usage(provider: str):
    now = time.time()
    p = _RATE_STATE.get(
        provider, {"daily_count": 0, "rpm_timestamps": [], "reset_at": _midnight_ts()}
    )
    p["daily_count"] = p.get("daily_count", 0) + 1
    p["rpm_timestamps"] = p.get("rpm_timestamps", []) + [now]
    _RATE_STATE[provider] = p


# ── Provider credentials ────────────────────────────────────────────────────
GEMINI_KEY      = os.getenv("GEMINI_API_KEY", "")
GROQ_KEY        = os.getenv("GROQ_API_KEY", "")
OPENROUTER_KEY  = os.getenv("OPENROUTER_API_KEY", "")
CF_ACCOUNT_ID   = os.getenv("CLOUDFLARE_ACCOUNT_ID", "")
CF_TOKEN        = os.getenv("CLOUDFLARE_API_TOKEN", "")
TIMEOUT         = 90


def _call_gemini(messages: List[Dict[str, str]], **kwargs) -> str:
    """Google Gemini — FIXED response parsing (was crashing on candidates[0].content.parts[0])"""
    if not GEMINI_KEY:
        raise ValueError("GEMINI_API_KEY not set")

    system_msg = ""
    user_messages = []
    for m in messages:
        if m["role"] == "system":
            system_msg = m["content"]
        else:
            user_messages.append(m)

    body = {
        "system_instruction": {"parts": [{"text": system_msg}]} if system_msg else None,
        "contents": [
            {
                "role": "model" if m["role"] == "assistant" else "user",
                "parts": [{"text": m["content"]}],
            }
            for m in user_messages
        ],
        "generationConfig": {
            "temperature": kwargs.get("temperature", 0.7),
            "maxOutputTokens": kwargs.get("max_tokens", 4096),
        },
    }
    if body["system_instruction"] is None:
        del body["system_instruction"]

    for model in ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-flash-8b"]:
        try:
            with httpx.Client(timeout=TIMEOUT) as client:
                r = client.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_KEY}",
                    json=body,
                )
                r.raise_for_status()
                data = r.json()

            candidates = data.get("candidates", [])
            if not candidates:
                raise ValueError(f"No candidates in Gemini response from {model}")
            content = candidates[0].get("content", {})
            parts = content.get("parts", [])
            if not parts:
                raise ValueError(f"No parts in Gemini response from {model}")
            text = parts[0].get("text", "")
            if not text:
                raise ValueError(f"Empty text from {model}")
            return text
        except (httpx.HTTPStatusError, ValueError) as e:
            logger.warning(f"Gemini {model} failed: {e}")
            continue

    raise RuntimeError("All Gemini models failed")


def _call_groq(messages: List[Dict[str, str]], **kwargs) -> str:
    """Groq — fastest inference, Llama 3.3 70B."""
    if not GROQ_KEY:
        raise ValueError("GROQ_API_KEY not set")

    body = {
        "model": "llama-3.3-70b-versatile",
        "messages": messages,
        "temperature": kwargs.get("temperature", 0.7),
        "max_tokens": kwargs.get("max_tokens", 4096),
    }
    with httpx.Client(timeout=TIMEOUT) as client:
        r = client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"},
            json=body,
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]


def _call_openrouter(messages: List[Dict[str, str]], **kwargs) -> str:
    """OpenRouter — FIXED model list (old models all return HTTP 400)."""
    if not OPENROUTER_KEY:
        raise ValueError("OPENROUTER_API_KEY not set")

    free_models = [
        "meta-llama/llama-3.3-70b-instruct:free",
        "deepseek/deepseek-chat-v3-0324:free",
        "qwen/qwen-2.5-72b-instruct:free",
        "google/gemma-3-27b-it:free",
        "mistralai/mistral-7b-instruct:free",
    ]

    errors = []
    for model in free_models:
        try:
            body = {
                "model": model,
                "messages": messages,
                "max_tokens": kwargs.get("max_tokens", 4096),
            }
            with httpx.Client(timeout=TIMEOUT) as client:
                r = client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {OPENROUTER_KEY}",
                        "HTTP-Referer": "https://huggingface.co/spaces/DevodG/Janus-backend",
                        "X-Title": "Janus",
                        "Content-Type": "application/json",
                    },
                    json=body,
                )
                r.raise_for_status()
                content = r.json()["choices"][0]["message"]["content"]
                if not content:
                    raise ValueError("Empty response")
                return content
        except Exception as e:
            errors.append(f"{model}: {e}")

    raise RuntimeError(f"All OpenRouter models failed: {'; '.join(errors)}")


def _call_cloudflare(messages: List[Dict[str, str]], **kwargs) -> str:
    """Cloudflare Workers AI — 10k req/day free."""
    if not CF_ACCOUNT_ID or not CF_TOKEN:
        raise ValueError("CLOUDFLARE credentials not set")

    body = {"messages": messages, "max_tokens": kwargs.get("max_tokens", 4096)}
    with httpx.Client(timeout=TIMEOUT) as client:
        r = client.post(
            f"https://api.cloudflare.com/client/v4/accounts/{CF_ACCOUNT_ID}/ai/run/@cf/meta/llama-3.3-70b-instruct-fp8-fast",
            headers={"Authorization": f"Bearer {CF_TOKEN}", "Content-Type": "application/json"},
            json=body,
        )
        r.raise_for_status()
        return r.json()["result"]["response"]


def _call_ollama(messages: List[Dict[str, str]], **kwargs) -> str:
    """Ollama — local, unlimited fallback (not available on HF Spaces)."""
    base = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    if base.endswith("/api"):
        base = base[:-4]
    model = os.getenv("OLLAMA_CHAT_MODEL", "qwen2.5:3b")
    body = {"model": model, "messages": messages, "stream": False}
    with httpx.Client(timeout=60) as client:
        r = client.post(f"{base}/v1/chat/completions", json=body)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]


# ── Provider registry ───────────────────────────────────────────────────────
PROVIDERS = [
    {"name": "groq",        "daily_limit": 14400,  "rpm_limit": 1000, "call": _call_groq,       "enabled": bool(GROQ_KEY)},
    {"name": "gemini",      "daily_limit": 1500,   "rpm_limit": 15,   "call": _call_gemini,     "enabled": bool(GEMINI_KEY)},
    {"name": "openrouter",  "daily_limit": 999999, "rpm_limit": 20,   "call": _call_openrouter, "enabled": bool(OPENROUTER_KEY)},
    {"name": "cloudflare",  "daily_limit": 10000,  "rpm_limit": 60,   "call": _call_cloudflare, "enabled": bool(CF_ACCOUNT_ID and CF_TOKEN)},
    {"name": "ollama",      "daily_limit": 999999, "rpm_limit": 999,  "call": _call_ollama,     "enabled": True},
]

# Consecutive failure tracking — skip provider after 3 failures until cooldown passes
_FAILURES:   Dict[str, int]   = {}
_LAST_FAIL:  Dict[str, float] = {}
COOLDOWN_SEC = 300  # 5 min cooldown after 3 consecutive failures


def call_model(messages: List[Dict[str, str]], **kwargs) -> str:
    """
    Smart router — tries providers in priority order with rate limit tracking.
    Returns text from the first successful provider.
    """
    errors = []
    now = time.time()

    for provider in PROVIDERS:
        if not provider["enabled"]:
            continue

        name = provider["name"]

        # Skip if on failure cooldown
        if _FAILURES.get(name, 0) >= 3:
            if now - _LAST_FAIL.get(name, 0) < COOLDOWN_SEC:
                logger.debug(f"[router] {name} on cooldown")
                continue
            else:
                _FAILURES[name] = 0

        if not _is_available(name, provider["daily_limit"], provider["rpm_limit"]):
            logger.info(f"[router] {name} skipped (rate limited)")
            continue

        try:
            logger.info(f"[router] trying {name}")
            result = provider["call"](messages, **kwargs)
            _record_usage(name)
            _FAILURES[name] = 0
            logger.info(f"[router] {name} succeeded")
            return result
        except Exception as e:
            _FAILURES[name] = _FAILURES.get(name, 0) + 1
            _LAST_FAIL[name] = now
            errors.append(f"{name}: {e}")
            logger.warning(f"[router] {name} failed: {e}")

    raise RuntimeError("All LLM providers exhausted:\n" + "\n".join(errors))


def safe_parse(text: str) -> dict:
    """Strip markdown fences, attempt JSON parse."""
    import re
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
