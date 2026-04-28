"""
Smart LLM Router for Janus.

Unified router across multiple free providers with rate limit tracking,
automatic failover, and daily quota management.

Provider priority:
1. Hugging Face Router (when configured)
2. Google Gemini (best free quality, 1500 req/day)
3. Groq (fastest, Llama 3.3 70B, 14400 req/day)
4. OpenRouter (free models — fixed model list)
5. Cloudflare Workers AI (10k req/day)
6. Ollama (local, unlimited)
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
    tomorrow = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(
        days=1
    )
    return int(tomorrow.timestamp())


def _is_available(provider: str, daily_limit: int, rpm_limit: int) -> bool:
    now = time.time()
    p = _RATE_STATE.get(
        provider, {
            "daily_count": 0, 
            "rpm_timestamps": [], 
            "reset_at": _midnight_ts(),
            "consecutive_failures": 0,
            "cooldown_until": 0
        }
    )
    
    # 1. Reset check
    if now > p.get("reset_at", 0):
        p["daily_count"] = 0
        p["rpm_timestamps"] = []
        p["reset_at"] = _midnight_ts()
        p["consecutive_failures"] = 0
        p["cooldown_until"] = 0

    # 2. Cooldown check
    if now < p.get("cooldown_until", 0):
        return False

    # 3. Quota check
    if p["daily_count"] >= daily_limit:
        return False
    
    # 4. RPM check
    p["rpm_timestamps"] = [t for t in p["rpm_timestamps"] if now - t < 60]
    if len(p["rpm_timestamps"]) >= rpm_limit:
        return False
    
    _RATE_STATE[provider] = p
    return True


def _record_usage(provider: str, success: bool = True):
    now = time.time()
    p = _RATE_STATE.get(
        provider, {
            "daily_count": 0, 
            "rpm_timestamps": [], 
            "reset_at": _midnight_ts(),
            "consecutive_failures": 0,
            "cooldown_until": 0
        }
    )
    
    if success:
        p["daily_count"] = p.get("daily_count", 0) + 1
        p["rpm_timestamps"] = p.get("rpm_timestamps", []) + [now]
        p["consecutive_failures"] = 0
    else:
        p["consecutive_failures"] = p.get("consecutive_failures", 0) + 1
        # Circuit Breaker: 3 strikes = 15 minute cooldown
        if p["consecutive_failures"] >= 3:
            p["cooldown_until"] = now + 900 
            logger.warning(f"[ROUTER] Provider {provider} entered cooldown until {p['cooldown_until']}")

    _RATE_STATE[provider] = p


# ── Provider credentials ────────────────────────────────────────────────────
GEMINI_KEY = os.getenv("GEMINI_API_KEY", "")
GROQ_KEY = os.getenv("GROQ_API_KEY", "")
OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY", "")
HUGGINGFACE_KEY = os.getenv("HUGGINGFACE_API_KEY", os.getenv("HF_TOKEN", ""))
CF_ACCOUNT_ID = os.getenv("CLOUDFLARE_ACCOUNT_ID", "")
CF_TOKEN = os.getenv("CLOUDFLARE_API_TOKEN", "")
TIMEOUT = 120
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


def _call_huggingface(messages: List[Dict[str, str]], **kwargs) -> str:
    """Hugging Face Router via the dedicated client."""
    if not HUGGINGFACE_KEY:
        raise ValueError("HUGGINGFACE_API_KEY not set")

    from app.agents.huggingface import hf_agent
    return hf_agent.call(messages, **kwargs)


def _call_gemini(messages: List[Dict[str, str]], **kwargs) -> str:
    """Google Gemini — best free quality."""
    if not GEMINI_KEY:
        raise ValueError("GEMINI_API_KEY not set")

    # Combine messages into a simple string for Gemini 1.5/2.0 API simplicity
    prompt = "\n".join([f"{m['role']}: {m['content']}" for m in messages])
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": kwargs.get("temperature", 0.7),
            "maxOutputTokens": kwargs.get("max_tokens", 4096),
        },
    }

    # Gemini supports multiple models; try 2.0-flash then 1.5-flash
    models = ["gemini-2.0-flash", "gemini-1.5-flash"]
    for model in models:
        try:
            with httpx.Client(timeout=TIMEOUT) as client:
                r = client.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_KEY}",
                    json=body,
                )
                r.raise_for_status()
                data = r.json()

            cands = data.get("candidates", [])
            if not cands:
                raise ValueError(f"No candidates in Gemini response from {model}")
            parts = cands[0].get("content", {}).get("parts", [])
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
            headers={
                "Authorization": f"Bearer {GROQ_KEY}",
                "Content-Type": "application/json",
            },
            json=body,
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]


def _call_openrouter(messages: List[Dict[str, str]], **kwargs) -> str:
    """OpenRouter — Robust free model list."""
    if not OPENROUTER_KEY:
        raise ValueError("OPENROUTER_API_KEY not set")

    # Priority models (Exp/Flash/Large-instruct)
    free_models = [
        "google/gemini-2.0-flash-exp:free",
        "google/gemma-3-27b-it:free",
        "meta-llama/llama-3.3-70b-instruct:free",
        "qwen/qwen-2.5-72b-instruct:free",
        "microsoft/phi-4:free",
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
                response_json = r.json()
                
                if "choices" not in response_json or not response_json["choices"]:
                     raise ValueError(f"OpenRouter {model} returned no choices: {response_json}")
                     
                msg_data = response_json["choices"][0]["message"]
                content = msg_data.get("content") or ""
                reasoning = msg_data.get("reasoning")
                if reasoning:
                    content = f"<think>\n{reasoning}\n</think>\n\n{content}"
                if not content:
                    raise ValueError("Empty response")
                return content
        except Exception as e:
            errors.append(f"{model}: {str(e)}")
            logger.warning(f"OpenRouter {model} failed: {e}")
            continue

    raise RuntimeError(f"All OpenRouter models failed: {'; '.join(errors)}")


def _call_cloudflare(messages: List[Dict[str, str]], **kwargs) -> str:
    """Cloudflare Workers AI."""
    if not CF_ACCOUNT_ID or not CF_TOKEN:
        raise ValueError("Cloudflare credentials not set")

    model = "@cf/meta/llama-3.1-70b-instruct"
    body = {"messages": messages}
    with httpx.Client(timeout=TIMEOUT) as client:
        r = client.post(
            f"https://api.cloudflare.com/client/v4/accounts/{CF_ACCOUNT_ID}/ai/run/{model}",
            headers={"Authorization": f"Bearer {CF_TOKEN}"},
            json=body,
        )
        r.raise_for_status()
        return r.json()["result"]["response"]


def _call_ollama(messages: List[Dict[str, str]], **kwargs) -> str:
    """Ollama — local fallback."""
    base = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    model = os.getenv("OLLAMA_MODEL", "llama3")

    body = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {"temperature": kwargs.get("temperature", 0.7)},
    }
    with httpx.Client(timeout=TIMEOUT) as client:
        r = client.post(f"{base}/api/chat", json=body)
        r.raise_for_status()
        return r.json()["message"]["content"]


# ── Provider registry ───────────────────────────────────────────────────────
PROVIDERS = [
    {
        "name": "gemini",
        "daily_limit": 1500,
        "rpm_limit": 15,
        "call": _call_gemini,
        "enabled": bool(GEMINI_KEY),
    },
    {
        "name": "groq",
        "daily_limit": 14400,
        "rpm_limit": 1000,
        "call": _call_groq,
        "enabled": bool(GROQ_KEY),
    },
    {
        "name": "huggingface",
        "daily_limit": 999999,
        "rpm_limit": 60,
        "call": _call_huggingface,
        "enabled": bool(HUGGINGFACE_KEY),
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
        "rpm_limit": 999,
        "call": _call_ollama,
        "enabled": os.getenv("OLLAMA_ENABLED", "true").lower() == "true",
    },
]


def call_model(messages: List[Dict[str, str]], **kwargs) -> str:
    """Highly robust unified entry point with multi-tier failover."""
    errors = []

    for p in PROVIDERS:
        if not p["enabled"]:
            continue

        if not _is_available(p["name"], p["daily_limit"], p["rpm_limit"]):
            continue

        try:
            result = p["call"](messages, **kwargs)
            _record_usage(p["name"], success=True)
            return result
        except Exception as e:
            _record_usage(p["name"], success=False)
            error_msg = f"{p['name']} error: {str(e)}"
            errors.append(error_msg)
            logger.warning(error_msg)
            continue

    raise RuntimeError(f"All model tiers failed:\n" + "\n".join(errors))


def get_router_status() -> dict:
    """Return status of all providers including cooldowns."""
    status = {}
    for p in PROVIDERS:
        now = time.time()
        record = _RATE_STATE.get(p["name"], {})
        status[p["name"]] = {
            "enabled": p["enabled"],
            "daily_count": record.get("daily_count", 0),
            "daily_limit": p["daily_limit"],
            "on_cooldown": now < record.get("cooldown_until", 0),
            "cooldown_remaining": max(0, int(record.get("cooldown_until", 0) - now)),
            "consecutive_failures": record.get("consecutive_failures", 0)
        }
    return status
