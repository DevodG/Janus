from __future__ import annotations
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

DATA_PATH = Path("backend/app/data/memory/fallback_events.json")

def _ensure_path():
    if not DATA_PATH.parent.exists():
        os.makedirs(DATA_PATH.parent, exist_ok=True)

def _read() -> List[Dict[str, Any]]:
    if not DATA_PATH.exists():
        return []
    try:
        content = DATA_PATH.read_text(encoding="utf-8")
        if not content:
            return []
        return json.loads(content)
    except Exception:
        return []

def _write(items: List[Dict[str, Any]]) -> None:
    _ensure_path()
    DATA_PATH.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")

def append_event(event: Dict[str, Any]) -> None:
    items = _read()
    # Check if duplicate by ID
    new_id = str(event.get("id"))
    items = [i for i in items if str(i.get("id")) != new_id]
    items.insert(0, event)
    _write(items[:100]) # Keep last 100

def list_events() -> List[Dict[str, Any]]:
    return _read()

def get_event(event_id: str) -> Optional[Dict[str, Any]]:
    for item in _read():
        if str(item.get("id")) == str(event_id):
            return item
    return None
