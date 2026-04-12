"""
backend/app/main.py — HF Spaces-compatible version

Key differences from local dev:
  1. PORT = 7860 (HF default) — configurable via $PORT env var
  2. CORS must allow the frontend Space URL, not just localhost
  3. All data dir creation is in-memory safe (dirs reset on restart)
  4. Daemon uses asyncio.create_task, not threading — safer in HF's container
  5. Lifespan has singleton guard so --reload doesn't double-start services
  6. /health supports HEAD (HF health checker uses HEAD)
"""
import asyncio
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

# ── Singleton guards ───────────────────────────────────────────────────────
_started = False
_services: dict = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _started

    # 1. Ensure runtime dirs exist (they will be empty after HF Space restart)
    _ensure_dirs()

    # 2. Log configuration warnings — never crash on missing optional keys
    _log_config_warnings()

    # 3. Response cache (always on)
    try:
        from app.services.response_cache import ResponseCache
        _services["cache"] = ResponseCache()
        app.state.cache = _services["cache"]
        logger.info("ResponseCache ready")
    except Exception as e:
        logger.warning("ResponseCache unavailable: %s", e)
        app.state.cache = None

    # 4. Compile LangGraph — degrade to 503 on /run rather than crash
    app.state.graph = None
    try:
        from app.graph import build_graph
        app.state.graph = build_graph()
        logger.info("LangGraph pipeline compiled OK")
    except Exception as e:
        logger.error("LangGraph build FAILED: %s — /run will 503", e)

    # 5. Daemon — exactly once even if uvicorn reloads
    if not _started:
        _started = True
        try:
            from app.services.daemon import JanusDaemon
            daemon = JanusDaemon()
            task = asyncio.create_task(daemon.run_forever())
            _services["daemon_task"] = task
            _services["daemon"] = daemon
            logger.info("Daemon task started")
        except Exception as e:
            logger.error("Daemon failed to start: %s", e)

    # 6. Optional adaptive intelligence
    app.state.adaptive = None
    if os.getenv("ADAPTIVE_INTELLIGENCE_ENABLED", "false").lower() == "true":
        try:
            from app.services.adaptive_intelligence import AdaptiveIntelligence
            app.state.adaptive = AdaptiveIntelligence()
            logger.info("AdaptiveIntelligence ready")
        except Exception as e:
            logger.error("AdaptiveIntelligence failed: %s", e)

    logger.info("Janus ready on port %s", os.getenv("PORT", "7860"))
    yield  # ← server is live

    # Shutdown
    for name, svc in _services.items():
        try:
            if asyncio.iscoroutine(svc) or asyncio.isfuture(svc):
                svc.cancel()
            elif hasattr(svc, "stop"):
                stop = svc.stop()
                if asyncio.iscoroutine(stop):
                    await stop
        except Exception as e:
            logger.error("Shutdown error for %s: %s", name, e)


def _ensure_dirs():
    """Create runtime data dirs — called at every startup since HF FS is ephemeral."""
    import pathlib
    base = pathlib.Path(__file__).parent / "data"
    for d in [
        "memory", "simulations", "logs", "knowledge",
        "skills", "prompt_versions", "learning", "adaptive",
        "cache", "sentinel", "sentinel/pending_patches",
    ]:
        (base / d).mkdir(parents=True, exist_ok=True)


def _log_config_warnings():
    """Warn about missing keys — useful in HF Space logs."""
    provider = os.getenv("PRIMARY_PROVIDER", "openrouter")
    key_map = {
        "openrouter": "OPENROUTER_API_KEY",
        "openai":     "OPENAI_API_KEY",
        "groq":       "GROQ_API_KEY",
        "gemini":     "GEMINI_API_KEY",
    }
    key_name = key_map.get(provider, "OPENROUTER_API_KEY")
    if not os.getenv(key_name):
        logger.warning("⚠ %s is not set in Space Secrets — LLM calls will fail", key_name)
    if not os.getenv("TAVILY_API_KEY"):
        logger.warning("⚠ TAVILY_API_KEY not set — web search disabled")
    if not any([
        os.getenv("ALPHAVANTAGE_API_KEY"),
        os.getenv("FINNHUB_API_KEY"),
        os.getenv("FMP_API_KEY"),
    ]):
        logger.warning("⚠ No market data API key set — historical charts will use yfinance only")
    if os.getenv("SPACE_ID") and not os.getenv("HF_STORE_REPO"):
        logger.warning(
            "⚠ Running on HF Space but HF_STORE_REPO not set. "
            "All memory/cases/skills will be LOST on every restart. "
            "Create a private dataset repo and add HF_STORE_REPO=username/janus-memory to Secrets."
        )


def create_app() -> FastAPI:
    app = FastAPI(
        title="Janus",
        description="Cognitive Intelligence Interface",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # ── CORS — critical for HF Spaces cross-origin calls ─────────────────
    # Frontend Space and backend Space have different origins
    raw_origins = os.getenv("ALLOWED_ORIGINS", "")
    allowed_origins = [o.strip() for o in raw_origins.split(",") if o.strip()]

    # Always include HF Space patterns + localhost for dev
    hf_space_id = os.getenv("SPACE_ID", "")
    if hf_space_id:
        # HF Space URLs follow pattern: https://{owner}-{space-name}.hf.space
        owner = hf_space_id.split("/")[0] if "/" in hf_space_id else hf_space_id
        allowed_origins.extend([
            f"https://{owner.lower()}-*.hf.space",   # wildcard for all spaces from same owner
            f"https://huggingface.co",
        ])

    # Always allow localhost for local dev/testing
    allowed_origins.extend([
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
    ])

    # If no specific origins configured, allow all (appropriate for public APIs)
    if not allowed_origins or os.getenv("CORS_ALLOW_ALL", "false").lower() == "true":
        allowed_origins = ["*"]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=allowed_origins != ["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Routers — always on ───────────────────────────────────────────────
    from app.routers.finance import router as finance_router
    app.include_router(finance_router, prefix="/finance", tags=["finance"])

    # ── Health (supports HEAD for HF health checker) ──────────────────────
    @app.api_route("/health", methods=["GET", "HEAD"])
    async def health(request=None):
        from fastapi import Request
        graph_ok = getattr(getattr(app, "state", None), "graph", None) is not None
        return {
            "status":  "ok" if graph_ok else "degraded",
            "graph":   "ready" if graph_ok else "failed",
            "space":   os.getenv("SPACE_ID", "local"),
            "version": "1.0.0",
        }

    @app.get("/health/deep")
    async def health_deep():
        graph_ok = getattr(getattr(app, "state", None), "graph", None) is not None
        return {
            "status": "ok" if graph_ok else "degraded",
            "space":  os.getenv("SPACE_ID", "local"),
            "features": {
                "simulation":  os.getenv("SIMULATION_ENABLED",    "true") == "true",
                "sentinel":    os.getenv("SENTINEL_ENABLED",       "true") == "true",
                "learning":    os.getenv("LEARNING_ENABLED",       "false") == "true",
                "adaptive":    os.getenv("ADAPTIVE_INTELLIGENCE_ENABLED", "false") == "true",
                "training":    os.getenv("CONTINUOUS_TRAINING_ENABLED",   "false") == "true",
                "curiosity":   os.getenv("CURIOSITY_ENGINE_ENABLED",      "false") == "true",
            },
            "data_sources": {
                "yfinance":     True,   # always available, no key needed
                "alphavantage": bool(os.getenv("ALPHAVANTAGE_API_KEY")),
                "finnhub":      bool(os.getenv("FINNHUB_API_KEY")),
                "fmp":          bool(os.getenv("FMP_API_KEY")),
                "eodhd":        bool(os.getenv("EODHD_API_KEY")),
                "tavily":       bool(os.getenv("TAVILY_API_KEY")),
                "newsapi":      bool(os.getenv("NEWSAPI_KEY") or os.getenv("NEWSAPI_API_KEY")),
            },
            "persistence": {
                "hf_store": bool(os.getenv("HF_STORE_REPO")),
                "ephemeral": os.getenv("SPACE_ID", "") != "" and not os.getenv("HF_STORE_REPO"),
            },
        }

    @app.post("/run")
    async def run_query(body: dict, background_tasks=None):
        from fastapi import BackgroundTasks
        from fastapi.responses import JSONResponse
        if getattr(getattr(app, "state", None), "graph", None) is None:
            return JSONResponse(
                status_code=503,
                content={"error": "Agent pipeline unavailable", "check": "/health/deep"}
            )
        try:
            result = await app.state.graph.ainvoke({
                "query": body.get("query", ""),
                "mode":  body.get("mode", "standard"),
            })
            return result
        except Exception as e:
            logger.error("Pipeline error: %s", e)
            return JSONResponse(status_code=500, content={"error": str(e)})

    @app.get("/cases")
    async def list_cases():
        import json, pathlib
        mem = pathlib.Path(__file__).parent / "data" / "memory"
        cases = []
        if mem.exists():
            for f in sorted(mem.glob("*.json"), reverse=True)[:50]:
                try:
                    cases.append(json.loads(f.read_text()))
                except Exception:
                    pass
        return {"cases": cases, "count": len(cases)}

    @app.get("/config/status")
    async def config_status():
        return {
            "primary_provider": os.getenv("PRIMARY_PROVIDER", "openrouter"),
            "space_id":         os.getenv("SPACE_ID", "local"),
            "persistent_store": bool(os.getenv("HF_STORE_REPO")),
        }

    # ── Optional routers ──────────────────────────────────────────────────
    if os.getenv("SIMULATION_ENABLED", "true").lower() == "true":
        try:
            from app.routers.simulation import router as sim_router
            app.include_router(sim_router, prefix="/simulation", tags=["simulation"])
        except Exception as e:
            logger.warning("Simulation router unavailable: %s", e)

    if os.getenv("SENTINEL_ENABLED", "true").lower() == "true":
        try:
            from app.routers.sentinel import router as sentinel_router
            app.include_router(sentinel_router, prefix="/sentinel", tags=["sentinel"])
        except Exception as e:
            logger.warning("Sentinel router unavailable: %s", e)

    if os.getenv("LEARNING_ENABLED", "false").lower() == "true":
        try:
            from app.routers.learning import router as learning_router
            app.include_router(learning_router, tags=["learning"])
        except Exception as e:
            logger.warning("Learning router unavailable: %s", e)

    # ── Prometheus metrics (optional but useful for HF Space monitoring) ──
    try:
        from prometheus_fastapi_instrumentator import Instrumentator
        Instrumentator().instrument(app).expose(app)
    except ImportError:
        pass

    return app


app = create_app()

# ── Entry point for HF Spaces ─────────────────────────────────────────────
# HF Spaces expects the server to bind on 0.0.0.0:7860
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "7860"))
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        log_level="info",
        reload=False,   # Never reload in production/HF Space
        workers=1,      # Single worker — HF free tier has limited RAM
    )
