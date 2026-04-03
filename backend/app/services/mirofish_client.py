"""
MiroFish client adapter.

MiroFish actual API (all under /api/):
  Graph/Project:
    POST /api/graph/ontology/generate  - upload seed file + requirement → project_id
    POST /api/graph/build              - build graph → task_id
    GET  /api/graph/task/<task_id>     - poll build status → graph_id when done

  Simulation:
    POST /api/simulation/create        - create simulation → simulation_id
    POST /api/simulation/prepare       - prepare agents
    POST /api/simulation/prepare/status - poll prepare status
    POST /api/simulation/start         - run simulation
    GET  /api/simulation/<sim_id>      - get simulation status
    GET  /api/simulation/list          - list simulations

  Report:
    POST /api/report/generate          - generate report → report_id
    POST /api/report/generate/status   - poll report status
    GET  /api/report/<report_id>       - get report
    GET  /api/report/by-simulation/<sim_id> - get report by simulation
    POST /api/report/chat              - chat with report agent
"""

import io
import time
import logging
from typing import Any, Dict, Optional

import httpx

from app.config import MIROFISH_API_BASE, MIROFISH_TIMEOUT_SECONDS

logger = logging.getLogger(__name__)

BASE = MIROFISH_API_BASE.rstrip("/")

# Module-level connection pool — reused across all requests
_http_pool = httpx.Client(
    timeout=MIROFISH_TIMEOUT_SECONDS,
    limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
)


class MiroFishError(Exception):
    pass


def _url(path: str) -> str:
    return f"{BASE}{path}"


def _post(path: str, json: Dict = None, data: Dict = None, files=None, timeout: int = 30) -> Dict:
    try:
        if files:
            # Use a one-off client for multipart uploads (connection pool can't reuse these)
            with httpx.Client(timeout=timeout) as client:
                response = client.post(_url(path), data=data or {}, files=files)
        else:
            response = _http_pool.post(_url(path), json=json or {}, timeout=timeout)
        if response.status_code >= 400:
            raise MiroFishError(f"MiroFish {path} error {response.status_code}: {response.text[:300]}")
        return response.json()
    except MiroFishError:
        raise
    except Exception as e:
        raise MiroFishError(str(e))


def _get(path: str, timeout: int = 30) -> Dict:
    try:
        response = _http_pool.get(_url(path), timeout=timeout)
        if response.status_code >= 400:
            raise MiroFishError(f"MiroFish {path} error {response.status_code}: {response.text[:300]}")
        return response.json()
    except MiroFishError:
        raise
    except Exception as e:
        raise MiroFishError(str(e))


# ── Health ────────────────────────────────────────────────────────────────────

def mirofish_health() -> Dict[str, Any]:
    try:
        with httpx.Client(timeout=10) as client:
            response = client.get(_url("/health"))
        return {
            "reachable": response.status_code < 500,
            "status_code": response.status_code,
            "body": response.text[:200],
        }
    except Exception as e:
        return {"reachable": False, "status_code": None, "body": str(e)}


# ── Full simulation workflow ──────────────────────────────────────────────────

def run_simulation(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Orchestrate the full MiroFish workflow:
      1. Generate ontology (upload seed text as a .txt file)
      2. Build graph (poll until done)
      3. Create simulation
      4. Prepare simulation (poll until done)
      5. Start simulation
    Returns a dict with simulation_id and status.
    """
    title = payload.get("title", "Simulation")
    seed_text = payload.get("seed_text", payload.get("prediction_goal", ""))
    requirement = payload.get("prediction_goal", title)

    logger.info(f"MiroFish: starting full workflow for '{title}'")

    # Step 1 – generate ontology by uploading seed text as a file
    seed_bytes = seed_text.encode("utf-8")
    files = [("files", ("seed.txt", io.BytesIO(seed_bytes), "text/plain"))]
    form_data = {
        "simulation_requirement": requirement,
        "project_name": title,
    }
    ontology_resp = _post("/api/graph/ontology/generate", data=form_data, files=files, timeout=120)
    if not ontology_resp.get("success"):
        raise MiroFishError(f"Ontology generation failed: {ontology_resp.get('error')}")
    project_id = ontology_resp["data"]["project_id"]
    logger.info(f"MiroFish: project created {project_id}")

    # Step 2 – build graph
    build_resp = _post("/api/graph/build", json={"project_id": project_id}, timeout=120)
    if not build_resp.get("success"):
        raise MiroFishError(f"Graph build failed: {build_resp.get('error')}")
    task_id = build_resp["data"]["task_id"]
    logger.info(f"MiroFish: graph build task {task_id}")

    # Poll graph build (max 5 min)
    graph_id = _poll_graph_build(task_id, max_wait=300)
    logger.info(f"MiroFish: graph ready {graph_id}")

    # Step 3 – create simulation
    create_resp = _post("/api/simulation/create", json={"project_id": project_id, "graph_id": graph_id})
    if not create_resp.get("success"):
        raise MiroFishError(f"Simulation create failed: {create_resp.get('error')}")
    simulation_id = create_resp["data"]["simulation_id"]
    logger.info(f"MiroFish: simulation created {simulation_id}")

    # Step 4 – prepare simulation (async, poll)
    prepare_resp = _post("/api/simulation/prepare", json={"simulation_id": simulation_id}, timeout=120)
    if not prepare_resp.get("success"):
        raise MiroFishError(f"Simulation prepare failed: {prepare_resp.get('error')}")
    prepare_task_id = prepare_resp["data"].get("task_id")
    if prepare_task_id:
        _poll_prepare(simulation_id, prepare_task_id, max_wait=300)
    logger.info(f"MiroFish: simulation prepared")

    # Step 5 – start simulation
    start_resp = _post("/api/simulation/start", json={"simulation_id": simulation_id}, timeout=60)
    if not start_resp.get("success"):
        raise MiroFishError(f"Simulation start failed: {start_resp.get('error')}")
    logger.info(f"MiroFish: simulation started {simulation_id}")

    return {
        "simulation_id": simulation_id,
        "project_id": project_id,
        "graph_id": graph_id,
        "status": "running",
    }


def _poll_graph_build(task_id: str, max_wait: int = 300) -> str:
    """Poll graph build task until done, return graph_id. Uses exponential backoff."""
    deadline = time.time() + max_wait
    interval = 2.0  # Start at 2s, double each time, cap at 15s
    while time.time() < deadline:
        resp = _get(f"/api/graph/task/{task_id}")
        data = resp.get("data", {})
        status = data.get("status", "")
        if status == "completed":
            # graph_id may be at top level or nested under "result"
            graph_id = data.get("graph_id") or data.get("result", {}).get("graph_id")
            if not graph_id:
                raise MiroFishError("Graph build completed but no graph_id returned")
            return graph_id
        if status in ("failed", "error"):
            raise MiroFishError(f"Graph build failed: {data.get('error', 'unknown')}")
        logger.debug(f"Graph build polling: status={status}, next check in {interval:.0f}s")
        time.sleep(interval)
        interval = min(interval * 2, 15.0)
    raise MiroFishError("Graph build timed out")


def _poll_prepare(simulation_id: str, task_id: str, max_wait: int = 300):
    """Poll simulation prepare until done. Uses exponential backoff."""
    deadline = time.time() + max_wait
    interval = 2.0
    while time.time() < deadline:
        resp = _post("/api/simulation/prepare/status", json={"task_id": task_id})
        data = resp.get("data", {})
        status = data.get("status", "")
        if status == "completed":
            return
        if status in ("failed", "error"):
            raise MiroFishError(f"Simulation prepare failed: {data.get('error', 'unknown')}")
        logger.debug(f"Prepare polling: status={status}, next check in {interval:.0f}s")
        time.sleep(interval)
        interval = min(interval * 2, 15.0)
    raise MiroFishError("Simulation prepare timed out")


# ── Status / Report / Chat ────────────────────────────────────────────────────

def simulation_status(simulation_id: str) -> Dict[str, Any]:
    resp = _get(f"/api/simulation/{simulation_id}")
    return resp.get("data", resp)


def simulation_report(simulation_id: str) -> Dict[str, Any]:
    """Get or generate report for a simulation."""
    # Try to get existing report first
    try:
        resp = _get(f"/api/report/by-simulation/{simulation_id}")
        if resp.get("success") and resp.get("data"):
            return resp["data"]
    except MiroFishError:
        pass

    # Generate report
    gen_resp = _post("/api/report/generate", json={"simulation_id": simulation_id}, timeout=120)
    if not gen_resp.get("success"):
        raise MiroFishError(f"Report generation failed: {gen_resp.get('error')}")

    report_id = gen_resp["data"].get("report_id")
    task_id = gen_resp["data"].get("task_id")

    # Poll if async
    if task_id:
        deadline = time.time() + 300
        while time.time() < deadline:
            status_resp = _post("/api/report/generate/status", json={"task_id": task_id})
            data = status_resp.get("data", {})
            if data.get("status") == "completed":
                report_id = data.get("report_id", report_id)
                break
            if data.get("status") in ("failed", "error"):
                raise MiroFishError(f"Report generation failed: {data.get('error')}")
            time.sleep(5)

    if report_id:
        report_resp = _get(f"/api/report/{report_id}")
        return report_resp.get("data", report_resp)

    return gen_resp.get("data", {})


def simulation_chat(simulation_id: str, message: str) -> Dict[str, Any]:
    """Chat with the report agent for a simulation."""
    # Get report_id for this simulation
    try:
        resp = _get(f"/api/report/by-simulation/{simulation_id}")
        report_id = resp.get("data", {}).get("report_id") if resp.get("success") else None
    except MiroFishError:
        report_id = None

    chat_payload = {"message": message}
    if report_id:
        chat_payload["report_id"] = report_id

    resp = _post("/api/report/chat", json=chat_payload, timeout=60)
    if not resp.get("success"):
        raise MiroFishError(f"Chat failed: {resp.get('error')}")
    return resp.get("data", resp)
