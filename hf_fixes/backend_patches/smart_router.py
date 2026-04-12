"""
backend/app/agents/smart_router.py — HF Spaces version

Fixes all LLM provider failures visible in the logs:
  ✗ OpenRouter HTTP 400 — stale model IDs (qwen3.6-plus, nemotron-3-super, etc.)
  ✗ Gemini "string indices must be integers, not 'str'" — wrong response parsing
  ✗ Groq HTTP 400 — stale model ID
  ✗ Ollama "Connection refused" — expected on HF Spaces (no local GPU)

Working provider chain (April 2026):
  1. Groq        — llama-3.3-70b-versatile  (fastest, 30 req/min free)
  2. OpenRouter  — multiple working free models
  3. Gemini      — gemini-1.5-flash (generous free tier)
  4. OpenAI      — gpt-4o-mini (paid fallback)
  # Ollama disabled on HF Spaces
"""
from __future__ import annotations

import json
import logging
import os
import re
import time
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)

# ── Working model lists (verified April 2026) ──────────────────────────────
GROQ_MODELS = [
    "llama-3.3-70b-versatile",
    "llama3-8b-8192",            # smaller fallback
    "mixtral-8x7b-32768",
]

OPENROUTER_MODELS = [
    "meta-llama/llama-3.3-70b-instruct:free",
    "deepseek/deepseek-chat-v3-0324:free",
    "qwen/qwen-2.5-72b-instruct:free",
    "google/gemma-3-27b-it:free",
    "mistralai/mistral-7b-instruct:free",
    "microsoft/phi-4:free",
    "nousresearch/hermes-3-llama-3.1-405b:free",
]

GEMINI_MODELS = [
    "gemini-1.5-flash",
    "gemini-1.5-flash-8b",
    "gemini-1.0-pro",
]

# ── Provider credentials ───────────────────────────────────────────────────
GROQ_API_KEY      = os.getenv("GROQ_API_KEY", "")
OPENROUTER_KEY    = os.getenv("OPENROUTER_API_KEY", "")
GEMINI_API_KEY    = os.getenv("GEMINI_API_KEY", "")
OPENAI_API_KEY    = os.getenv("OPENAI_API_KEY", "")
IS_HF_SPACE       = os.getenv("SPACE_ID", "") != ""


# ── Retry helper ───────────────────────────────────────────────────────────
def _retry(fn, retries: int = 2, base_delay: float = 1.0):
    last: Optional[Exception] = None
    for attempt in range(retries + 1):
        try:
            return fn()
        except Exception as e:
            last = e
            status = getattr(getattr(e, "response", None), "status_code", None)
            if status in (401, 403, 404):
                raise  # don't retry auth/not-found errors
            if attempt < retries:
                time.sleep(base_delay * (2 ** attempt))
    raise last  # type: ignore


# ── Individual providers ───────────────────────────────────────────────────

def _call_groq(messages: list[dict], mode: str = "chat") -> str:
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY not set")

    errors = []
    for model in GROQ_MODELS:
        try:
            payload = {
                "model":       model,
                "messages":    messages,
                "temperature": 0.7 if mode == "chat" else 0.2,
                "max_tokens":  2048,
            }
            def do_call():
                with httpx.Client(timeout=30) as client:
                    r = client.post(
                        "https://api.groq.com/openai/v1/chat/completions",
                        json=payload,
                        headers={
                            "Authorization": f"Bearer {GROQ_API_KEY}",
                            "Content-Type": "application/json",
                        },
                    )
                    r.raise_for_status()
                    return r.json()

            data = _retry(do_call)
            return data["choices"][0]["message"]["content"].strip()
        except Exception as e:
            errors.append(f"groq/{model}: {e}")
            continue

    raise RuntimeError(f"All Groq models failed: {'; '.join(errors)}")


def _call_openrouter(messages: list[dict], mode: str = "chat") -> str:
    if not OPENROUTER_KEY:
        raise ValueError("OPENROUTER_API_KEY not set")

    errors = []
    for model in OPENROUTER_MODELS:
        try:
            payload = {
                "model":       model,
                "messages":    messages,
                "temperature": 0.7 if mode == "chat" else 0.2,
                "max_tokens":  2048,
            }
            def do_call():
                with httpx.Client(timeout=45) as client:
                    r = client.post(
                        "https://openrouter.ai/api/v1/chat/completions",
                        json=payload,
                        headers={
                            "Authorization":  f"Bearer {OPENROUTER_KEY}",
                            "Content-Type":   "application/json",
                            "HTTP-Referer":   "https://huggingface.co/spaces",
                            "X-Title":        "Janus",
                        },
                    )
                    r.raise_for_status()
                    return r.json()

            data = _retry(do_call)
            content = data["choices"][0]["message"]["content"]
            if not content:
                raise ValueError("Empty response from model")
            return content.strip()
        except Exception as e:
            errors.append(f"openrouter/{model}: {e}")
            continue

    raise RuntimeError(f"All OpenRouter models failed: {'; '.join(errors)}")


def _call_gemini(messages: list[dict], mode: str = "chat") -> str:
    """
    Fix: the original code had 'string indices must be integers, not str'
    because it was indexing response.text directly on the GenerateContentResponse
    object instead of using candidates[0].content.parts[0].text
    """
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY not set")

    try:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)

        errors = []
        for model_name in GEMINI_MODELS:
            try:
                model = genai.GenerativeModel(model_name)

                # Convert OpenAI-style messages to Gemini format
                # Gemini uses 'user'/'model' roles, not 'user'/'assistant'
                gemini_history = []
                system_prompt  = None
                for msg in messages:
                    role = msg.get("role", "user")
                    content = msg.get("content", "")
                    if role == "system":
                        system_prompt = content
                        continue
                    gemini_role = "model" if role == "assistant" else "user"
                    gemini_history.append({"role": gemini_role, "parts": [content]})

                # Prepend system prompt to first user message if present
                if system_prompt and gemini_history:
                    first_user = next(
                        (i for i, m in enumerate(gemini_history) if m["role"] == "user"),
                        None
                    )
                    if first_user is not None:
                        gemini_history[first_user]["parts"][0] = (
                            f"{system_prompt}\n\n{gemini_history[first_user]['parts'][0]}"
                        )

                if not gemini_history:
                    raise ValueError("No user messages to send")

                # ── THE FIX: correct response parsing ────────────────────
                response = model.generate_content(
                    gemini_history[-1]["parts"][0]
                    if len(gemini_history) == 1
                    else gemini_history
                )
                # response.text works on GenerateContentResponse IF there's no safety block
                # But response is NOT a dict — don't index it like response["text"]
                # Correct access pattern:
                try:
                    text = response.text  # convenience property, safe if no safety filter
                except (AttributeError, ValueError):
                    # Fall back to manual traversal if .text raises
                    text = response.candidates[0].content.parts[0].text

                if not text:
                    raise ValueError("Empty Gemini response")
                return text.strip()

            except Exception as e:
                errors.append(f"gemini/{model_name}: {e}")
                continue

        raise RuntimeError(f"All Gemini models failed: {'; '.join(errors)}")

    except ImportError:
        raise RuntimeError("google-generativeai not installed")


def _call_openai(messages: list[dict], mode: str = "chat") -> str:
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY not set")
    try:
        import openai
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.7 if mode == "chat" else 0.2,
            max_tokens=2048,
        )
        return resp.choices[0].message.content.strip()
    except ImportError:
        raise RuntimeError("openai package not installed")


# ── Main router ────────────────────────────────────────────────────────────

class SmartRouter:
    """
    Tries providers in priority order.
    Provider priority depends on what keys are set:
      Groq (fast) → OpenRouter (many free models) → Gemini → OpenAI
    Ollama is skipped on HF Spaces.
    """

    def __init__(self):
        self._providers = self._build_provider_list()
        self._failures:  dict[str, int] = {}
        self._last_fail: dict[str, float] = {}
        self._cooldown = 300  # 5 min cooldown after provider fails

    def _build_provider_list(self) -> list[tuple[str, Any]]:
        providers = []
        if GROQ_API_KEY:
            providers.append(("groq", _call_groq))
        if OPENROUTER_KEY:
            providers.append(("openrouter", _call_openrouter))
        if GEMINI_API_KEY:
            providers.append(("gemini", _call_gemini))
        if OPENAI_API_KEY:
            providers.append(("openai", _call_openai))
        # Ollama: only on local, never on HF Space
        if not IS_HF_SPACE and os.getenv("OLLAMA_ENABLED", "false").lower() == "true":
            try:
                from app.agents._model import call_ollama
                providers.append(("ollama", call_ollama))
            except ImportError:
                pass
        return providers

    def call(self, messages: list[dict], mode: str = "chat") -> str:
        if not self._providers:
            raise RuntimeError(
                "No LLM providers configured. "
                "Set at least one of: GROQ_API_KEY, OPENROUTER_API_KEY, GEMINI_API_KEY, OPENAI_API_KEY "
                "in Space Secrets."
            )

        errors = []
        for name, fn in self._providers:
            # Skip recently failed providers
            if self._is_on_cooldown(name):
                continue
            try:
                logger.info("[router] trying %s", name)
                result = fn(messages, mode)
                # Success — reset failure count
                self._failures[name] = 0
                return result
            except Exception as e:
                logger.warning("[router] %s failed: %s", name, e)
                self._failures[name] = self._failures.get(name, 0) + 1
                self._last_fail[name] = time.time()
                errors.append(f"{name}: {e}")

        raise RuntimeError(
            f"All LLM providers exhausted:\n" + "\n".join(errors)
        )

    def _is_on_cooldown(self, name: str) -> bool:
        if self._failures.get(name, 0) < 3:
            return False  # Not failed enough to cooldown
        last = self._last_fail.get(name, 0)
        return (time.time() - last) < self._cooldown


# ── Module-level interface ─────────────────────────────────────────────────
_router = SmartRouter()


def call_model(
    prompt_or_messages,
    mode: str = "chat",
    system: Optional[str] = None,
) -> str:
    """
    Main entrypoint for all LLM calls in Janus.

    Args:
        prompt_or_messages: Either a string prompt or a list of message dicts.
        mode: "chat" (creative) or "json" (precise, low temperature).
        system: Optional system prompt (prepended to messages).
    """
    if isinstance(prompt_or_messages, str):
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt_or_messages})
    else:
        messages = prompt_or_messages
        if system and (not messages or messages[0].get("role") != "system"):
            messages = [{"role": "system", "content": system}] + messages

    return _router.call(messages, mode=mode)
