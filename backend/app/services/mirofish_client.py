from typing import Any, Dict

import httpx

from app.config import (
    MIROFISH_API_BASE,
    MIROFISH_TIMEOUT_SECONDS,
    MIROFISH_HEALTH_PATH,
    MIROFISH_RUN_PATH,
    MIROFISH_STATUS_PATH,
    MIROFISH_REPORT_PATH,
    MIROFISH_CHAT_PATH,
)


class MiroFishError(Exception):
    pass


def _build_url(path: str, simulation_id: str | None = None) -> str:
    if simulation_id is not None:
        path = path.replace("{id}", simulation_id)
    return f"{MIROFISH_API_BASE.rstrip('/')}{path}"


def mirofish_health() -> Dict[str, Any]:
    try:
        with httpx.Client(timeout=10) as client:
            response = client.get(_build_url(MIROFISH_HEALTH_PATH))
        return {
            "reachable": response.status_code < 500,
            "status_code": response.status_code,
            "body": response.text[:500],
        }
    except Exception as e:
        return {
            "reachable": False,
            "status_code": None,
            "body": str(e),
        }


def run_simulation(payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        with httpx.Client(timeout=MIROFISH_TIMEOUT_SECONDS) as client:
            response = client.post(_build_url(MIROFISH_RUN_PATH), json=payload)
        if response.status_code >= 400:
            raise MiroFishError(f"MiroFish run error {response.status_code}: {response.text}")
        return response.json()
    except Exception as e:
        raise MiroFishError(str(e))


def simulation_status(simulation_id: str) -> Dict[str, Any]:
    try:
        with httpx.Client(timeout=30) as client:
            response = client.get(_build_url(MIROFISH_STATUS_PATH, simulation_id))
        if response.status_code >= 400:
            raise MiroFishError(f"MiroFish status error {response.status_code}: {response.text}")
        return response.json()
    except Exception as e:
        raise MiroFishError(str(e))


def simulation_report(simulation_id: str) -> Dict[str, Any]:
    try:
        with httpx.Client(timeout=30) as client:
            response = client.get(_build_url(MIROFISH_REPORT_PATH, simulation_id))
        if response.status_code >= 400:
            raise MiroFishError(f"MiroFish report error {response.status_code}: {response.text}")
        return response.json()
    except Exception as e:
        raise MiroFishError(str(e))


def simulation_chat(simulation_id: str, message: str) -> Dict[str, Any]:
    try:
        with httpx.Client(timeout=60) as client:
            response = client.post(
                _build_url(MIROFISH_CHAT_PATH, simulation_id),
                json={"message": message},
            )
        if response.status_code >= 400:
            raise MiroFishError(f"MiroFish chat error {response.status_code}: {response.text}")
        return response.json()
    except Exception as e:
        raise MiroFishError(str(e))