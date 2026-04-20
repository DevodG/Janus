import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.config import MEMORY_DIR


def _memory_dir() -> Path:
    path = Path(MEMORY_DIR)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _case_path(case_id: str) -> Path:
    return _memory_dir() / f"{case_id}.json"


def list_cases(limit: Optional[int] = None, full: bool = False) -> List[Dict[str, Any]]:
    files = sorted(
        _memory_dir().glob("*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    results: List[Dict[str, Any]] = []
    for path in files:
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            if full:
                results.append(data)
            else:
                preview = data.get("final_answer") or data.get("final", {}).get(
                    "response", ""
                )
                results.append(
                    {
                        "case_id": data.get("case_id", path.stem),
                        "user_input": data.get("user_input", ""),
                        "saved_at": data.get("saved_at"),
                        "final_answer_preview": str(preview)[:200],
                        "simulation_id": data.get("simulation_id"),
                        "route": data.get("route"),
                    }
                )
        except Exception:
            continue

    return results[:limit] if limit else results


def get_case(case_id: str) -> Optional[Dict[str, Any]]:
    path = _case_path(case_id)
    if not path.exists():
        return None

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def delete_case(case_id: str) -> bool:
    path = _case_path(case_id)
    if not path.exists():
        return False

    path.unlink()
    return True


def get_cases_by_simulation(simulation_id: str) -> List[Dict[str, Any]]:
    """Get all cases linked to a specific simulation."""
    all_cases = []
    for path in _memory_dir().glob("*.json"):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if data.get("simulation_id") == simulation_id:
                all_cases.append(data)
        except Exception:
            continue
    return all_cases


def memory_stats() -> Dict[str, Any]:
    files = list(_memory_dir().glob("*.json"))
    files_sorted = sorted(files, key=lambda p: p.stat().st_mtime, reverse=True)

    disk_bytes = sum(p.stat().st_size for p in files)
    latest_case_id = files_sorted[0].stem if files_sorted else None

    return {
        "total_cases": len(files),
        "latest_case_id": latest_case_id,
        "memory_dir": str(_memory_dir()),
        "disk_bytes": disk_bytes,
    }
