from pathlib import Path
from importlib.util import find_spec
from typing import Dict, Any
import logging

from app.config import (
    APP_VERSION,
    MEMORY_DIR,
    PROMPTS_DIR,
    PRIMARY_PROVIDER,
    FALLBACK_PROVIDER,
    OPENROUTER_API_KEY,
    OPENROUTER_BASE_URL,
    OLLAMA_ENABLED,
    OLLAMA_BASE_URL,
    OPENAI_API_KEY,
    OPENAI_BASE_URL,
    TAVILY_API_KEY,
    NEWSAPI_KEY,
    ALPHAVANTAGE_API_KEY,
    MIROFISH_ENABLED,
)
from app.services.mirofish_client import mirofish_health

logger = logging.getLogger(__name__)


REQUIRED_PROMPTS = ["research.txt", "planner.txt", "verifier.txt", "synthesizer.txt"]


def _memory_dir_writable() -> bool:
    try:
        path = Path(MEMORY_DIR)
        path.mkdir(parents=True, exist_ok=True)
        test_file = path / ".healthcheck.tmp"
        test_file.write_text("ok", encoding="utf-8")
        test_file.unlink(missing_ok=True)
        return True
    except Exception:
        return False


def _check_provider_health(provider: str) -> Dict[str, Any]:
    """Check if a provider is configured and reachable."""
    import httpx
    
    provider = provider.lower()
    
    if provider == "openrouter":
        if not OPENROUTER_API_KEY:
            return {"configured": False, "reachable": False, "error": "API key missing"}
        try:
            with httpx.Client(timeout=5) as client:
                response = client.get(f"{OPENROUTER_BASE_URL}/models", headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}"
                })
                return {"configured": True, "reachable": response.status_code < 500, "status_code": response.status_code}
        except Exception as e:
            logger.warning(f"OpenRouter health check failed: {e}")
            return {"configured": True, "reachable": False, "error": str(e)}
    
    elif provider == "ollama":
        if not OLLAMA_ENABLED:
            return {"configured": False, "reachable": False, "error": "Ollama disabled"}
        try:
            with httpx.Client(timeout=5) as client:
                response = client.get(f"{OLLAMA_BASE_URL.replace('/api', '')}/api/tags")
                return {"configured": True, "reachable": response.status_code == 200, "status_code": response.status_code}
        except Exception as e:
            logger.warning(f"Ollama health check failed: {e}")
            return {"configured": True, "reachable": False, "error": str(e)}
    
    elif provider == "openai":
        if not OPENAI_API_KEY:
            return {"configured": False, "reachable": False, "error": "API key missing"}
        try:
            with httpx.Client(timeout=5) as client:
                response = client.get(f"{OPENAI_BASE_URL}/models", headers={
                    "Authorization": f"Bearer {OPENAI_API_KEY}"
                })
                return {"configured": True, "reachable": response.status_code < 500, "status_code": response.status_code}
        except Exception as e:
            logger.warning(f"OpenAI health check failed: {e}")
            return {"configured": True, "reachable": False, "error": str(e)}
    
    return {"configured": False, "reachable": False, "error": "Unknown provider"}


def deep_health() -> Dict[str, Any]:
    prompt_checks = {
        prompt: (Path(PROMPTS_DIR) / prompt).exists()
        for prompt in REQUIRED_PROMPTS
    }

    mirofish = mirofish_health() if MIROFISH_ENABLED else {"reachable": False, "status_code": None, "body": "disabled"}

    # Check provider health
    primary_health = _check_provider_health(PRIMARY_PROVIDER)
    fallback_health = _check_provider_health(FALLBACK_PROVIDER)
    
    logger.info(f"Primary provider {PRIMARY_PROVIDER} health: {primary_health}")
    logger.info(f"Fallback provider {FALLBACK_PROVIDER} health: {fallback_health}")

    checks = {
        "memory_dir_writable": _memory_dir_writable(),
        "prompt_files": prompt_checks,
        "prompts_loaded": all(prompt_checks.values()),
        "primary_provider": PRIMARY_PROVIDER,
        "primary_provider_health": primary_health,
        "fallback_provider": FALLBACK_PROVIDER,
        "fallback_provider_health": fallback_health,
        "openrouter_key_present": bool(OPENROUTER_API_KEY),
        "openai_key_present": bool(OPENAI_API_KEY),
        "ollama_enabled": OLLAMA_ENABLED,
        "tavily_enabled": bool(TAVILY_API_KEY),
        "newsapi_enabled": bool(NEWSAPI_KEY),
        "alphavantage_enabled": bool(ALPHAVANTAGE_API_KEY),
        "mirofish_enabled": MIROFISH_ENABLED,
        "mirofish_health": mirofish,
        "httpx_available": find_spec("httpx") is not None,
        "langgraph_available": find_spec("langgraph") is not None,
        "dotenv_available": find_spec("dotenv") is not None,
    }

    status = "ok" if checks["memory_dir_writable"] and checks["prompts_loaded"] else "degraded"

    return {
        "status": status,
        "version": APP_VERSION,
        "checks": checks,
    }
