from pathlib import Path
from typing import Dict, List, Optional

from app.config import PROMPTS_DIR

ALLOWED_PROMPTS = {"research", "planner", "verifier", "synthesizer"}


def _prompt_path(name: str) -> Path:
    safe_name = name.replace(".txt", "").strip()
    if safe_name not in ALLOWED_PROMPTS:
        raise ValueError(f"Unknown prompt: {name}")
    return Path(PROMPTS_DIR) / f"{safe_name}.txt"


def list_prompts() -> List[Dict[str, str]]:
    results = []
    for name in sorted(ALLOWED_PROMPTS):
        path = _prompt_path(name)
        if path.exists():
            results.append(
                {
                    "name": name,
                    "content": path.read_text(encoding="utf-8"),
                }
            )
    return results


def get_prompt(name: str) -> Optional[Dict[str, str]]:
    path = _prompt_path(name)
    if not path.exists():
        return None

    return {
        "name": name.replace(".txt", ""),
        "content": path.read_text(encoding="utf-8"),
    }


def update_prompt(name: str, content: str) -> Dict[str, str]:
    path = _prompt_path(name)
    path.write_text(content, encoding="utf-8")

    return {
        "name": name.replace(".txt", ""),
        "content": content,
    }
