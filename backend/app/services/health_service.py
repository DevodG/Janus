from pathlib import Path
from importlib.util import find_spec
from typing import Dict, Any

from app.config import (
    APP_VERSION,
    MEMORY_DIR,
    PROMPTS_DIR,
    PRIMARY_PROVIDER,
    FALLBACK_PROVIDER,
    OPENROUTER_API_KEY,
    OLLAMA_ENABLED,
    TAVILY_API_KEY,
    NEWSAPI_KEY,
    ALPHAVANTAGE_API_KEY,
    MIROFISH_ENABLED,
)
from app.services.mirofish_client import mirofish_health


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


def deep_health() -> Dict[str, Any]:
    prompt_checks = {
        prompt: (Path(PROMPTS_DIR) / prompt).exists()
        for prompt in REQUIRED_PROMPTS
    }

    mirofish = mirofish_health() if MIROFISH_ENABLED else {"reachable": False, "status_code": None, "body": "disabled"}

    checks = {
        "memory_dir_writable": _memory_dir_writable(),
        "prompt_files": prompt_checks,
        "prompts_loaded": all(prompt_checks.values()),
        "primary_provider": PRIMARY_PROVIDER,
        "fallback_provider": FALLBACK_PROVIDER,
        "openrouter_key_present": bool(OPENROUTER_API_KEY),
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
