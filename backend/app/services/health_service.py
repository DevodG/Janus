from pathlib import Path
from importlib.util import find_spec
from typing import Dict, Any

from app.config import (
    MEMORY_DIR,
    PROMPTS_DIR,
    LLM_PROVIDER,
    DEEPSEEK_API_KEY,
    DEEPSEEK_CHAT_MODEL,
    DEEPSEEK_REASONER_MODEL,
)

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
    prompt_checks = {}
    for prompt in REQUIRED_PROMPTS:
        prompt_checks[prompt] = (Path(PROMPTS_DIR) / prompt).exists()

    all_prompts_present = all(prompt_checks.values())

    checks = {
        "memory_dir_writable": _memory_dir_writable(),
        "prompts_loaded": all_prompts_present,
        "prompt_files": prompt_checks,
        "llm_provider": LLM_PROVIDER,
        "deepseek_key_present": bool(DEEPSEEK_API_KEY),
        "deepseek_chat_model": DEEPSEEK_CHAT_MODEL,
        "deepseek_reasoner_model": DEEPSEEK_REASONER_MODEL,
        "langgraph_available": find_spec("langgraph") is not None,
        "dotenv_available": find_spec("dotenv") is not None,
        "openai_sdk_available": find_spec("openai") is not None,
    }

    overall = "ok" if checks["memory_dir_writable"] and all_prompts_present else "degraded"

    return {
        "status": overall,
        "version": "0.3.0-deepseek",
        "checks": checks,
    }
