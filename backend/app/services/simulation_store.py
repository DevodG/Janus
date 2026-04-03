import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from app.config import SIMULATION_DIR

Path(SIMULATION_DIR).mkdir(parents=True, exist_ok=True)


def _path(simulation_id: str) -> Path:
    return Path(SIMULATION_DIR) / f"{simulation_id}.json"


def save_simulation(simulation_id: str, payload: Dict[str, Any]) -> str:
    data = dict(payload)
    data["saved_at"] = datetime.utcnow().isoformat()
    path = _path(simulation_id)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return str(path)


def get_simulation(simulation_id: str) -> Optional[Dict[str, Any]]:
    path = _path(simulation_id)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))