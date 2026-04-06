"""
Smart LLM Router for Janus.

Unified router across multiple free providers with rate limit tracking,
automatic failover, and daily quota management.

Provider priority:
1. Google Gemini 2.0 Flash (best free quality, 1500 req/day)
2. Groq (fastest, Llama 3.3 70B, 14400 req/day)
3. OpenRouter (free models, effectively unlimited)
4. Cloudflare Workers AI (10k req/day)
5. Ollama (local, unlimited)
"""

import os
import time
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any, Optional

import httpx

logger = logging.getLogger(__name__)

# ─── Rate Limit State ────────────────────────────────────────────────────────

STATE_DIR = Path(__file__).parent.parent.parent / "data" / "router_state"
STATE_DIR.mkdir(parents=True, exist_ok=True)
STATE_FILE = STATE_DIR / "provider_state.json"


def _midnight_ts() -> int:
    now = datetime.now(timezone.utc)
    tomorrow = now.replace(hour=0, minute=0, second=0, microsecond=0)
    from datetime import timedelta

    tomorrow = tomorrow + timedelta(days=1)
    return int(tomorrow.timestamp())


def _load_state() -> dict:
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_state(state: dict):
    try:
        with open(STATE_FILE, "w") as f:
            json.dump(state, f, indent=2)
    except Exception:
        pass


def _is_available(provider: str, daily_limit: int, rpm_limit: int, state: dict) -> bool:
    now = time.time()
    p = state.get(
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

    state[provider] = p
    return True


def _record_usage(provider: str, state: dict):
    now = time.time()
    p = state.get(
        provider, {"daily_count": 0, "rpm_timestamps": [], "reset_at": _midnight_ts()}
    )
    p["daily_count"] = p.get("daily_count", 0) + 1
    p["rpm_timestamps"] = p.get("rpm_timestamps", []) + [now]
    state[provider] = p
    _save_state(state)


# ─── Provider Implementations ────────────────────────────────────────────────

GEMINI_KEY = os.getenv("GEMINI_API_KEY", "")
GROQ_KEY = os.getenv("GROQ_API_KEY", "")
OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY", "")
CF_ACCOUNT_ID = os.getenv("CLOUDFLARE_ACCOUNT_ID", "")
CF_TOKEN = os.getenv("CLOUDFLARE_API_TOKEN", "")

TIMEOUT = 90


def _call_gemini(messages: List[Dict[str, str]], **kwargs) -> str:
    """Google Gemini 2.0 Flash — best free quality."""
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
        "system_instruction": {"parts": [{"text": system_msg}]},
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

    with httpx.Client(timeout=TIMEOUT) as client:
        r = client.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_KEY}",
            json=body,
        )
        r.raise_for_status()
        data = r.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]


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
            headers={
                "Authorization": f"Bearer {GROQ_KEY}",
                "Content-Type": "application/json",
            },
            json=body,
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]


def _call_openrouter(messages: List[Dict[str, str]], **kwargs) -> str:
    """OpenRouter — free model ladder."""
    if not OPENROUTER_KEY:
        raise ValueError("OPENROUTER_API_KEY not set")

    free_models = [
        "qwen/qwen3.6-plus:free",
        "nvidia/nemotron-3-super-120b-a12b:free",
        "minimax/minimax-m2.5:free",
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
                        "HTTP-Referer": "https://huggingface.co",
                        "X-Title": "Janus",
                        "Content-Type": "application/json",
                    },
                    json=body,
                )
                r.raise_for_status()
                return r.json()["choices"][0]["message"]["content"]
        except Exception as e:
            errors.append(f"{model}: {e}")

    raise RuntimeError(f"All OpenRouter models failed: {'; '.join(errors)}")


def _call_cloudflare(messages: List[Dict[str, str]], **kwargs) -> str:
    """Cloudflare Workers AI — 10k req/day free."""
    if not CF_ACCOUNT_ID or not CF_TOKEN:
        raise ValueError("CLOUDFLARE_ACCOUNT_ID or CLOUDFLARE_API_TOKEN not set")

    body = {
        "messages": messages,
        "max_tokens": kwargs.get("max_tokens", 4096),
    }

    with httpx.Client(timeout=TIMEOUT) as client:
        r = client.post(
            f"https://api.cloudflare.com/client/v4/accounts/{CF_ACCOUNT_ID}/ai/run/@cf/meta/llama-3.3-70b-instruct-fp8-fast",
            headers={
                "Authorization": f"Bearer {CF_TOKEN}",
                "Content-Type": "application/json",
            },
            json=body,
        )
        r.raise_for_status()
        data = r.json()
        return data["result"]["response"]


def _call_ollama(messages: List[Dict[str, str]], **kwargs) -> str:
    """Ollama — local, unlimited fallback."""
    base = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    if base.endswith("/api"):
        base = base[:-4]

    model = os.getenv("OLLAMA_CHAT_MODEL", "qwen2.5:3b")
    body = {
        "model": model,
        "messages": messages,
        "stream": False,
    }

    with httpx.Client(timeout=60) as client:
        r = client.post(f"{base}/v1/chat/completions", json=body)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]


# ─── Provider Registry ───────────────────────────────────────────────────────

PROVIDERS = [
    {
        "name": "groq",
        "daily_limit": 14400,
        "rpm_limit": 1000,
        "call": _call_groq,
        "enabled": bool(GROQ_KEY),
    },
    {
        "name": "gemini",
        "daily_limit": 1500,
        "rpm_limit": 15,
        "call": _call_gemini,
        "enabled": bool(GEMINI_KEY),
    },
    {
        "name": "openrouter",
        "daily_limit": 999999,
        "rpm_limit": 20,
        "call": _call_openrouter,
        "enabled": bool(OPENROUTER_KEY),
    },
    {
        "name": "cloudflare",
        "daily_limit": 10000,
        "rpm_limit": 60,
        "call": _call_cloudflare,
        "enabled": bool(CF_ACCOUNT_ID and CF_TOKEN),
    },
    {
        "name": "ollama",
        "daily_limit": 999999,
        "rpm_limit": 999999,
        "call": _call_ollama,
        "enabled": True,
    },
]


def call_model(messages: List[Dict[str, str]], **kwargs) -> str:
    """
    Smart router — tries providers in priority order with rate limit tracking.
    Returns text from the first successful provider.
    """
    state = _load_state()
    errors = []

    for provider in PROVIDERS:
        if not provider["enabled"]:
            continue

        name = provider["name"]
        if not _is_available(
            name, provider["daily_limit"], provider["rpm_limit"], state
        ):
            logger.info(f"[router] {name} skipped (rate limited)")
            continue

        try:
            logger.info(f"[router] trying {name}")
            result = provider["call"](messages, **kwargs)
            _record_usage(name, state)
            logger.info(f"[router] {name} succeeded")
            return result
        except Exception as e:
            errors.append(f"{name}: {e}")
            logger.warning(f"[router] {name} failed: {e}")

    raise RuntimeError(f"All LLM providers exhausted:\n" + "\n".join(errors))


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
