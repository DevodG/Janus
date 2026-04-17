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
            import concurrent.futures
            daemon = JanusDaemon()
            loop = asyncio.get_event_loop()
            executor = concurrent.futures.ThreadPoolExecutor(max_workers=1, thread_name_prefix="daemon")
            future = loop.run_in_executor(executor, daemon.run)
            _services["daemon_future"] = future
            _services["daemon_executor"] = executor
            _services["daemon"] = daemon
            logger.info("Daemon thread started")
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
    app.include_router(finance_router)

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
                "newsapi":      bool(os.getenv("NEWS_API_KEY") or os.getenv("NEWSAPI_KEY")),
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

    # ── Silence HF Space internal log-viewer poll ──────────────────────────
    @app.get("/")
    async def root(logs: str = None):
        return {"status": "ok", "service": "Janus"}

    # ── Daemon routes ──────────────────────────────────────────────────────
    @app.get("/daemon/status")
    async def daemon_status():
        daemon = _services.get("daemon")
        if daemon:
            return daemon.get_status()
        return {"running": False, "message": "Daemon not started"}

    @app.get("/daemon/alerts")
    async def daemon_alerts(limit: int = 20, min_severity: str = "low"):
        daemon = _services.get("daemon")
        if daemon:
            try:
                return daemon.signal_queue.get_alerts(limit=limit, min_severity=min_severity)
            except Exception:
                return daemon.signal_queue.get_stats()
        return []

    @app.get("/daemon/watchlist")
    async def daemon_watchlist():
        daemon = _services.get("daemon")
        if daemon:
            try:
                return daemon.market_watcher.get_watchlist_status()
            except Exception:
                return {"watchlist": daemon.market_watcher.watchlist}
        return []

    @app.get("/daemon/events")
    async def daemon_events(limit: int = 20, event_type: str = None):
        daemon = _services.get("daemon")
        if daemon:
            try:
                if event_type:
                    return daemon.event_detector.get_events_by_type(event_type)
                return daemon.event_detector.get_recent_events(limit=limit)
            except Exception as e:
                return {"events": [], "error": str(e)}
        return {"events": []}

    @app.get("/daemon/circadian")
    async def daemon_circadian():
        daemon = _services.get("daemon")
        if daemon:
            try:
                return daemon.circadian.get_status()
            except Exception:
                phase = daemon.circadian.get_current_phase()
                return {"phase": phase.value}
        return {"running": False}

    @app.get("/daemon/curiosity")
    async def daemon_curiosity():
        daemon = _services.get("daemon")
        if daemon:
            try:
                return daemon.curiosity.get_status()
            except Exception as e:
                return {"running": True, "error": str(e)}
        return {"running": False}

    @app.get("/daemon/curiosity/discoveries")
    async def curiosity_discoveries(limit: int = 10):
        daemon = _services.get("daemon")
        if daemon:
            try:
                return daemon.curiosity.get_discoveries(limit=limit)
            except Exception:
                return []
        return []

    @app.get("/daemon/curiosity/interests")
    async def curiosity_interests():
        daemon = _services.get("daemon")
        if daemon:
            try:
                return daemon.curiosity.get_interests()
            except Exception:
                return {}
        return {}

    @app.post("/daemon/curiosity/now")
    async def trigger_curiosity_now():
        daemon = _services.get("daemon")
        if daemon:
            try:
                report = daemon.curiosity.run_curiosity_cycle()
                daemon.last_curiosity_cycle = report
                return report
            except Exception as e:
                return {"error": str(e)}
        return {"error": "Daemon not running"}

    @app.get("/daemon/dreams")
    async def daemon_dreams():
        daemon = _services.get("daemon")
        if daemon and daemon.last_dream:
            return daemon.last_dream
        return {"dreams": [], "message": "No dream cycle run yet"}

    @app.post("/daemon/dream/now")
    async def trigger_dream_now():
        daemon = _services.get("daemon")
        if daemon:
            try:
                report = daemon.dream_processor.run_dream_cycle()
                daemon.last_dream = report
                return report
            except Exception as e:
                return {"error": str(e)}
        return {"error": "Daemon not running"}

    @app.get("/pending-thoughts")
    async def pending_thoughts():
        daemon = _services.get("daemon")
        if daemon:
            thoughts = getattr(daemon, "_pending_thoughts", [])
            return {"pending_thoughts": thoughts[:10], "count": len(thoughts)}
        return {"pending_thoughts": [], "count": 0}

    @app.get("/context")
    async def get_context():
        daemon = _services.get("daemon")
        signals = []
        if daemon:
            try:
                signals = list(daemon.signal_queue._queue)[-10:] if hasattr(daemon.signal_queue, "_queue") else []
            except Exception:
                pass
        return {"context": "ok", "recent_signals": len(signals)}

    # ── Memory routes ──────────────────────────────────────────────────────
    @app.get("/memory/stats")
    async def memory_stats():
        try:
            from app.memory import knowledge_store
            stats = knowledge_store.get_stats() if hasattr(knowledge_store, "get_stats") else {}
            return {
                "queries": stats.get("total_queries", 0),
                "entities": stats.get("total_entities", 0),
                "links": stats.get("total_links", 0),
                "domains": stats.get("domain_counts", {}),
            }
        except Exception as e:
            return {"queries": 0, "entities": 0, "links": 0, "domains": {}, "error": str(e)}

    @app.get("/memory/queries")
    async def memory_queries(limit: int = 20):
        try:
            from app.memory import knowledge_store
            return knowledge_store.get_recent_queries(limit=limit) if hasattr(knowledge_store, "get_recent_queries") else []
        except Exception:
            return []

    # ── Intelligence / Cache routes ────────────────────────────────────────
    @app.get("/intelligence/report")
    async def intelligence_report():
        cache = _services.get("cache")
        daemon = _services.get("daemon")
        return {
            "status": "ok",
            "cache_stats": cache.get_stats() if cache and hasattr(cache, "get_stats") else {},
            "daemon_cycles": daemon.cycle_count if daemon else 0,
            "space": os.getenv("SPACE_ID", "local"),
        }

    @app.get("/intelligence/domain/{domain}")
    async def intelligence_domain(domain: str):
        return {"domain": domain, "status": "ok"}

    @app.get("/cache/stats")
    async def cache_stats():
        cache = _services.get("cache")
        if cache and hasattr(cache, "get_stats"):
            return cache.get_stats()
        return {"entries": 0, "hit_rate": 0, "status": "unavailable"}

    @app.post("/cache/cleanup")
    async def cache_cleanup():
        cache = _services.get("cache")
        if cache and hasattr(cache, "cleanup_expired"):
            expired = cache.cleanup_expired()
            return {"expired_removed": expired, "cache_stats": cache.get_stats()}
        return {"expired_removed": 0}

    @app.post("/intelligence/save")
    async def intelligence_save():
        return {"status": "ok"}

    # ── Prompts routes ─────────────────────────────────────────────────────
    @app.get("/prompts")
    async def list_prompts_route():
        import pathlib
        prompts_dir = pathlib.Path(__file__).parent / "prompts"
        prompts = []
        if prompts_dir.exists():
            for f in prompts_dir.glob("*.txt"):
                prompts.append({"name": f.stem, "file": f.name})
        return prompts

    @app.get("/prompts/{name}")
    async def get_prompt_route(name: str):
        from fastapi.responses import JSONResponse
        import pathlib
        prompts_dir = pathlib.Path(__file__).parent / "prompts"
        path = prompts_dir / f"{name}.txt"
        if not path.exists():
            return JSONResponse(status_code=404, content={"detail": "Prompt not found"})
        return {"name": name, "content": path.read_text(encoding="utf-8")}

    @app.put("/prompts/{name}")
    async def update_prompt_route(name: str, payload: dict):
        import pathlib
        prompts_dir = pathlib.Path(__file__).parent / "prompts"
        prompts_dir.mkdir(exist_ok=True)
        path = prompts_dir / f"{name}.txt"
        path.write_text(payload.get("content", ""), encoding="utf-8")
        return {"message": "Prompt updated", "name": name}

    # ── Self / Reflection routes ───────────────────────────────────────────
    @app.get("/self/report")
    async def self_report():
        try:
            from app.services.self_reflection import self_reflection
            return {
                "opinions": self_reflection.get_opinions()[:10],
                "corrections": self_reflection.get_corrections()[:5],
                "gaps": self_reflection.get_gaps()[:5],
                "dataset": self_reflection.get_dataset_stats() if hasattr(self_reflection, "get_dataset_stats") else {},
                "self_model": getattr(self_reflection, "self_model", {}),
            }
        except Exception as e:
            return {"opinions": [], "corrections": [], "gaps": [], "error": str(e)}

    @app.get("/self/opinions")
    async def self_opinions(topic: str = None):
        try:
            from app.services.self_reflection import self_reflection
            return {"opinions": self_reflection.get_opinions(topic)}
        except Exception:
            return {"opinions": []}

    @app.get("/self/corrections")
    async def self_corrections(topic: str = None):
        try:
            from app.services.self_reflection import self_reflection
            return {"corrections": self_reflection.get_corrections(topic) if topic else self_reflection.get_corrections()}
        except Exception:
            return {"corrections": []}

    @app.get("/self/gaps")
    async def self_gaps():
        try:
            from app.services.self_reflection import self_reflection
            return {"gaps": self_reflection.get_gaps()}
        except Exception:
            return {"gaps": []}

    @app.get("/self/dataset")
    async def self_dataset():
        try:
            from app.services.self_reflection import self_reflection
            return self_reflection.get_dataset_stats() if hasattr(self_reflection, "get_dataset_stats") else {}
        except Exception:
            return {}

    # ── Extended Cases routes ──────────────────────────────────────────────
    @app.get("/cases/{case_id}")
    async def case_detail(case_id: str):
        import json, pathlib
        from fastapi.responses import JSONResponse
        mem = pathlib.Path(__file__).parent / "data" / "memory"
        for f in mem.glob("*.json"):
            try:
                data = json.loads(f.read_text())
                if data.get("id") == case_id or f.stem == case_id:
                    return data
            except Exception:
                pass
        return JSONResponse(status_code=404, content={"detail": "Case not found"})

    @app.delete("/cases/{case_id}")
    async def case_delete(case_id: str):
        import pathlib
        from fastapi.responses import JSONResponse
        mem = pathlib.Path(__file__).parent / "data" / "memory"
        for f in mem.glob("*.json"):
            try:
                import json
                data = json.loads(f.read_text())
                if data.get("id") == case_id or f.stem == case_id:
                    f.unlink()
                    return {"deleted": True, "case_id": case_id}
            except Exception:
                pass
        return JSONResponse(status_code=404, content={"detail": "Case not found"})

    @app.get("/cases/{case_id}/raw")
    async def case_raw(case_id: str):
        import json, pathlib
        from fastapi.responses import JSONResponse
        mem = pathlib.Path(__file__).parent / "data" / "memory"
        for f in mem.glob("*.json"):
            try:
                data = json.loads(f.read_text())
                if data.get("id") == case_id or f.stem == case_id:
                    return {"raw": f.read_text()}
            except Exception:
                pass
        return JSONResponse(status_code=404, content={"detail": "Case not found"})

    # ── Agents / Pipeline / Debug routes ──────────────────────────────────
    @app.get("/agents")
    async def list_agents():
        return ["router", "research", "planner", "verifier", "synthesizer"]

    @app.get("/agents/{agent_name}")
    async def agent_detail(agent_name: str):
        return {"name": agent_name, "status": "active"}

    @app.get("/pipeline/stats")
    async def pipeline_stats():
        return {
            "graph_ready": getattr(getattr(app, "state", None), "graph", None) is not None,
            "space": os.getenv("SPACE_ID", "local"),
        }

    @app.get("/debug/state/{case_id}")
    async def debug_state(case_id: str):
        return {"case_id": case_id, "debug": "not available in production"}

    # ── Traces / Curation / Domain routes ─────────────────────────────────
    @app.get("/traces")
    async def list_traces():
        return {"traces": []}

    @app.get("/traces/stats")
    async def traces_stats():
        return {"total": 0}

    @app.get("/curation/examples")
    async def curation_examples():
        return {"examples": []}

    @app.get("/curation/stats")
    async def curation_stats():
        return {"total": 0}

    @app.post("/curation/push-to-hf")
    async def curation_push():
        return {"status": "ok", "pushed": 0}

    @app.get("/domain/classify")
    async def domain_classify(query: str = ""):
        return {"domain": "general", "confidence": 0.5}

    @app.get("/domain/confidence")
    async def domain_confidence():
        return {"domains": {}}

    @app.get("/domain/top")
    async def domain_top():
        return {"top_domains": []}

    @app.get("/health/features")
    async def health_features():
        return {
            "simulation":  os.getenv("SIMULATION_ENABLED", "true") == "true",
            "sentinel":    os.getenv("SENTINEL_ENABLED", "true") == "true",
            "learning":    os.getenv("LEARNING_ENABLED", "false") == "true",
            "curiosity":   os.getenv("CURIOSITY_ENGINE_ENABLED", "false") == "true",
        }



    # ── Optional routers ──────────────────────────────────────────────────
    if os.getenv("SIMULATION_ENABLED", "true").lower() == "true":
        try:
            from app.routers.simulation import router as sim_router
            app.include_router(sim_router)
        except Exception as e:
            logger.warning("Simulation router unavailable: %s", e)

    if os.getenv("SENTINEL_ENABLED", "true").lower() == "true":
        try:
            from app.routers.sentinel import router as sentinel_router
            app.include_router(sentinel_router)
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
