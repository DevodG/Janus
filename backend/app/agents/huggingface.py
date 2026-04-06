"""
HuggingFace Inference API Client for Janus.

NOTE: HF deprecated api-inference.huggingface.co in favor of router.huggingface.co.
The new router requires provider-specific endpoints. This client tries multiple providers.
Fallback to OpenRouter is recommended for reliability.
"""

import json
import time
import logging
from typing import Dict, List, Any, Optional

import httpx

from app.config import HUGGINGFACE_API_KEY, HUGGINGFACE_MODEL

logger = logging.getLogger(__name__)

MAX_RETRIES = 2
BACKOFF_BASE = 1
PROVIDER_TIMEOUT = 15

PROVIDER_ROUTES = [
    f"https://router.huggingface.co/nebius/v1/chat/completions",
    f"https://router.huggingface.co/together/v1/chat/completions",
    f"https://router.huggingface.co/sambanova/v1/chat/completions",
]


class HuggingFaceInferenceClient:
    """HuggingFace Inference API client — tries multiple providers."""

    def __init__(self, model: str = HUGGINGFACE_MODEL):
        self.model = model
        self.headers = {
            "Authorization": f"Bearer {HUGGINGFACE_API_KEY}",
            "Content-Type": "application/json",
        }

    def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.7),
            "max_tokens": kwargs.get("max_tokens", 4096),
        }

        for route in PROVIDER_ROUTES:
            try:
                with httpx.Client(timeout=PROVIDER_TIMEOUT) as client:
                    response = client.post(
                        route,
                        headers=self.headers,
                        json=payload,
                    )

                    if response.status_code == 200:
                        data = response.json()
                        choices = data.get("choices", [])
                        if choices:
                            return choices[0].get("message", {}).get("content", "")
                        return data.get("generated_text", "")

                    elif response.status_code == 429:
                        time.sleep(BACKOFF_BASE)
                        continue

                    elif response.status_code in (400, 403, 404):
                        logger.debug(
                            f"[HF] Provider {route.split('/')[3]} unavailable ({response.status_code})"
                        )
                        break

                    else:
                        logger.warning(f"[HF] Error {response.status_code} on {route}")
                        break

            except httpx.TimeoutException:
                logger.debug(f"[HF] Timeout on {route}")
                continue
            except Exception as e:
                logger.debug(f"[HF] Error on {route}: {e}")
                break

        raise RuntimeError("All HF providers exhausted")

    def reason(self, messages: List[Dict[str, str]], **kwargs) -> str:
        return self.chat(
            messages,
            temperature=kwargs.get("temperature", 0.9),
            max_tokens=kwargs.get("max_tokens", 8192),
        )

    def is_available(self) -> bool:
        try:
            with httpx.Client(timeout=10) as client:
                r = client.get(
                    "https://router.huggingface.co/hf-inference/v1/models",
                    headers=self.headers,
                )
                return r.status_code < 500
        except Exception:
            return False


hf_client = HuggingFaceInferenceClient()
