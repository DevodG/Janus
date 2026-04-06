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
from app.services.query_classifier import QueryClassifier, QueryType
from app.services.cache_manager import IntelligentCacheManager
from app.services.learning_filter import LearningFilter
from app.services.adaptive_intelligence import adaptive_intelligence
from app.services.memory_graph import MemoryGraph
from app.services.daemon import JanusDaemon
from app.services.adaptive_pipeline import adaptive_pipeline
from app.services.circadian_rhythm import CircadianRhythm
from app.services.dream_processor import DreamCycleProcessor
from app.services.context_engine import context_engine
from app.services.reflex_layer import reflex_layer
from app.services.self_reflection import self_reflection
from app.services.self_training import self_training_engine
from app.routers.simulation import router as simulation_router
from app.routers.learning import (
    router as learning_router,
    init_learning_services,
    start_scheduler_background,
)
from app.routers.sentinel import router as sentinel_router
from app.routers.finance import router as finance_router
from app.config import get_config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Janus", version=APP_VERSION)

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
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://devodg-janus-backend.hf.space",
        "https://janus-frontend.vercel.app",
    ],
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
        logger.warning(
            f"Slow request: {request.method} {request.url.path} took {elapsed:.1f}s"
        )

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

    # Start Janus daemon in background thread
    daemon_enabled = os.getenv("DAEMON_ENABLED", "true").lower() == "true"
    if daemon_enabled:
        try:
            import threading
            from app.services.daemon import janus_daemon

            daemon_thread = threading.Thread(
                target=janus_daemon.run, daemon=True, name="janus-daemon"
            )
            daemon_thread.start()
            logger.info("Janus daemon started in background thread")
        except Exception as e:
            logger.error(f"Failed to start Janus daemon: {e}")


# ── Health ────────────────────────────────────────────────────────────────────


@app.get("/health")
def health():
    return {"status": "ok", "version": APP_VERSION}


@app.get("/health/deep")
def health_deep():
    return deep_health()


@app.get("/context")
def get_context():
    """Get the current system context."""
    return context_engine.build_context("")


@app.get("/pending-thoughts")
def get_pending_thoughts():
    """Get pending thoughts the system wants to share."""
    thoughts = context_engine.get_pending_thoughts()
    return {
        "pending_thoughts": thoughts,
        "count": len(thoughts),
    }


@app.get("/self/opinions")
def get_opinions(topic: str = None):
    """Get the system's formed opinions."""
    return {"opinions": self_reflection.get_opinions(topic)}


@app.get("/self/corrections")
def get_corrections(topic: str = None):
    """Get corrections the user has made."""
    return {"corrections": self_reflection.get_corrections(topic)}


@app.get("/self/gaps")
def get_gaps():
    """Get knowledge gaps the system has identified."""
    return {"gaps": self_reflection.get_gaps()}


@app.get("/self/dataset")
def get_dataset_stats():
    """Get training dataset statistics."""
    return self_reflection.get_dataset_stats()


@app.get("/self/report")
def get_self_report():
    """Get full self-reflection report."""
    return {
        "opinions": self_reflection.get_opinions()[:10],
        "corrections": self_reflection.get_corrections()[:5],
        "gaps": self_reflection.get_gaps()[:5],
        "dataset": self_reflection.get_dataset_stats(),
        "self_model": self_reflection.self_model,
    }


@app.post("/self/correct")
def submit_correction(data: dict):
    """User submits a correction — the system remembers."""
    user_input = data.get("user_input", "")
    original = data.get("original", "")
    correction = data.get("correction", "")
    self_reflection.record_correction(user_input, original, correction)
    return {"status": "remembered"}


@app.post("/self/learn")
def trigger_learning(max_gaps: int = 3, max_datasets: int = 2, max_samples: int = 50):
    """Trigger autonomous learning cycle — search HF datasets for gaps."""
    from app.services.autonomous_learner import autonomous_learner

    result = autonomous_learner.run_learning_cycle(
        max_gaps=max_gaps,
        max_datasets_per_gap=max_datasets,
        max_samples_per_dataset=max_samples,
    )
    return result


@app.get("/self/learning-status")
def get_learning_status():
    """Get autonomous learner status."""
    from app.services.autonomous_learner import autonomous_learner

    return autonomous_learner.get_status()


@app.get("/self/fine-tuning")
def get_fine_tuning_stats():
    """Get fine-tuning dataset statistics."""
    from app.services.fine_tuning_builder import fine_tuning_builder

    return fine_tuning_builder.get_stats()


@app.get("/self/datasets")
def get_available_datasets(topic: str = None):
    """Search HF Hub for relevant datasets."""
    from app.services.hf_dataset_searcher import hf_dataset_searcher

    if topic:
        return {"datasets": hf_dataset_searcher.search_for_gap(topic)}
    return {"curated": hf_dataset_searcher.get_curated_datasets()}


@app.get("/self/training")
def get_training_report():
    """Get self-training report."""
    return self_training_engine.get_training_report()


@app.get("/config/status")
def config_status():
    return {
        "app_version": APP_VERSION,
        "groq_key_present": bool(os.getenv("GROQ_API_KEY")),
        "gemini_key_present": bool(os.getenv("GEMINI_API_KEY")),
        "openrouter_key_present": bool(os.getenv("OPENROUTER_API_KEY")),
        "ollama_base_url": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        "ollama_model": os.getenv("OLLAMA_MODEL", "llama3.2"),
        "tavily_enabled": bool(os.getenv("TAVILY_API_KEY")),
        "newsapi_enabled": bool(os.getenv("NEWS_API_KEY", os.getenv("NEWSAPI_KEY"))),
        "alphavantage_enabled": bool(
            os.getenv("ALPHA_VANTAGE_API_KEY", os.getenv("ALPHAVANTAGE_API_KEY"))
        ),
        "mirofish_base_url": os.getenv("MIROFISH_BASE_URL", "http://localhost:8001"),
        "api_discovery_endpoint": os.getenv(
            "API_DISCOVERY_ENDPOINT", "http://localhost:8002"
        ),
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


# ── Caching & Intelligence Services ──────────────────────────────────────────

query_classifier = QueryClassifier()
cache_manager = IntelligentCacheManager()
learning_filter = LearningFilter()
memory_graph = MemoryGraph()

# ── Background Daemon ────────────────────────────────────────────────────────

janus_daemon = None


def start_janus_daemon():
    """Start the background intelligence daemon."""
    global janus_daemon
    try:
        janus_daemon = JanusDaemon()
        import threading

        thread = threading.Thread(target=janus_daemon.run, daemon=True)
        thread.start()
        logger.info("Janus background daemon started")
    except Exception as e:
        logger.error(f"Failed to start Janus daemon: {e}")


start_janus_daemon()


# ── Case Execution ────────────────────────────────────────────────────────────


def _log_agent_errors(result: dict):
    """Log any agent errors from the pipeline result."""
    for agent_key in [
        "route",
        "research",
        "planner",
        "verifier",
        "simulation",
        "finance",
        "final",
    ]:
        agent_output = result.get(agent_key, {})
        if isinstance(agent_output, dict):
            if agent_output.get("status") == "error":
                logger.warning(
                    f"[AGENT ERROR] {agent_key}: {agent_output.get('reason', 'unknown')}"
                )
            elif agent_output.get("error"):
                logger.warning(
                    f"[AGENT ERROR] {agent_key}: {agent_output.get('error')}"
                )


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
        user_input = task.user_input
        logger.info("Processing /run: %s", user_input[:100])

        # Step 1: Try reflex layer first (instant, contextual, no model call)
        context = context_engine.build_context(user_input)
        reflex = reflex_layer.respond(user_input, context)
        if reflex:
            logger.info("Reflex layer responded instantly")
            context_engine.update_after_interaction(
                user_input, reflex.get("final_answer", ""), context
            )
            return reflex

        # Step 2: Classify the query
        query_type, query_confidence, query_meta = query_classifier.classify(user_input)
        domain = query_meta.get("detected_domain", "general")
        logger.info(
            f"Query classified: type={query_type.value}, domain={domain}, confidence={query_confidence:.2f}"
        )

        # Step 3: Try cache first
        cached = cache_manager.get(user_input)
        if cached:
            logger.info(
                f"Cache HIT ({cached['cache_age_hours']:.1f}h old, {cached['hit_count']} hits)"
            )
            context_engine.update_after_interaction(
                user_input, cached["answer"], context
            )
            return {
                "case_id": "",
                "user_input": user_input,
                "final_answer": cached["answer"],
                "cached": True,
                "cache_age_hours": round(cached["cache_age_hours"], 1),
                "query_type": cached["query_type"],
                "domain": cached["domain"],
                "route": {},
                "research": {},
                "final": {"response": cached["answer"], "confidence": 0.9},
                "outputs": [],
            }

        # Step 4: Get adaptive intelligence context
        ai_context = adaptive_intelligence.get_context_for_query(user_input, domain)
        logger.info(
            f"Adaptive context: {ai_context['total_cases_learned']} cases learned, personality_depth={ai_context['system_personality']['analytical_depth']:.2f}"
        )

        # Step 5: Run the full pipeline
        start = time.perf_counter()
        result = run_case(user_input)
        elapsed = time.perf_counter() - start

        # Log any agent errors
        _log_agent_errors(result)

        # Build response payload
        final = result.get("final", {})
        final_answer = final.get("response", final.get("summary", ""))
        payload = {
            "case_id": result.get("case_id", ""),
            "user_input": user_input,
            "route": result.get("route", {}),
            "research": result.get("research", {}),
            "simulation": result.get("simulation"),
            "finance": result.get("finance"),
            "final": final,
            "final_answer": final_answer,
            "outputs": [
                result.get("research", {}),
                final,
            ],
        }
        save_case(result.get("case_id", ""), payload)

        # Step 6: Cache the result
        cache_manager.put(
            query=user_input,
            answer=final_answer,
            query_type=query_type,
            domain=domain,
            model_insights=final.get("data_sources", []),
            metadata={
                "case_id": result.get("case_id", ""),
                "confidence": final.get("confidence", 0.5),
                "elapsed": round(elapsed, 1),
            },
        )
        logger.info(f"Result cached: type={query_type.value}, domain={domain}")

        # Step 6b: Store in memory graph
        case_id = result.get("case_id", "")
        memory_graph.add_query(
            query_id=case_id,
            text=user_input,
            type=query_type.value,
            domain=domain,
            confidence=final.get("confidence", 0.5),
            response_summary=final_answer[:200] if final_answer else None,
        )

        # Extract entities from response
        research = result.get("research", {})
        for fact in research.get("key_facts", []):
            words = fact.split()
            for word in words:
                cleaned = word.strip(".,;:()\"'")
                if cleaned and cleaned[0].isupper() and len(cleaned) > 2:
                    entity_id = cleaned.lower().replace(" ", "_")
                    memory_graph.add_entity(entity_id, cleaned, "entity")
                    memory_graph.link_query_entity(case_id, entity_id, 0.5)

        # Step 7: Learn from this case (adaptive intelligence)
        adaptive_intelligence.learn_from_case(payload, elapsed)
        logger.info(
            f"Adaptive intelligence updated: total_cases={adaptive_intelligence.total_cases}"
        )

        # Update context engine
        context_engine.update_after_interaction(user_input, final_answer, context)
        context_engine.record_performance(
            success=bool(final_answer),
            confidence=final.get("confidence", 0.5),
            elapsed=elapsed,
        )

        # Self-reflection: analyze own response quality
        self_reflection.reflect_on_response(
            user_input=user_input,
            response=final_answer,
            confidence=final.get("confidence", 0.5),
            data_sources=final.get("data_sources", []),
            gaps=final.get("caveats", []),
            elapsed=elapsed,
        )

        # Self-training: critique, refine prompts, improve responses
        training_result = self_training_engine.train_on_response(
            user_input=user_input,
            response=final_answer,
            confidence=final.get("confidence", 0.5),
            data_sources=final.get("data_sources", []),
            elapsed=elapsed,
            prompt_name="synthesizer",
        )
        logger.info(
            f"Self-training cycle #{training_result['training_cycle']}: "
            f"score={training_result['prompt_score']}, "
            f"weaknesses={len(training_result['critique'].get('weaknesses', []))}"
        )

        # Step 8: Fire-and-forget: traditional learning
        should_learn, learn_reason = learning_filter.should_learn(
            query_type=query_type,
            query=user_input,
            answer=final_answer,
            domain=domain,
            metadata=query_meta,
        )
        if should_learn:
            _fire_and_forget_learning(payload)
            logger.info(f"Learning triggered: {learn_reason}")
        else:
            logger.info(f"Learning skipped: {learn_reason}")

        # Add metadata to response
        payload["query_type"] = query_type.value
        payload["domain"] = domain
        payload["cached"] = False
        payload["learned"] = should_learn
        payload["learning_reason"] = learn_reason
        payload["elapsed_seconds"] = round(elapsed, 1)
        payload["adaptive_context"] = {
            "total_cases_learned": adaptive_intelligence.total_cases,
            "domain_expertise_level": ai_context.get("domain_expertise", {}).get(
                "case_count", 0
            ),
            "memory_graph": memory_graph.get_stats(),
        }

        return payload
    except Exception as e:
        logger.exception("Error in /run")
        raise HTTPException(
            status_code=500, detail="Failed to process request. Please try again."
        )


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
        raise HTTPException(
            status_code=500, detail="Failed to process request. Please try again."
        )


@app.post("/run/fast")
def run_fast(task: UserTask):
    """Run with adaptive pipeline — automatically optimizes depth based on query complexity."""
    try:
        result = adaptive_pipeline.run(task.user_input)
        return result
    except Exception as e:
        logger.exception("Error in /run/fast")
        raise HTTPException(
            status_code=500, detail="Failed to process request. Please try again."
        )


@app.get("/pipeline/stats")
def pipeline_stats():
    """Get adaptive pipeline statistics."""
    return adaptive_pipeline.get_stats()


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
        raise HTTPException(
            status_code=500, detail="Failed to run agent. Please try again."
        )


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


# ── Intelligence & Caching Endpoints ─────────────────────────────────────────


@app.get("/intelligence/report")
def intelligence_report():
    """Get the full adaptive intelligence report."""
    return adaptive_intelligence.get_full_intelligence_report()


@app.get("/intelligence/domain/{domain}")
def domain_intelligence(domain: str):
    """Get domain-specific expertise level."""
    expertise = adaptive_intelligence.domain_expertise.get(domain)
    if not expertise:
        return {
            "domain": domain,
            "case_count": 0,
            "message": "No expertise accumulated yet",
        }
    return expertise.get_expertise_summary()


@app.get("/cache/stats")
def cache_stats():
    """Get cache statistics."""
    return cache_manager.get_stats()


@app.post("/cache/cleanup")
def cache_cleanup():
    """Clean up expired cache entries."""
    expired = cache_manager.cleanup_expired()
    adaptive_intelligence.save()
    return {
        "expired_removed": expired,
        "cache_stats": cache_manager.get_stats(),
        "adaptive_cases": adaptive_intelligence.total_cases,
    }


@app.post("/intelligence/save")
def intelligence_save():
    """Force save all adaptive intelligence."""
    adaptive_intelligence.save()
    return {"saved": True, "total_cases": adaptive_intelligence.total_cases}


# ── Living System Endpoints ──────────────────────────────────────────────────


@app.get("/daemon/status")
def daemon_status():
    """Get background daemon status."""
    if janus_daemon:
        return janus_daemon.get_status()
    return {"running": False, "message": "Daemon not started"}


@app.get("/daemon/alerts")
def daemon_alerts(limit: int = 20, min_severity: str = "low"):
    """Get alerts from the signal queue."""
    if janus_daemon:
        return janus_daemon.signal_queue.get_alerts(
            limit=limit, min_severity=min_severity
        )
    return []


@app.get("/daemon/watchlist")
def daemon_watchlist():
    """Get current watchlist status."""
    if janus_daemon:
        return janus_daemon.market_watcher.get_watchlist_status()
    return []


@app.get("/daemon/events")
def daemon_events(limit: int = 20, event_type: str = None):
    """Get detected events."""
    if janus_daemon:
        if event_type:
            return janus_daemon.event_detector.get_events_by_type(event_type)
        return janus_daemon.event_detector.get_recent_events(limit=limit)
    return []


@app.get("/daemon/circadian")
def daemon_circadian():
    """Get circadian rhythm status."""
    if janus_daemon:
        return janus_daemon.circadian.get_status()
    return {"running": False}


@app.get("/daemon/dreams")
def daemon_dreams(limit: int = 10):
    """Get dream history."""
    if janus_daemon:
        return janus_daemon.dream_processor.get_dream_history(limit=limit)
    return []


@app.post("/daemon/dream/now")
def trigger_dream_cycle():
    """Manually trigger a dream cycle."""
    if janus_daemon:
        dream_report = janus_daemon.dream_processor.run_dream_cycle(
            memory_graph=memory_graph,
            adaptive_intelligence=adaptive_intelligence,
        )
        janus_daemon.last_dream = dream_report
        return dream_report
    return {"error": "Daemon not running"}


@app.get("/daemon/curiosity")
def daemon_curiosity():
    """Get curiosity engine status."""
    if janus_daemon:
        return janus_daemon.curiosity.get_status()
    return {"running": False}


@app.get("/daemon/curiosity/discoveries")
def curiosity_discoveries(limit: int = 10):
    """Get curiosity discoveries."""
    if janus_daemon:
        return janus_daemon.curiosity.get_discoveries(limit=limit)
    return []


@app.get("/daemon/curiosity/interests")
def curiosity_interests():
    """Get curiosity interests."""
    if janus_daemon:
        return janus_daemon.curiosity.get_interests()
    return {}


@app.post("/daemon/curiosity/now")
def trigger_curiosity_cycle():
    """Manually trigger a curiosity cycle."""
    if janus_daemon:
        report = janus_daemon.curiosity.run_curiosity_cycle()
        janus_daemon.last_curiosity_cycle = report
        return report
    return {"error": "Daemon not running"}


@app.get("/memory/stats")
def memory_graph_stats():
    """Get memory graph statistics."""
    return memory_graph.get_stats()


@app.get("/memory/queries")
def memory_queries(domain: str = None, search: str = None, limit: int = 20):
    """Query the memory graph."""
    if search:
        return memory_graph.search_queries(search, limit=limit)
    if domain:
        return memory_graph.get_queries_by_domain(domain, limit=limit)
    return {"message": "Use 'search' or 'domain' parameter"}


@app.get("/memory/related/{query_id}")
def memory_related(query_id: str, limit: int = 5):
    """Get queries related to a given query."""
    return memory_graph.get_related_queries(query_id, limit=limit)
