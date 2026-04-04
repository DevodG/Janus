import time
import logging
import os
import json

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.schemas import UserTask, AgentRunRequest, PromptUpdateRequest
from app.graph import run_case
from app.memory import save_case
from app.config import (
    APP_VERSION,
    MEMORY_DIR,
    PROMPTS_DIR,
    load_prompt,
)
from app.services.case_store import list_cases, get_case, delete_case, memory_stats
from app.services.prompt_store import list_prompts, get_prompt, update_prompt
from app.services.health_service import deep_health
from app.services.agent_registry import list_agents, get_agent, run_single_agent
from app.routers.simulation import router as simulation_router
from app.routers.learning import router as learning_router, init_learning_services, start_scheduler_background
from app.routers.sentinel import router as sentinel_router
from app.routers.finance import router as finance_router
from app.config import get_config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="MiroOrg v2", version=APP_VERSION)

# Initialize domain packs
from app.domain_packs.init_packs import init_domain_packs
init_domain_packs()

# Initialize learning layer
config = get_config()
if config.learning_enabled:
    try:
        init_learning_services(config)
        logger.info("Learning layer initialized")
    except Exception as e:
        logger.error(f"Failed to initialize learning layer: {e}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(simulation_router)
app.include_router(learning_router)
app.include_router(sentinel_router)
app.include_router(finance_router)


# ── Request Timing Middleware ─────────────────────────────────────────────────

@app.middleware("http")
async def timing_middleware(request: Request, call_next):
    """Add X-Process-Time header and log slow requests."""
    start = time.perf_counter()
    response = await call_next(request)
    elapsed = time.perf_counter() - start
    response.headers["X-Process-Time"] = f"{elapsed:.3f}"

    if elapsed > 10.0:
        logger.warning(f"Slow request: {request.method} {request.url.path} took {elapsed:.1f}s")

    return response


# ── Error Handler ─────────────────────────────────────────────────────────────

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Sanitize error responses — don't leak internal stack traces."""
    logger.exception(f"Unhandled error on {request.method} {request.url.path}")
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal error occurred. Please try again."},
    )


# ── Startup Event ─────────────────────────────────────────────────────────────

@app.on_event("startup")
async def on_startup():
    """Start background tasks on app startup."""
    if config.learning_enabled:
        try:
            start_scheduler_background()
            logger.info("Background learning scheduler started")
        except Exception as e:
            logger.error(f"Failed to start learning scheduler: {e}")

    # Start sentinel scheduler
    sentinel_enabled = os.getenv("SENTINEL_ENABLED", "true").lower() == "true"
    if sentinel_enabled:
        try:
            from app.services.sentinel.scheduler import start_sentinel_scheduler
            start_sentinel_scheduler()
            logger.info("Sentinel scheduler started")
        except Exception as e:
            logger.error(f"Failed to start sentinel scheduler: {e}")


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "version": APP_VERSION}


@app.get("/health/deep")
def health_deep():
    return deep_health()


@app.get("/config/status")
def config_status():
    return {
        "app_version": APP_VERSION,
        "openrouter_key_present": bool(os.getenv("OPENROUTER_API_KEY")),
        "ollama_base_url": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        "ollama_model": os.getenv("OLLAMA_MODEL", "llama3.2"),
        "tavily_enabled": bool(os.getenv("TAVILY_API_KEY")),
        "newsapi_enabled": bool(os.getenv("NEWS_API_KEY", os.getenv("NEWSAPI_KEY"))),
        "alphavantage_enabled": bool(os.getenv("ALPHA_VANTAGE_API_KEY", os.getenv("ALPHAVANTAGE_API_KEY"))),
        "mirofish_base_url": os.getenv("MIROFISH_BASE_URL", "http://localhost:8001"),
        "api_discovery_endpoint": os.getenv("API_DISCOVERY_ENDPOINT", "http://localhost:8002"),
        "memory_dir": str(MEMORY_DIR),
        "prompts_dir": str(PROMPTS_DIR),
    }


# ── Agents ────────────────────────────────────────────────────────────────────

@app.get("/agents")
def agents():
    return list_agents()


@app.get("/agents/{agent_name}")
def agent_detail(agent_name: str):
    agent = get_agent(agent_name)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


# ── Case Execution ────────────────────────────────────────────────────────────

def _log_agent_errors(result: dict):
    """Log any agent errors from the pipeline result."""
    for agent_key in ["route", "research", "planner", "verifier", "simulation", "finance", "final"]:
        agent_output = result.get(agent_key, {})
        if isinstance(agent_output, dict):
            if agent_output.get("status") == "error":
                logger.warning(f"[AGENT ERROR] {agent_key}: {agent_output.get('reason', 'unknown')}")
            elif agent_output.get("error"):
                logger.warning(f"[AGENT ERROR] {agent_key}: {agent_output.get('error')}")


def _fire_and_forget_learning(payload: dict):
    """Fire-and-forget learning from a completed case."""
    from app.routers.learning import learning_engine as _le
    if _le:
        try:
            _le.learn_from_case(payload)
        except Exception as e:
            logger.error(f"Learning from case failed (non-blocking): {e}")


@app.post("/run")
def run_org(task: UserTask):
    try:
        logger.info("Processing /run: %s", task.user_input[:100])
        result = run_case(task.user_input)

        # Log any agent errors
        _log_agent_errors(result)

        # Build response payload
        final = result.get("final", {})
        payload = {
            "case_id": result.get("case_id", ""),
            "user_input": result.get("user_input", ""),
            "route": result.get("route", {}),
            "research": result.get("research", {}),
            "planner": result.get("planner", {}),
            "verifier": result.get("verifier", {}),
            "simulation": result.get("simulation"),
            "finance": result.get("finance"),
            "final": final,
            "final_answer": final.get("response", final.get("summary", "")),
            "outputs": [
                result.get("research", {}),
                result.get("planner", {}),
                result.get("verifier", {}),
                final,
            ],
        }
        save_case(result.get("case_id", ""), payload)

        # Fire-and-forget: learn from this case
        _fire_and_forget_learning(payload)

        return payload
    except Exception as e:
        logger.exception("Error in /run")
        raise HTTPException(status_code=500, detail="Failed to process request. Please try again.")


@app.post("/run/debug")
def run_org_debug(task: UserTask):
    try:
        result = run_case(task.user_input)
        _log_agent_errors(result)
        save_case(result.get("case_id", ""), result)
        _fire_and_forget_learning(result)
        return result
    except Exception as e:
        logger.exception("Error in /run/debug")
        raise HTTPException(status_code=500, detail="Failed to process request. Please try again.")


@app.post("/run/agent")
def run_one_agent(request: AgentRunRequest):
    try:
        return run_single_agent(
            agent=request.agent,
            user_input=request.user_input,
            research_output=request.research_output,
            planner_output=request.planner_output,
            verifier_output=request.verifier_output,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Error in /run/agent")
        raise HTTPException(status_code=500, detail="Failed to run agent. Please try again.")


# ── Debug State Endpoint ──────────────────────────────────────────────────────

@app.get("/debug/state/{case_id}")
def debug_state(case_id: str):
    """Return the full saved state for a case — useful for debugging."""
    case_path = MEMORY_DIR / f"{case_id}.json"
    if not case_path.exists():
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found")
    try:
        with open(case_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read case: {e}")


# ── Cases ─────────────────────────────────────────────────────────────────────

@app.get("/cases")
def cases(limit: int | None = Query(default=None, ge=1, le=200)):
    return list_cases(limit=limit)


@app.get("/cases/{case_id}")
def case_detail(case_id: str):
    case = get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return case


@app.get("/cases/{case_id}/raw")
def case_raw(case_id: str):
    case = get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return case


@app.delete("/cases/{case_id}")
def case_delete(case_id: str):
    deleted = delete_case(case_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Case not found")
    return {"deleted": True, "case_id": case_id}


@app.get("/memory/stats")
def memory_stats_endpoint():
    return memory_stats()


# ── Prompts ───────────────────────────────────────────────────────────────────

@app.get("/prompts")
def prompts():
    return list_prompts()


@app.get("/prompts/{name}")
def prompt_detail(name: str):
    try:
        prompt = get_prompt(name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")
    return prompt


@app.put("/prompts/{name}")
def prompt_update(name: str, payload: PromptUpdateRequest):
    try:
        return update_prompt(name, payload.content)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
