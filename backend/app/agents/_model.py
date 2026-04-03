from typing import Optional, List, Dict, Any
import logging

import httpx

from app.config import (
    PRIMARY_PROVIDER,
    FALLBACK_PROVIDER,
    OPENROUTER_API_KEY,
    OPENROUTER_BASE_URL,
    OPENROUTER_CHAT_MODEL,
    OPENROUTER_REASONER_MODEL,
    OPENROUTER_SITE_URL,
    OPENROUTER_APP_NAME,
    OLLAMA_ENABLED,
    OLLAMA_BASE_URL,
    OLLAMA_CHAT_MODEL,
    OLLAMA_REASONER_MODEL,
    OPENAI_API_KEY,
    OPENAI_BASE_URL,
    OPENAI_CHAT_MODEL,
    OPENAI_REASONER_MODEL,
)

logger = logging.getLogger(__name__)


class LLMProviderError(Exception):
    pass


def _pick_openrouter_model(mode: str) -> str:
    return OPENROUTER_REASONER_MODEL if mode == "reasoner" else OPENROUTER_CHAT_MODEL


def _pick_ollama_model(mode: str) -> str:
    return OLLAMA_REASONER_MODEL if mode == "reasoner" else OLLAMA_CHAT_MODEL


def _pick_openai_model(mode: str) -> str:
    return OPENAI_REASONER_MODEL if mode == "reasoner" else OPENAI_CHAT_MODEL


def _build_messages(prompt: str, system_prompt: Optional[str] = None) -> List[Dict[str, str]]:
    messages: List[Dict[str, str]] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    return messages


def _call_openrouter(prompt: str, mode: str = "chat", system_prompt: Optional[str] = None) -> str:
    if not OPENROUTER_API_KEY:
        raise LLMProviderError("OPENROUTER_API_KEY is missing.")

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }
    if OPENROUTER_SITE_URL:
        headers["HTTP-Referer"] = OPENROUTER_SITE_URL
    if OPENROUTER_APP_NAME:
        headers["X-Title"] = OPENROUTER_APP_NAME

    payload = {
        "model": _pick_openrouter_model(mode),
        "messages": _build_messages(prompt, system_prompt=system_prompt),
    }

    with httpx.Client(timeout=90) as client:
        response = client.post(f"{OPENROUTER_BASE_URL}/chat/completions", headers=headers, json=payload)

    if response.status_code >= 400:
        raise LLMProviderError(f"OpenRouter error {response.status_code}: {response.text}")

    data = response.json()
    return data["choices"][0]["message"]["content"].strip()


def _call_ollama(prompt: str, mode: str = "chat", system_prompt: Optional[str] = None) -> str:
    if not OLLAMA_ENABLED:
        raise LLMProviderError("Ollama fallback is disabled.")

    payload = {
        "model": _pick_ollama_model(mode),
        "messages": _build_messages(prompt, system_prompt=system_prompt),
        "stream": False,
    }

    with httpx.Client(timeout=120) as client:
        response = client.post(f"{OLLAMA_BASE_URL}/chat", json=payload)

    if response.status_code >= 400:
        raise LLMProviderError(f"Ollama error {response.status_code}: {response.text}")

    data = response.json()
    message = data.get("message", {})
    return str(message.get("content", "")).strip()


def _call_openai(prompt: str, mode: str = "chat", system_prompt: Optional[str] = None) -> str:
    if not OPENAI_API_KEY:
        raise LLMProviderError("OPENAI_API_KEY is missing.")

    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": _pick_openai_model(mode),
        "messages": _build_messages(prompt, system_prompt=system_prompt),
    }

    with httpx.Client(timeout=90) as client:
        response = client.post(f"{OPENAI_BASE_URL}/chat/completions", headers=headers, json=payload)

    if response.status_code >= 400:
        raise LLMProviderError(f"OpenAI error {response.status_code}: {response.text}")

    data = response.json()
    return data["choices"][0]["message"]["content"].strip()


def call_model(
    prompt: str,
    mode: str = "chat",
    system_prompt: Optional[str] = None,
    provider_override: Optional[str] = None,
) -> str:
    provider = (provider_override or PRIMARY_PROVIDER).lower()
    logger.info(f"Calling model with provider={provider}, mode={mode}")

    try:
        if provider == "openrouter":
            result = _call_openrouter(prompt, mode=mode, system_prompt=system_prompt)
            logger.info(f"Provider {provider} succeeded")
            return result
        if provider == "ollama":
            result = _call_ollama(prompt, mode=mode, system_prompt=system_prompt)
            logger.info(f"Provider {provider} succeeded")
            return result
        if provider == "openai":
            result = _call_openai(prompt, mode=mode, system_prompt=system_prompt)
            logger.info(f"Provider {provider} succeeded")
            return result
        raise LLMProviderError(f"Unsupported provider: {provider}")
    except Exception as primary_error:
        logger.warning(f"Primary provider {provider} failed: {primary_error}")
        fallback = FALLBACK_PROVIDER.lower()
        if fallback == provider:
            logger.error(f"No fallback available, primary provider {provider} failed")
            raise LLMProviderError(str(primary_error))

        logger.info(f"Attempting fallback to provider={fallback}")
        try:
            if fallback == "ollama":
                result = _call_ollama(prompt, mode=mode, system_prompt=system_prompt)
                logger.info(f"Fallback provider {fallback} succeeded")
                return result
            if fallback == "openrouter":
                result = _call_openrouter(prompt, mode=mode, system_prompt=system_prompt)
                logger.info(f"Fallback provider {fallback} succeeded")
                return result
            if fallback == "openai":
                result = _call_openai(prompt, mode=mode, system_prompt=system_prompt)
                logger.info(f"Fallback provider {fallback} succeeded")
                return result
        except Exception as fallback_error:
            logger.error(f"Fallback provider {fallback} also failed: {fallback_error}")
            raise LLMProviderError(
                f"Primary provider failed: {primary_error} | Fallback failed: {fallback_error}"
            )

        logger.error(f"Primary provider {provider} failed with no valid fallback")
        raise LLMProviderError(str(primary_error))
