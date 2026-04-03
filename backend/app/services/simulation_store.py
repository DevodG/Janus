import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, List

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


def list_simulations(limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """List all simulations with optional limit."""
    simulations = []
    for path in Path(SIMULATION_DIR).glob("*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            simulations.append(data)
        except Exception:
            continue
    
    # Sort by saved_at descending (newest first)
    simulations.sort(key=lambda x: x.get("saved_at", ""), reverse=True)
    
    if limit:
        return simulations[:limit]
    return simulations


def search_simulations(query: str, status: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Search simulations by title or prediction_goal.
    Optionally filter by status.
    """
    all_sims = list_simulations()
    results = []
    
    query_lower = query.lower()
    
    for sim in all_sims:
        # Filter by status if provided
        if status and sim.get("status") != status:
            continue
        
        # Search in title and prediction_goal
        title = sim.get("title", "").lower()
        goal = sim.get("prediction_goal", "").lower()
        
        if query_lower in title or query_lower in goal:
            results.append(sim)
    
    return results


def filter_simulations_by_status(status: str) -> List[Dict[str, Any]]:
    """Filter simulations by status."""
    all_sims = list_simulations()
    return [sim for sim in all_sims if sim.get("status") == status]