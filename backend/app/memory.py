import json
from datetime import datetime
from pathlib import Path
from app.config import MEMORY_DIR

Path(MEMORY_DIR).mkdir(parents=True, exist_ok=True)


def save_case(case_id: str, payload: dict) -> str:
    path = Path(MEMORY_DIR) / f"{case_id}.json"
    payload["saved_at"] = datetime.utcnow().isoformat()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    return str(path)
