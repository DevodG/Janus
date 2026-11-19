"""goals.py — goal stack + intrinsic motivation.

Goals are explicit, inspectable, and revisable. Intrinsic motivation is
bounded: measured gaps (curriculum/eval failures) automatically propose goals;
nothing else invents objectives, and goals never bypass the eval gate.
"""
from __future__ import annotations

import json
import time
import uuid
from pathlib import Path

_PATH = Path(__file__).parent / "data" / "goals.jsonl"


def _read() -> list[dict]:
    if not _PATH.exists():
        return []
    return [json.loads(l) for l in _PATH.read_text().splitlines() if l.strip()]


def _write(rows: list[dict]) -> None:
    _PATH.parent.mkdir(parents=True, exist_ok=True)
    _PATH.write_text("\n".join(json.dumps(r) for r in rows) + ("\n" if rows else ""))


def add_goal(text: str, source: str = "user") -> dict:
    rows = _read()
    goal = {"id": uuid.uuid4().hex[:8], "text": text, "source": source,
            "status": "active", "ts": time.time(), "progress": 0.0}
    rows.append(goal)
    _write(rows)
    return goal


def goals(status: str = "active") -> list[dict]:
    return [g for g in _read() if g["status"] == status]


def set_progress(goal_id: str, progress: float) -> bool:
    rows = _read()
    for g in rows:
        if g["id"] == goal_id:
            g["progress"] = max(0.0, min(1.0, progress))
            g["status"] = "done" if g["progress"] >= 1.0 else "active"
            _write(rows)
            return True
    return False


def motivate_from_gaps(gaps: dict) -> list[dict]:
    """Intrinsic motivation: each measured gap proposes exactly one goal."""
    existing = {g["text"] for g in goals()}
    created = []
    for fam, cnt in gaps.items():
        text = f"Master self-curriculum family '{fam}' (failed {cnt}x)"
        if text not in existing:
            created.append(add_goal(text, source="gap-driven"))
    return created
