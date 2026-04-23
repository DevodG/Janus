"""
backend/app/main.py — HF Spaces-compatible version

Key differences from local dev:
  1. PORT = 7860 (HF default) — configurable via $PORT env var
  2. Supports a bundled same-origin frontend, plus external UI origins when configured
  3. All data dir creation is in-memory safe (dirs reset on restart)
  4. Daemon uses asyncio.create_task, not threading — safer in HF's container
  5. Lifespan has singleton guard so --reload doesn't double-start services
  6. /health supports HEAD (HF health checker uses HEAD)
"""

import asyncio
from datetime import datetime
import json
import logging
import math
import os
import subprocess
import time
import uuid
from contextlib import asynccontextmanager
from typing import Optional, List, Dict, Any, Union

from fastapi import FastAPI, HTTPException, Request, UploadFile, File, Form
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

_FRONTEND_PROXY_METHODS = ["GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
_HOP_BY_HOP_HEADERS = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailer",
    "transfer-encoding",
    "upgrade",
    "content-encoding",
    "content-length",
}

_JANUS_PROVIDER_MODELS = [
    {
        "id": "janus-chat",
        "object": "model",
        "created": 1776500000,
        "owned_by": "janus",
        "description": "General Janus cognitive chat model backed by routing, memory, simulation, and verification.",
    },
    {
        "id": "janus-reasoner",
        "object": "model",
        "created": 1776500000,
        "owned_by": "janus",
        "description": "Janus reasoning mode with stronger deliberation and simulation for uncertain tasks.",
    },
    {
        "id": "janus-markets",
        "object": "model",
        "created": 1776500000,
        "owned_by": "janus",
        "description": "Janus market-aware mode with seeded global market and company knowledge.",
    },
    {
        "id": "janus-embed",
        "object": "model",
        "created": 1776500000,
        "owned_by": "janus",
        "description": "Deterministic Janus embedding model for semantic lookup and retrieval workflows.",
    },
]

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
    app.state.graph_error = "none"
    try:
        from app.graph import get_compiled_graph

        app.state.graph = get_compiled_graph()
        logger.info("LangGraph pipeline compiled OK")
    except Exception as e:
        import traceback
        app.state.graph_error = f"{e}\n{traceback.format_exc()}"
        logger.error("LangGraph build FAILED: %s — /run will 503", e)

    # 4b. Core cognition services used by the live request path
    try:
        from app.services.adaptive_intelligence import adaptive_intelligence
        from app.services.context_engine import context_engine
        from app.services.memory_manager import memory_manager
        from app.services.reflex_layer import reflex_layer
        from app.services.self_reflection import self_reflection

        app.state.adaptive = adaptive_intelligence
        app.state.context_engine = context_engine
        app.state.memory_manager = memory_manager
        app.state.reflex_layer = reflex_layer
        app.state.self_reflection = self_reflection
        logger.info("Core cognition services ready")
    except Exception as e:
        logger.error("Core cognition service init failed: %s", e)

    # 4c. Learning services for case-level experience accumulation
    app.state.learning_engine = None
    try:
        from app.config import get_config
        from app.routers import learning as learning_router_module

        learning_config = get_config()
        learning_router_module.init_learning_services(learning_config)
        app.state.learning_engine = learning_router_module.learning_engine
        if learning_config.learning_enabled:
            learning_router_module.start_scheduler_background()
        logger.info("Learning services ready")
    except Exception as e:
        logger.error("Learning services failed to initialize: %s", e)

    # 4d. Observation, curation, and classification services
    try:
        from app.services.curation import curator, hf_pusher
        from app.services.domain_classifier import domain_classifier
        from app.services.observation import get_tracer, scorer
        from app.services.query_classifier import QueryClassifier

        app.state.curator = curator
        app.state.domain_classifier = domain_classifier
        app.state.hf_pusher = hf_pusher
        app.state.query_classifier = QueryClassifier()
        app.state.trace_scorer = scorer
        app.state.tracer = get_tracer()
        logger.info("Observation and classification services ready")
    except Exception as e:
        logger.error("Observation/classification init failed: %s", e)

    try:
        await _start_frontend_server()
    except Exception as e:
        logger.error("Bundled frontend failed to start: %s", e)

    # 5. Daemon — exactly once even if uvicorn reloads
    if not _started:
        _started = True
        try:
            from app.services.daemon import JanusDaemon
            import concurrent.futures

            daemon = JanusDaemon()
            loop = asyncio.get_event_loop()
            executor = concurrent.futures.ThreadPoolExecutor(
                max_workers=1, thread_name_prefix="daemon"
            )
            future = loop.run_in_executor(executor, daemon.run)
            _services["daemon_future"] = future
            _services["daemon_executor"] = executor
            _services["daemon"] = daemon
            logger.info("Daemon thread started")
        except Exception as e:
            logger.error("Daemon failed to start: %s", e)

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
            elif hasattr(svc, "poll") and hasattr(svc, "terminate"):
                if svc.poll() is None:
                    svc.terminate()
                    try:
                        svc.wait(timeout=10)
                    except Exception:
                        svc.kill()
        except Exception as e:
            logger.error("Shutdown error for %s: %s", name, e)


def _ensure_dirs():
    """Create runtime data dirs — called at every startup since HF FS is ephemeral."""
    try:
        from app.config import ensure_data_dirs

        ensure_data_dirs()
        return
    except Exception as e:
        logger.warning("ensure_data_dirs() failed, using minimal dir set: %s", e)

    import pathlib

    base = pathlib.Path(__file__).parent / "data"
    for d in [
        "memory",
        "simulations",
        "logs",
        "knowledge",
        "skills",
        "prompt_versions",
        "learning",
        "adaptive",
        "cache",
        "sentinel",
        "sentinel/pending_patches",
    ]:
        (base / d).mkdir(parents=True, exist_ok=True)


def _log_config_warnings():
    """Warn about missing keys — useful in HF Space logs."""
    provider = os.getenv("PRIMARY_PROVIDER", "huggingface")
    key_map = {
        "huggingface": "HUGGINGFACE_API_KEY",
        "openrouter": "OPENROUTER_API_KEY",
        "openai": "OPENAI_API_KEY",
        "groq": "GROQ_API_KEY",
        "gemini": "GEMINI_API_KEY",
    }
    key_name = key_map.get(provider, "HUGGINGFACE_API_KEY")
    if not os.getenv(key_name):
        logger.warning(
            "⚠ %s is not set in Space Secrets — LLM calls will fail", key_name
        )
    if not os.getenv("TAVILY_API_KEY"):
        logger.warning("⚠ TAVILY_API_KEY not set — web search disabled")
    if not any(
        [
            os.getenv("ALPHAVANTAGE_API_KEY"),
            os.getenv("FINNHUB_API_KEY"),
            os.getenv("FMP_API_KEY"),
        ]
    ):
        logger.warning(
            "⚠ No market data API key set — historical charts will use yfinance only"
        )
    if os.getenv("SPACE_ID") and not os.getenv("HF_STORE_REPO"):
        logger.warning(
            "⚠ Running on HF Space but HF_STORE_REPO not set. "
            "All memory/cases/skills will be LOST on every restart. "
            "Create a private dataset repo and add HF_STORE_REPO=username/janus-memory to Secrets."
        )


def _normalize_route(route: dict | None) -> dict:
    normalized = dict(route or {})
    domain = normalized.get("domain_pack") or normalized.get("domain") or "general"
    normalized.setdefault("domain", domain)
    normalized.setdefault("domain_pack", domain)

    if "execution_mode" not in normalized:
        if normalized.get("requires_simulation"):
            normalized["execution_mode"] = "simulation"
        elif normalized.get("requires_finance_data"):
            normalized["execution_mode"] = "finance"
        else:
            normalized["execution_mode"] = "standard"

    return normalized


def _merge_context(base: dict, incoming: dict | None) -> dict:
    if not incoming:
        return base
    merged = dict(base)
    for key, value in incoming.items():
        if isinstance(merged.get(key), dict) and isinstance(value, dict):
            merged[key] = _merge_context(merged[key], value)
        else:
            merged[key] = value
    return merged


def _time_of_day() -> str:
    hour = datetime.now().hour
    if 5 <= hour < 12:
        return "morning"
    if 12 <= hour < 17:
        return "afternoon"
    if 17 <= hour < 22:
        return "evening"
    return "late night"


def _build_runtime_context(app: FastAPI, user_input: str, requested: dict | None) -> dict:
    from app.services.context_engine import context_engine
    from app.services.memory_manager import memory_manager
    from app.services.self_reflection import self_reflection
    from app.services.user_analyzer import user_analyzer

    context = context_engine.build_context(user_input)
    user_state = user_analyzer.analyze_query(user_input)

    daemon = _services.get("daemon")
    daemon_thoughts = list(getattr(daemon, "_pending_thoughts", [])[:3]) if daemon else []
    existing_thoughts = context.get("system_self", {}).get("pending_thoughts", [])
    thought_map = {}
    for thought in [*daemon_thoughts, *existing_thoughts]:
        text = thought.get("thought", "")
        if text and text not in thought_map:
            thought_map[text] = thought

    recent_discoveries = []
    if daemon and hasattr(daemon, "curiosity"):
        try:
            recent_discoveries = daemon.curiosity.get_discoveries(limit=3)
        except Exception:
            recent_discoveries = []

    total_cases = memory_manager.total_cases() if hasattr(memory_manager, "total_cases") else 0
    gaps = self_reflection.get_gaps()[:5]
    context["system_self"] = {
        **context.get("system_self", {}),
        "pending_thoughts": list(thought_map.values())[:5],
        "recent_discoveries": recent_discoveries,
        "capabilities": [
            "research",
            "simulation",
            "planning",
            "verification",
            "financial analysis",
        ],
        "weaknesses": [gap.get("reason", "") for gap in gaps[:3] if gap.get("reason")],
        "total_cases_analyzed": total_cases,
        "uptime": f"{getattr(daemon, 'cycle_count', 0)} daemon cycles" if daemon else "live session",
    }
    context["self_reflection"] = {
        "opinions": self_reflection.get_opinions()[:5],
        "corrections": self_reflection.get_corrections()[:5],
        "gaps": gaps,
        "self_model": getattr(self_reflection, "self_model", {}),
    }
    context["user_persona"] = user_state
    context["memory"] = {
        "similar_cases": memory_manager.find_similar(user_input, top_k=5)
    }

    adaptive = getattr(app.state, "adaptive", None)
    if adaptive and hasattr(adaptive, "get_context_for_query"):
        try:
            context["adaptive_intelligence"] = adaptive.get_context_for_query(
                user_input, "general"
            )
        except Exception as e:
            logger.debug("Adaptive context unavailable: %s", e)

    context["daemon"] = {
        "running": daemon is not None,
        "cycle_count": getattr(daemon, "cycle_count", 0),
        "circadian_phase": daemon.circadian.get_current_phase().value
        if daemon and hasattr(daemon, "circadian")
        else "offline",
    }
    context["environment"] = {"time_of_day": _time_of_day()}
    return _merge_context(context, requested)


def _build_case_outputs(result: dict) -> list[dict]:
    outputs = []

    def _append(agent: str, details: dict | None) -> None:
        if not isinstance(details, dict) or not details:
            return
        summary = (
            details.get("summary")
            or details.get("response")
            or details.get("estimated_output")
            or ""
        )
        outputs.append(
            {
                "agent": agent,
                "summary": str(summary),
                "confidence": float(details.get("confidence", 0.0) or 0.0),
                "details": details,
            }
        )

    _append("research", result.get("research"))
    _append("planner", result.get("planner"))
    _append("verifier", result.get("verifier"))
    _append("synthesizer", result.get("final"))
    return outputs


def _build_routing_path(case_payload: dict) -> str:
    path = ["switchboard"]
    if case_payload.get("simulation"):
        path.append("mirofish")
    elif case_payload.get("finance"):
        path.append("finance")
    path.extend(["research", "planner", "verifier", "synthesizer"])
    return " > ".join(path)


def _build_tool_results(case_payload: dict) -> list[dict]:
    tool_results = []
    sections = {
        "simulation": case_payload.get("simulation"),
        "finance": case_payload.get("finance"),
        "research": case_payload.get("research"),
        "planner": case_payload.get("planner"),
        "verifier": case_payload.get("verifier"),
    }

    for name, payload in sections.items():
        if not isinstance(payload, dict) or not payload:
            continue

        status = payload.get("status", "ok")
        if name == "verifier":
            status = "ok" if payload.get("passed", True) else "warning"
        if name == "planner" and str(payload.get("estimated_output", "")).lower().startswith("error"):
            status = "error"

        tool_results.append(
            {
                "tool": name,
                "status": status,
                "confidence": float(payload.get("confidence", 0.0) or 0.0),
            }
        )

    return tool_results


def _collect_case_errors(case_payload: dict) -> list[str]:
    errors: list[str] = []
    for name in ("research", "planner", "verifier", "finance", "simulation", "final"):
        payload = case_payload.get(name)
        if not isinstance(payload, dict) or not payload:
            continue

        if payload.get("status") == "error":
            errors.append(f"{name}: {payload.get('reason', 'unknown error')}")
        if name == "planner" and str(payload.get("estimated_output", "")).lower().startswith("error"):
            errors.append(f"planner: {payload.get('estimated_output')}")
        if name == "final":
            for caveat in payload.get("caveats", []):
                if "fail" in str(caveat).lower() or "error" in str(caveat).lower():
                    errors.append(f"final: {caveat}")
    return errors


def _record_observation_trace(app: FastAPI, case_payload: dict) -> dict:
    tracer = getattr(app.state, "tracer", None)
    trace_scorer = getattr(app.state, "trace_scorer", None)
    query_classifier = getattr(app.state, "query_classifier", None)
    curator = getattr(app.state, "curator", None)
    if tracer is None or trace_scorer is None:
        return {}

    user_input = case_payload.get("user_input", "")
    query_type = "unknown"
    detected_domain = case_payload.get("route", {}).get("domain", "general")
    if query_classifier and hasattr(query_classifier, "classify"):
        try:
            query_type_result, _, query_meta = query_classifier.classify(user_input)
            query_type = getattr(query_type_result, "value", str(query_type_result))
            if detected_domain == "general" and query_meta.get("detected_domain"):
                detected_domain = query_meta.get("detected_domain")
        except Exception as e:
            logger.debug("Query classification failed for trace: %s", e)

    trace_data = {
        "query": user_input,
        "query_type": query_type,
        "domain": detected_domain,
        "routing_path": _build_routing_path(case_payload),
        "provider_used": os.getenv("PRIMARY_PROVIDER", "unknown"),
        "output": case_payload.get("final_answer", ""),
        "output_length": len(case_payload.get("final_answer", "")),
        "latency_ms": int(float(case_payload.get("elapsed_seconds", 0) or 0) * 1000),
        "confidence": float(case_payload.get("final", {}).get("confidence", 0.0) or 0.0),
        "tool_results": _build_tool_results(case_payload),
        "data_sources": case_payload.get("final", {}).get("data_sources", []),
        "errors": _collect_case_errors(case_payload),
        "cached": False,
    }
    scoring = trace_scorer.score(trace_data)
    trace_data["score"] = scoring.get("score", 0.0)
    trace_data["score_breakdown"] = scoring.get("breakdown", {})

    trace_id = tracer.log_trace(trace_data)
    trace_info = {
        "trace_id": trace_id,
        "trace_score": trace_data["score"],
        "trace_score_breakdown": trace_data["score_breakdown"],
    }

    if curator is not None:
        try:
            trace_info["curation"] = curator.curate_trace({**trace_data, "trace_id": trace_id})
        except Exception as e:
            logger.error("Trace curation failed: %s", e)

    return trace_info


def _apply_post_run_learning(app: FastAPI, case_payload: dict, runtime_context: dict) -> None:
    from app.memory import save_case
    from app.services.context_engine import context_engine
    from app.services.memory_manager import memory_manager
    from app.services.self_reflection import self_reflection

    final = case_payload.get("final", {})
    final_answer = case_payload.get("final_answer", "")
    elapsed = float(case_payload.get("elapsed_seconds", 0) or 0)
    trace_info = _record_observation_trace(app, case_payload)
    case_payload.update(trace_info)
    quality_score = max(
        float(final.get("confidence", 0.0) or 0.0),
        float(trace_info.get("trace_score", 0.0) or 0.0),
    )

    topic = runtime_context.get("current_topic")
    daemon = _services.get("daemon")
    if daemon and getattr(daemon, "curiosity", None) and topic and topic != "general query":
        try:
            daemon.curiosity.add_interest(topic, score=min(0.08, 0.03 + quality_score * 0.05))
        except Exception as e:
            logger.error("Curiosity interest update failed: %s", e)

    if topic and topic != "general query" and quality_score < 0.45:
        try:
            context_engine.add_pending_thought(
                f"I still feel uncertain about {topic} and should revisit it with better evidence.",
                priority=0.7,
                source="post_run_doubt",
            )
        except Exception as e:
            logger.error("Pending thought update failed: %s", e)

    case_id = case_payload.get("case_id")
    if case_id:
        try:
            save_case(case_id, case_payload)
        except Exception as e:
            logger.error("Case persistence failed: %s", e)

    try:
        memory_manager.add_case(
            {
                **case_payload,
                "quality_score": quality_score,
                "domain": case_payload.get("route", {}).get("domain", "general"),
            }
        )
    except Exception as e:
        logger.error("Memory indexing failed: %s", e)

    try:
        context_engine.update_after_interaction(user_input=case_payload.get("user_input", ""), response=final_answer, context=runtime_context)
    except Exception as e:
        logger.error("Context update failed: %s", e)

    try:
        self_reflection.reflect_on_response(
            user_input=case_payload.get("user_input", ""),
            response=final_answer,
            confidence=float(final.get("confidence", 0.0) or 0.0),
            data_sources=final.get("data_sources", []),
            gaps=case_payload.get("research", {}).get("gaps", []),
            elapsed=elapsed,
        )
    except Exception as e:
        logger.error("Self-reflection update failed: %s", e)

    try:
        from app.services.self_training import self_training_engine
        
        training_stats = self_training_engine.train_on_response(
            user_input=case_payload.get("user_input", ""),
            response=final_answer,
            confidence=float(final.get("confidence", 0.0) or 0.0),
            data_sources=final.get("data_sources", []),
            elapsed=elapsed,
            prompt_name="synthesizer",
        )
        logger.info(f"Self-training cycle {training_stats.get('training_cycle')} complete. Prompt score: {training_stats.get('prompt_score')}")
    except Exception as e:
        logger.error("Self-training engine failed: %s", e)

    adaptive = getattr(app.state, "adaptive", None)
    if adaptive and hasattr(adaptive, "learn_from_case"):
        try:
            adaptive.learn_from_case(case_payload, elapsed)
        except Exception as e:
            logger.error("Adaptive learning failed: %s", e)

    learning_engine = getattr(app.state, "learning_engine", None)
    if learning_engine and hasattr(learning_engine, "learn_from_case"):
        try:
            learning_engine.learn_from_case(case_payload)
        except Exception as e:
            logger.error("Learning engine case update failed: %s", e)


def _message_content_to_text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict):
                if item.get("type") == "text":
                    parts.append(str(item.get("text", "")))
                elif "text" in item:
                    parts.append(str(item.get("text", "")))
            else:
                parts.append(str(item))
        return "\n".join(part for part in parts if part)
    return str(content or "")


def _extract_user_input_from_messages(messages: list[dict]) -> str:
    if not messages:
        return ""

    last_user = ""
    for message in messages[-12:]:
        role = str(message.get("role", "user"))
        content = _message_content_to_text(message.get("content", ""))
        if not content.strip():
            continue
        if role == "user":
            last_user = content.strip()
    return last_user or _message_content_to_text(messages[-1].get("content", "")).strip()


def _render_message_history(messages: list[dict]) -> list[dict]:
    rendered = []
    for message in messages[-12:]:
        content = _message_content_to_text(message.get("content", "")).strip()
        if not content:
            continue
        rendered.append(
            {
                "role": str(message.get("role", "user")),
                "content": content,
            }
        )
    return rendered


def _approx_tokens(text: str) -> int:
    return max(1, len((text or "").strip()) // 4)


def _provider_context_from_body(body: dict) -> dict:
    messages = body.get("messages") or []
    system_messages = [
        _message_content_to_text(message.get("content", ""))
        for message in messages
        if message.get("role") == "system"
    ]
    return {
        "provider_facade": {
            "model": body.get("model", "janus-chat"),
            "temperature": body.get("temperature", 0.7),
            "max_tokens": body.get("max_tokens") or body.get("max_completion_tokens"),
            "system_messages": [msg for msg in system_messages if msg],
            "conversation": _render_message_history(messages),
            "raw_message_count": len(messages),
        }
    }


async def _execute_case_request(app: FastAPI, body: dict) -> dict:
    from app.graph import run_case
    from app.services.reflex_layer import reflex_layer

    user_input = (body.get("user_input") or body.get("query") or "").strip()
    if not user_input:
        raise HTTPException(status_code=400, detail="Missing user_input")

    started_at = time.perf_counter()
    runtime_context = _build_runtime_context(app, user_input, body.get("context"))

    reflex_result = reflex_layer.respond(user_input, runtime_context)
    if reflex_result:
        reflex_answer = reflex_result.get("final_answer", "")
        try:
            from app.services.context_engine import context_engine

            context_engine.update_after_interaction(
                user_input=user_input,
                response=reflex_answer,
                context=runtime_context,
            )
        except Exception as e:
            logger.error("Reflex context update failed: %s", e)

        return {
            "case_id": reflex_result.get("case_id"),
            "user_input": user_input,
            "route": _normalize_route(reflex_result.get("route")),
            "research": reflex_result.get("research", {}),
            "planner": reflex_result.get("planner", {}),
            "verifier": reflex_result.get("verifier", {}),
            "simulation": reflex_result.get("simulation"),
            "finance": reflex_result.get("finance"),
            "final": {
                **reflex_result.get("final", {}),
                "response": reflex_answer,
            },
            "final_answer": reflex_answer,
            "elapsed_seconds": round(time.perf_counter() - started_at, 1),
        }

    result = await run_case(user_input, runtime_context)
    final = result.get("final", {})
    response = {
        "case_id": result.get("case_id"),
        "user_input": user_input,
        "route": _normalize_route(result.get("route")),
        "research": result.get("research", {}),
        "planner": result.get("planner", {}),
        "verifier": result.get("verifier", {}),
        "simulation": result.get("simulation"),
        "finance": result.get("finance"),
        "final": final,
        "final_answer": final.get("response") or final.get("summary") or "",
        "elapsed_seconds": round(time.perf_counter() - started_at, 1),
    }
    response["outputs"] = _build_case_outputs(response)
    _apply_post_run_learning(app, response, runtime_context)
    return response


def _check_provider_auth(request: Request) -> None:
    expected = os.getenv("JANUS_API_KEY", "").strip()
    if not expected:
        return

    auth = request.headers.get("authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer token")
    provided = auth.split(" ", 1)[1].strip()
    if provided != expected:
        raise HTTPException(status_code=401, detail="Invalid API key")


def _extract_ticker_symbol(text: str) -> str | None:
    import re

    company_map = {
        "nvidia": "NVDA",
        "apple": "AAPL",
        "microsoft": "MSFT",
        "amazon": "AMZN",
        "alphabet": "GOOGL",
        "google": "GOOGL",
        "meta": "META",
        "facebook": "META",
        "tesla": "TSLA",
        "tsmc": "TSM",
        "asml": "ASML",
        "jpmorgan": "JPM",
        "reliance": "RELIANCE",
        "infosys": "INFY",
    }
    lowered = (text or "").lower()
    for company, ticker in company_map.items():
        if company in lowered:
            return ticker

    matches = re.findall(r"\b[A-Z]{2,5}\b", text or "")
    if matches:
        return matches[0]
    return None


def _select_provider_tool_call(
    user_input: str, route: dict, tools: list[dict], tool_choice
) -> dict | None:
    if not tools:
        return None
    if tool_choice == "none":
        return None

    functions = [
        tool for tool in tools if isinstance(tool, dict) and tool.get("type") == "function"
    ]
    if not functions:
        return None

    explicit_name = None
    if isinstance(tool_choice, dict):
        explicit_name = (
            tool_choice.get("function", {}) or {}
        ).get("name")

    if explicit_name:
        chosen = next(
            (tool for tool in functions if tool.get("function", {}).get("name") == explicit_name),
            None,
        )
        if chosen is None:
            return None
    else:
        query_words = {
            token
            for token in __import__("re").findall(r"[a-z0-9_]+", (user_input or "").lower())
            if len(token) >= 3
        }
        scored = []
        for tool in functions:
            fn = tool.get("function", {})
            haystack = (
                f"{fn.get('name', '')} {fn.get('description', '')}"
            ).lower()
            overlap = sum(1 for word in query_words if word in haystack)
            if route.get("domain") and route.get("domain", "").lower() in haystack:
                overlap += 2
            if route.get("requires_finance_data") and any(
                hint in haystack for hint in ["finance", "market", "stock", "ticker"]
            ):
                overlap += 2
            if route.get("requires_simulation") and any(
                hint in haystack for hint in ["simulate", "forecast", "scenario"]
            ):
                overlap += 2
            scored.append((overlap, tool))

        scored.sort(key=lambda item: item[0], reverse=True)
        best_score, chosen = scored[0]
        if tool_choice == "auto" and best_score <= 0:
            return None

    fn = chosen.get("function", {})
    function_name = fn.get("name", "janus_tool")
    properties = ((fn.get("parameters", {}) or {}).get("properties", {}) or {})
    arguments = {}
    ticker = _extract_ticker_symbol(user_input)

    for key in properties.keys():
        lowered = key.lower()
        if any(token in lowered for token in ["query", "question", "prompt", "input", "task", "request"]):
            arguments[key] = user_input
        elif any(token in lowered for token in ["domain", "topic"]):
            arguments[key] = route.get("domain", "general")
        elif any(token in lowered for token in ["intent", "goal", "reason"]):
            arguments[key] = route.get("intent", user_input)
        elif any(token in lowered for token in ["ticker", "symbol"]):
            arguments[key] = ticker or user_input
        elif "company" in lowered:
            arguments[key] = user_input

    if not arguments and properties:
        first_key = next(iter(properties.keys()))
        arguments[first_key] = user_input

    return {
        "id": f"call_{uuid.uuid4().hex}",
        "type": "function",
        "function": {
            "name": function_name,
            "arguments": json.dumps(arguments, ensure_ascii=False),
        },
    }


def _split_stream_text(text: str, target_size: int = 80) -> list[str]:
    words = (text or "").split()
    if not words:
        return [""]
    chunks = []
    current = []
    current_len = 0
    for word in words:
        if current and current_len + len(word) + 1 > target_size:
            chunks.append(" ".join(current))
            current = [word]
            current_len = len(word)
        else:
            current.append(word)
            current_len += len(word) + (1 if current_len else 0)
    if current:
        chunks.append(" ".join(current))
    return chunks


def _sse_event(payload: dict, event: str | None = None) -> str:
    prefix = f"event: {event}\n" if event else ""
    return prefix + f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


async def _execute_provider_tool_call(
    app: FastAPI, tool_call: dict, user_input: str, route: dict
) -> dict:
    function = tool_call.get("function", {}) or {}
    name = function.get("name", "")
    try:
        arguments = json.loads(function.get("arguments", "{}"))
    except Exception:
        arguments = {}

    query = (
        arguments.get("query")
        or arguments.get("question")
        or arguments.get("input")
        or arguments.get("task")
        or user_input
    )

    def _run_sync() -> dict:
        if name in {"get_stock_quote", "get_market_quote", "ticker_intelligence"}:
            from app.domain_packs.finance.market_data import get_company_overview, get_quote, search_symbol

            symbol = (
                arguments.get("ticker")
                or arguments.get("symbol")
                or _extract_ticker_symbol(query)
            )
            if not symbol and query:
                results = search_symbol(query)
                symbol = (results[0] or {}).get("1. symbol") if results else None
            symbol = (symbol or "").upper()
            quote = get_quote(symbol) if symbol else {}
            overview = get_company_overview(symbol) if symbol else {}
            return {
                "tool": name,
                "symbol": symbol,
                "quote": quote,
                "overview": {
                    "name": overview.get("Name"),
                    "sector": overview.get("Sector"),
                    "industry": overview.get("Industry"),
                    "market_cap": overview.get("MarketCapitalization"),
                    "pe_ratio": overview.get("PERatio"),
                    "analyst_target": overview.get("AnalystTargetPrice"),
                },
            }

        if name in {"search_market_symbols", "search_symbol"}:
            from app.domain_packs.finance.market_data import search_symbol

            results = search_symbol(query)
            return {
                "tool": name,
                "query": query,
                "results": [
                    {
                        "symbol": item.get("1. symbol"),
                        "name": item.get("2. name"),
                        "region": item.get("4. region"),
                        "currency": item.get("8. currency"),
                    }
                    for item in results[:8]
                ],
            }

        if name in {"search_memory", "memory_search", "find_similar_cases"}:
            memory_manager = getattr(app.state, "memory_manager", None)
            limit = int(arguments.get("limit", 5) or 5)
            results = (
                memory_manager.find_similar(query, top_k=limit)
                if memory_manager and hasattr(memory_manager, "find_similar")
                else []
            )
            return {"tool": name, "query": query, "results": results}

        if name in {"get_company_news", "search_finance_news", "get_top_headlines"}:
            from app.domain_packs.finance.news import (
                get_company_news,
                get_top_headlines,
                search_news,
            )

            limit = int(arguments.get("limit", 5) or 5)
            symbol = arguments.get("ticker") or arguments.get("symbol") or _extract_ticker_symbol(query)
            company = arguments.get("company") or query

            if name == "get_top_headlines":
                category = arguments.get("category") or "business"
                articles = get_top_headlines(category=category, page_size=limit)
                return {
                    "tool": name,
                    "category": category,
                    "articles": articles[:limit],
                }

            if name == "get_company_news" and symbol:
                articles = get_company_news(company, days_back=7, symbol=symbol)
            else:
                articles = search_news(query, page_size=limit)
            return {
                "tool": name,
                "query": query,
                "symbol": symbol,
                "articles": articles[:limit],
            }

        if name in {"deep_web_research", "public_web_research", "web_research"}:
            from app.services.external_sources import deep_web_research_bundle

            limit = int(arguments.get("limit", 4) or 4)
            follow_links = int(arguments.get("follow_links", 1) or 1)
            bundle = deep_web_research_bundle(
                query, max_results=limit, follow_links=follow_links
            )
            results = bundle.get("results", [])
            synthesis = bundle.get("synthesis", {})
            return {
                "tool": name,
                "query": query,
                "summary": synthesis.get("summary", ""),
                "key_points": synthesis.get("key_points", []),
                "avg_credibility": synthesis.get("avg_credibility", 0.0),
                "top_sources": synthesis.get("top_sources", []),
                "query_variants": bundle.get("query_variants", []),
                "results": results[:limit],
            }

        if name in {"market_web_brief", "company_web_brief", "market_research_brief"}:
            from app.domain_packs.finance.market_data import get_company_overview, get_quote
            from app.domain_packs.finance.news import get_company_news
            from app.services.external_sources import deep_web_research_bundle

            symbol = (
                arguments.get("ticker")
                or arguments.get("symbol")
                or _extract_ticker_symbol(query)
            )
            symbol = (symbol or "").upper()
            company = arguments.get("company") or query
            quote = get_quote(symbol) if symbol else {}
            overview = get_company_overview(symbol) if symbol else {}
            news = get_company_news(company, days_back=7, symbol=symbol)[:5] if symbol else []
            bundle = deep_web_research_bundle(query, max_results=4, follow_links=1)
            web_results = bundle.get("results", [])
            synthesis = bundle.get("synthesis", {})
            top_sources = [
                {
                    "title": item.get("title"),
                    "url": item.get("url"),
                    "credibility_score": item.get("credibility_score", 0.0),
                    "credibility_reason": item.get("credibility_reason", "unknown"),
                }
                for item in web_results[:4]
            ]
            return {
                "tool": name,
                "symbol": symbol,
                "company": company,
                "quote": quote,
                "overview": {
                    "name": overview.get("Name"),
                    "sector": overview.get("Sector"),
                    "industry": overview.get("Industry"),
                    "market_cap": overview.get("MarketCapitalization"),
                    "pe_ratio": overview.get("PERatio"),
                    "analyst_target": overview.get("AnalystTargetPrice"),
                },
                "news": news,
                "web_results": web_results,
                "summary": synthesis.get("summary", ""),
                "key_points": synthesis.get("key_points", []),
                "avg_credibility": synthesis.get("avg_credibility", 0.0),
                "query_variants": bundle.get("query_variants", []),
                "top_sources": top_sources,
            }

        if name in {"analyze_finance_text", "finance_text_analysis"}:
            from app.domain_packs.finance.entity_resolver import extract_entities
            from app.domain_packs.finance.event_analyzer import analyze_event_impact, detect_event_type
            from app.domain_packs.finance.rumor_detector import detect_rumor_indicators
            from app.domain_packs.finance.scam_detector import detect_scam_indicators
            from app.domain_packs.finance.source_checker import aggregate_source_scores
            from app.domain_packs.finance.stance_detector import (
                analyze_price_action_language,
                detect_stance,
            )
            from app.domain_packs.finance.ticker_resolver import extract_tickers

            text = arguments.get("text") or query
            sources = arguments.get("sources") or []
            tickers = extract_tickers(text)
            entities = extract_entities(text)
            stance = detect_stance(text)
            price_action = analyze_price_action_language(text)
            scam = detect_scam_indicators(text)
            rumor = detect_rumor_indicators(text)
            events = detect_event_type(text)
            event_impact = analyze_event_impact(text, events)
            source_assessment = aggregate_source_scores(sources) if sources else None
            return {
                "tool": name,
                "tickers": tickers,
                "entities": [e for e in entities if e.get("confidence", 0) >= 0.7],
                "stance": stance,
                "price_action": price_action,
                "scam_detection": scam,
                "rumor_detection": rumor,
                "event_impact": event_impact,
                "source_assessment": source_assessment,
            }

        if name in {"search_knowledge", "knowledge_search"}:
            from app.memory import knowledge_store

            limit = int(arguments.get("limit", 5) or 5)
            domain = arguments.get("domain") or route.get("domain", "general")
            results = knowledge_store.search(query, domain=domain, top_k=limit)
            return {"tool": name, "query": query, "domain": domain, "results": results}

        if name in {"classify_domain", "domain_classify"}:
            domain_classifier = getattr(app.state, "domain_classifier", None)
            result = domain_classifier.classify(query) if domain_classifier else None
            top_domains = (
                domain_classifier.get_top_domains(query, top_n=3)
                if domain_classifier and hasattr(domain_classifier, "get_top_domains")
                else []
            )
            return {
                "tool": name,
                "query": query,
                "domain": result.domain.value if result else "general",
                "confidence": result.confidence if result else 0.5,
                "keywords_found": result.keywords_found if result else [],
                "top_domains": [
                    {"domain": domain.value, "confidence": confidence}
                    for domain, confidence in top_domains
                ],
            }

        if name in {"run_simulation", "simulate_scenario"}:
            from app.services.simulation_engine import simulation_engine

            simulation = simulation_engine.run_simulation(
                query,
                context={
                    "provider_tool": True,
                    "route": route,
                    "tool_call_id": tool_call.get("id"),
                },
            )
            synthesis = simulation.get("synthesis", {})
            return {
                "tool": name,
                "simulation_id": simulation.get("simulation_id"),
                "most_likely": synthesis.get("most_likely"),
                "scenarios": synthesis.get("scenarios", [])[:3],
                "confidence": synthesis.get("confidence", 0.0),
            }

        if name in {"chat_with_simulation", "simulation_followup"}:
            from app.services.simulation_engine import simulation_engine

            sim_id = arguments.get("simulation_id") or arguments.get("sim_id")
            message = arguments.get("message") or arguments.get("question") or query
            response = simulation_engine.chat_with_simulation(sim_id, message) if sim_id else {"error": "Missing simulation_id"}
            return {"tool": name, **response}

        if name in {"get_watchlist_status", "watchlist_status"}:
            daemon = _services.get("daemon")
            results = (
                daemon.market_watcher.get_watchlist_status()
                if daemon and hasattr(daemon, "market_watcher")
                else []
            )
            return {"tool": name, "results": results}

        if name in {"get_domain_report", "domain_report"}:
            domain_classifier = getattr(app.state, "domain_classifier", None)
            memory_manager = getattr(app.state, "memory_manager", None)
            classification = domain_classifier.classify(query) if domain_classifier else None
            domain = arguments.get("domain") or (classification.domain.value if classification else route.get("domain", "general"))
            domain_stats = (
                memory_manager.get_domain_stats().get(domain, {})
                if memory_manager and hasattr(memory_manager, "get_domain_stats")
                else {}
            )
            frequent_patterns = (
                [p for p in memory_manager.get_frequent_patterns(min_freq=2) if p.get("term")]
                if memory_manager and hasattr(memory_manager, "get_frequent_patterns")
                else []
            )
            return {
                "tool": name,
                "domain": domain,
                "classification": {
                    "domain": classification.domain.value if classification else domain,
                    "confidence": classification.confidence if classification else 0.5,
                    "keywords_found": classification.keywords_found if classification else [],
                },
                "domain_stats": domain_stats,
                "frequent_patterns": frequent_patterns[:10],
            }

        raise ValueError(f"Unsupported Janus tool: {name}")

    return await asyncio.to_thread(_run_sync)


def _summarize_provider_tool_execution(execution: dict, user_input: str) -> str:
    """Fallback summarizer if the main reasoning model fails."""
    tool = execution.get("tool")
    
    # ── ZeroTrust Guardian & MMSA Fusion ────────────────────────
    if execution.get("guardian_score") is not None or "dissonance_score" in execution:
        risk = execution.get("guardian_score") or execution.get("deception_probability", 0) * 100
        action = execution.get("safe_action", "Proceed with extreme caution.")
        return (
            f"Janus completed a Multimodal Dissonance scan. "
            f"Risk Index: {risk:.1f}%. "
            f"Forensic Conclusion: {execution.get('reason', 'Evidence synthesis complete.')} "
            f"Recommended Safe Action: {action}"
        )

    if tool in {"get_stock_quote", "get_market_quote", "ticker_intelligence"}:
        symbol = execution.get("symbol") or "the requested company"
        quote = execution.get("quote", {})
        overview = execution.get("overview", {})
        price = quote.get("05. price")
        change_pct = quote.get("10. change percent")
        market_cap = overview.get("market_cap")
        pe_ratio = overview.get("pe_ratio")
        target = overview.get("analyst_target")
        parts = [f"Janus fetched market data for {symbol}."]
        if price is not None:
            parts.append(f"Price: {price}.")
        if change_pct not in (None, ""):
            parts.append(f"Change percent: {change_pct}.")
        if market_cap:
            parts.append(f"Market cap: {market_cap}.")
        if pe_ratio:
            parts.append(f"PE ratio: {pe_ratio}.")
        if target:
            parts.append(f"Analyst target: {target}.")
        parts.append("Use this as grounding, not as standalone investment advice.")
        return " ".join(parts)

    if tool in {"search_market_symbols", "search_symbol"}:
        results = execution.get("results", [])
        if not results:
            return "Janus could not find a market symbol for that query."
        top = results[0]
        return (
            f"Janus found {len(results)} matching symbols. "
            f"Top match: {top.get('symbol')} for {top.get('name')} in {top.get('region')}."
        )

    if tool in {"get_company_news", "search_finance_news", "get_top_headlines"}:
        articles = execution.get("articles", [])
        if not articles:
            return "Janus found no relevant finance news articles for that request."
        titles = [article.get("title", "") for article in articles[:3] if article.get("title")]
        topic = execution.get("symbol") or execution.get("query") or execution.get("category") or "the request"
        return (
            f"Janus gathered {len(articles)} relevant finance news items for {topic}. "
            f"Top headlines: {'; '.join(titles)}."
        )

    if tool in {"news_market_web_brief", "research_sweep", "intel_sweep"}:
        top = (execution.get("top_sources") or [{}])[0]
        points = execution.get("key_points") or []
        point_text = " ".join(p.get("point", "") for p in points[:2])
        return (
            f"Janus synthesized a multimodal brief. "
            f"Top Source: {top.get('domain', 'primary index')}. "
            f"Key Findings: {point_text[:320] if point_text else 'Synthesis awaiting deeper model reasoning.'}"
        )

    if tool in {"market_web_brief", "company_web_brief", "market_research_brief"}:
        symbol = execution.get("symbol") or execution.get("company") or "the index"
        parts = [f"Janus generated a market intelligence brief for {symbol}."]
        if execution.get("avg_credibility"):
            parts.append(f"Source credibility: {execution.get('avg_credibility'):.2f}.")
        return " ".join(parts)

    if tool in {"analyze_finance_text", "finance_text_analysis"}:
        stance = (execution.get("stance") or {}).get("stance", "neutral")
        scam_score = (execution.get("scam_detection") or {}).get("scam_score", 0)
        rumor_score = (execution.get("rumor_detection") or {}).get("rumor_score", 0)
        events = (execution.get("event_impact") or {}).get("summary") or "No major event impact detected."
        return (
            f"Janus analyzed the finance text. Stance: {stance}. "
            f"Scam score: {scam_score}. Rumor score: {rumor_score}. {events}"
        )

    if tool in {"search_memory", "memory_search", "find_similar_cases"}:
        results = execution.get("results", [])
        if not results:
            return "Janus found no closely related prior cases in memory."
        top = results[0]
        return (
            f"Janus found {len(results)} similar past cases. "
            f"Closest match: {top.get('query')} with similarity {top.get('score')}."
        )

    if tool in {"search_knowledge", "knowledge_search"}:
        results = execution.get("results", [])
        if not results:
            return "Janus found no matching knowledge entries for that query."
        top = results[0]
        headline = top.get("title") or top.get("topic") or "knowledge entry"
        return (
            f"Janus found {len(results)} matching knowledge entries. "
            f"Top result: {headline}."
        )

    if tool in {"classify_domain", "domain_classify"}:
        return (
            f"Janus classified this query as {execution.get('domain', 'general')} "
            f"with confidence {execution.get('confidence', 0.0)}."
        )

    if tool in {"run_simulation", "simulate_scenario"}:
        scenarios = execution.get("scenarios", [])
        return (
            f"Janus ran simulation {execution.get('simulation_id')}. "
            f"Most likely outcome: {execution.get('most_likely', 'unknown')}. "
            f"Generated {len(scenarios)} scenarios."
        )

    if tool in {"chat_with_simulation", "simulation_followup"}:
        response = execution.get("response") or execution.get("error") or "No simulation follow-up response."
        return f"Janus consulted the saved simulation. {response}"

    if tool in {"get_watchlist_status", "watchlist_status"}:
        results = execution.get("results", [])
        return f"Janus returned status for {len(results)} watchlist instruments."

    if tool in {"get_domain_report", "domain_report"}:
        domain = execution.get("domain", "general")
        count = (execution.get("domain_stats") or {}).get("count", 0)
        patterns = execution.get("frequent_patterns", [])
        return (
            f"Janus built a domain report for {domain}. "
            f"Known cases in that domain: {count}. "
            f"Tracked patterns: {len(patterns)}."
        )

    return f"Janus successfully executed the {tool} routine for: {user_input}."


def _reason_over_tool_execution(user_input: str, execution: dict) -> str:
    """Expert reasoning layer over tool outputs."""
    fallback = _summarize_provider_tool_execution(execution, user_input)
    
    # Ensure fallback is never empty even if the logic above fails
    if not fallback or len(fallback.strip()) < 5:
        fallback = f"Janus has processed the following signal: {user_input}. Analysis complete."

    try:
        from app.agents._model import call_model

        messages = [
            {
                "role": "system",
                "content": "You are Janus, the Multimodal Intelligence Sentinel. Summarize the tool execution results naturally."
            },
            {
                "role": "user",
                "content": (
                    f"User request:\n{user_input}\n\n"
                    f"Executed tool result:\n{json.dumps(execution, ensure_ascii=False, indent=2)}\n\n"
                    "Provide a high-fidelity final answer."
                ),
            },
        ]
        result = call_model(messages)
        cleaned = (result or "").strip()
        # Double-check cleaned to avoid protocol errors
        if not cleaned or len(cleaned) < 10:
             return fallback
        return cleaned
    except Exception:
        return fallback


def _stable_hash_int(text: str) -> int:
    import hashlib

    digest = hashlib.sha256(text.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big", signed=False)


def _embed_text(text: str, dimensions: int = 256) -> list[float]:
    import re

    dim = max(16, min(int(dimensions or 256), 2048))
    vector = [0.0] * dim
    tokens = re.findall(r"[a-z0-9_]+", (text or "").lower())
    if not tokens:
        return vector

    for token in tokens:
        slot = _stable_hash_int(token) % dim
        weight = 1.0 + min(len(token), 12) / 12.0
        vector[slot] += weight

    norm = math.sqrt(sum(value * value for value in vector)) or 1.0
    return [round(value / norm, 6) for value in vector]


def _build_chat_completion_response(
    model: str, case_response: dict, tool_call: dict | None = None
) -> dict:
    content = case_response.get("final_answer", "")
    prompt_tokens = _approx_tokens(case_response.get("user_input", ""))
    completion_tokens = _approx_tokens(content)
    if tool_call:
        assistant_message = {
            "role": "assistant",
            "content": None,
            "tool_calls": [tool_call],
        }
        finish_reason = "tool_calls"
    else:
        assistant_message = {
            "role": "assistant",
            "content": content,
        }
        finish_reason = "stop"
    return {
        "id": f"chatcmpl-{uuid.uuid4().hex}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": assistant_message,
                "finish_reason": finish_reason,
            }
        ],
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        },
        "janus": {
            "case_id": case_response.get("case_id"),
            "route": case_response.get("route", {}),
            "trace_id": case_response.get("trace_id"),
            "trace_score": case_response.get("trace_score"),
        },
    }


def _build_responses_api_response(
    model: str, case_response: dict, tool_call: dict | None = None
) -> dict:
    content = case_response.get("final_answer", "")
    prompt_tokens = _approx_tokens(case_response.get("user_input", ""))
    completion_tokens = _approx_tokens(content)
    if tool_call:
        output = [
            {
                "id": f"fc_{uuid.uuid4().hex}",
                "type": "function_call",
                "call_id": tool_call.get("id"),
                "name": tool_call.get("function", {}).get("name"),
                "arguments": tool_call.get("function", {}).get("arguments", "{}"),
            }
        ]
    else:
        output = [
            {
                "id": f"msg_{uuid.uuid4().hex}",
                "type": "message",
                "role": "assistant",
                "content": [{"type": "output_text", "text": content}],
            }
        ]
    return {
        "id": f"resp_{uuid.uuid4().hex}",
        "object": "response",
        "created_at": int(time.time()),
        "model": model,
        "output": output,
        "usage": {
            "input_tokens": prompt_tokens,
            "output_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        },
        "janus": {
            "case_id": case_response.get("case_id"),
            "route": case_response.get("route", {}),
            "trace_id": case_response.get("trace_id"),
        },
    }


async def _stream_chat_completion_response(
    model: str, case_response: dict, tool_call: dict | None = None
):
    stream_id = f"chatcmpl-{uuid.uuid4().hex}"
    created = int(time.time())
    yield _sse_event(
        {
            "id": stream_id,
            "object": "chat.completion.chunk",
            "created": created,
            "model": model,
            "choices": [{"index": 0, "delta": {"role": "assistant"}, "finish_reason": None}],
        }
    )

    if tool_call:
        yield _sse_event(
            {
                "id": stream_id,
                "object": "chat.completion.chunk",
                "created": created,
                "model": model,
                "choices": [
                    {
                        "index": 0,
                        "delta": {"tool_calls": [{**tool_call, "index": 0}]},
                        "finish_reason": None,
                    }
                ],
            }
        )
        yield _sse_event(
            {
                "id": stream_id,
                "object": "chat.completion.chunk",
                "created": created,
                "model": model,
                "choices": [{"index": 0, "delta": {}, "finish_reason": "tool_calls"}],
            }
        )
        yield "data: [DONE]\n\n"
        return

    for chunk in _split_stream_text(case_response.get("final_answer", "")):
        yield _sse_event(
            {
                "id": stream_id,
                "object": "chat.completion.chunk",
                "created": created,
                "model": model,
                "choices": [
                    {"index": 0, "delta": {"content": chunk}, "finish_reason": None}
                ],
            }
        )
    yield _sse_event(
        {
            "id": stream_id,
            "object": "chat.completion.chunk",
            "created": created,
            "model": model,
            "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
        }
    )
    yield "data: [DONE]\n\n"


async def _stream_responses_api_response(
    model: str, case_response: dict, tool_call: dict | None = None
):
    response_id = f"resp_{uuid.uuid4().hex}"
    created = int(time.time())
    yield _sse_event(
        {"id": response_id, "object": "response", "created_at": created, "model": model},
        event="response.created",
    )

    if tool_call:
        yield _sse_event(
            {
                "response_id": response_id,
                "item": {
                    "id": f"fc_{uuid.uuid4().hex}",
                    "type": "function_call",
                    "call_id": tool_call.get("id"),
                    "name": tool_call.get("function", {}).get("name"),
                    "arguments": tool_call.get("function", {}).get("arguments", "{}"),
                },
            },
            event="response.output_item.added",
        )
    else:
        for chunk in _split_stream_text(case_response.get("final_answer", "")):
            yield _sse_event(
                {"response_id": response_id, "delta": chunk},
                event="response.output_text.delta",
            )

    yield _sse_event(
        {
            "id": response_id,
            "object": "response",
            "created_at": created,
            "model": model,
            "status": "completed",
        },
        event="response.completed",
    )


def _frontend_server_path() -> str | None:
    import pathlib

    frontend_dir = os.getenv("NEXT_STANDALONE_DIR", "").strip()
    if not frontend_dir:
        return None

    server_js = pathlib.Path(frontend_dir) / "server.js"
    if not server_js.exists():
        logger.warning("Bundled frontend missing: %s", server_js)
        return None

    return str(server_js)


async def _wait_for_frontend(port: str, attempts: int = 40, delay: float = 0.5) -> bool:
    import httpx

    url = f"http://127.0.0.1:{port}/"
    async with httpx.AsyncClient(timeout=2.0) as client:
        for _ in range(attempts):
            try:
                response = await client.get(url)
                if response.status_code < 500:
                    return True
            except Exception:
                pass
            await asyncio.sleep(delay)
    return False


async def _start_frontend_server():
    server_js = _frontend_server_path()
    if not server_js or _services.get("frontend_process"):
        return

    env = os.environ.copy()
    port = os.getenv("NEXT_INTERNAL_PORT", "3000")
    env["PORT"] = port
    env["HOSTNAME"] = "127.0.0.1"
    env.setdefault("NODE_ENV", "production")

    process = subprocess.Popen(
        [os.getenv("NODE_BIN", "node"), server_js],
        cwd=os.path.dirname(server_js),
        env=env,
    )
    _services["frontend_process"] = process

    if await _wait_for_frontend(port):
        logger.info("Bundled frontend started on internal port %s", port)
    else:
        logger.warning("Bundled frontend did not become ready on port %s", port)


async def _proxy_frontend_request(request, path: str = ""):
    import httpx
    from fastapi.responses import JSONResponse, Response

    if _frontend_server_path() is None:
        return JSONResponse(
            status_code=404, content={"detail": "Frontend not configured"}
        )

    target = f"http://127.0.0.1:{os.getenv('NEXT_INTERNAL_PORT', '3000')}/"
    if path:
        target += path
    if request.url.query:
        target += f"?{request.url.query}"

    filtered_request_headers = {
        key: value
        for key, value in request.headers.items()
        if key.lower() not in {"host", *_HOP_BY_HOP_HEADERS}
    }
    body = await request.body()

    try:
        async with httpx.AsyncClient(follow_redirects=False, timeout=60.0) as client:
            proxied = await client.request(
                request.method,
                target,
                content=body,
                headers=filtered_request_headers,
            )
    except httpx.HTTPError as e:
        logger.error("Frontend proxy failed: %s", e)
        return JSONResponse(
            status_code=502, content={"detail": "Bundled frontend unavailable"}
        )

    response_headers = {
        key: value
        for key, value in proxied.headers.items()
        if key.lower() not in _HOP_BY_HOP_HEADERS
    }
    return Response(
        content=proxied.content,
        status_code=proxied.status_code,
        headers=response_headers,
        media_type=proxied.headers.get("content-type"),
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

    # ── CORS — same-origin by default, configurable for external UIs ─────
    raw_origins = os.getenv("ALLOWED_ORIGINS", "")
    allowed_origins = [o.strip() for o in raw_origins.split(",") if o.strip()]

    # Always include HF Space patterns + localhost for dev
    hf_space_id = os.getenv("SPACE_ID", "")
    if hf_space_id:
        # HF Space URLs follow pattern: https://{owner}-{space-name}.hf.space
        owner = hf_space_id.split("/")[0] if "/" in hf_space_id else hf_space_id
        allowed_origins.extend(
            [
                f"https://{owner.lower()}-*.hf.space",  # wildcard for all spaces from same owner
                f"https://huggingface.co",
            ]
        )

    # Always allow localhost for local dev/testing
    allowed_origins.extend(
        [
            "http://localhost:3000",
            "http://localhost:3001",
            "http://127.0.0.1:3000",
        ]
    )

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
    from app.routes.analyze import router as analyze_router
    from app.routes.history import router as history_router
    from app.routes.feedback import router as feedback_router
    from app.routes.websocket import router as websocket_router

    app.include_router(finance_router)
    app.include_router(analyze_router)
    app.include_router(history_router)
    app.include_router(feedback_router)
    app.include_router(websocket_router)

    # ── Health (supports HEAD for HF health checker) ──────────────────────
    @app.api_route("/health", methods=["GET", "HEAD"])
    async def health(request=None):
        from fastapi import Request

        graph_ok = getattr(getattr(app, "state", None), "graph", None) is not None
        return {
            "status": "ok" if graph_ok else "degraded",
            "graph": "ready" if graph_ok else "failed",
            "space": os.getenv("SPACE_ID", "local"),
            "version": "1.0.0",
            "error_detail": getattr(getattr(app, "state", None), "graph_error", "none"),
        }

    @app.get("/health/graph_error")
    async def health_graph_error():
        from app.graph import graph_status
        return graph_status()

    @app.get("/health/deep")
    async def health_deep():
        graph_ok = getattr(getattr(app, "state", None), "graph", None) is not None
        return {
            "status": "ok" if graph_ok else "degraded",
            "space": os.getenv("SPACE_ID", "local"),
            "features": {
                "simulation": os.getenv("SIMULATION_ENABLED", "true") == "true",
                "sentinel": os.getenv("SENTINEL_ENABLED", "true") == "true",
                "learning": os.getenv("LEARNING_ENABLED", "false") == "true",
                "adaptive": os.getenv("ADAPTIVE_INTELLIGENCE_ENABLED", "false")
                == "true",
                "training": os.getenv("CONTINUOUS_TRAINING_ENABLED", "false") == "true",
                "curiosity": os.getenv("CURIOSITY_ENGINE_ENABLED", "false") == "true",
            },
            "data_sources": {
                "yfinance": True,  # always available, no key needed
                "alphavantage": bool(os.getenv("ALPHAVANTAGE_API_KEY")),
                "finnhub": bool(os.getenv("FINNHUB_API_KEY")),
                "fmp": bool(os.getenv("FMP_API_KEY")),
                "eodhd": bool(os.getenv("EODHD_API_KEY")),
                "tavily": bool(os.getenv("TAVILY_API_KEY")),
                "newsapi": bool(os.getenv("NEWS_API_KEY") or os.getenv("NEWSAPI_KEY")),
            },
            "persistence": {
                "hf_store": bool(os.getenv("HF_STORE_REPO")),
                "ephemeral": os.getenv("SPACE_ID", "") != ""
                and not os.getenv("HF_STORE_REPO"),
            },
        }

    @app.post("/run")
    async def run_query(body: dict, background_tasks=None):
        from fastapi.responses import JSONResponse

        try:
            return await _execute_case_request(app, body)
        except HTTPException as e:
            return JSONResponse(status_code=e.status_code, content={"detail": e.detail})
        except Exception as e:
            logger.error("Pipeline error: %s", e)
            return JSONResponse(status_code=500, content={"detail": str(e)})

    @app.get("/v1/models")
    async def provider_models(request: Request):
        _check_provider_auth(request)
        return {"object": "list", "data": _JANUS_PROVIDER_MODELS}

    @app.get("/v1/models/{model_id}")
    async def provider_model_detail(model_id: str, request: Request):
        from fastapi.responses import JSONResponse

        _check_provider_auth(request)
        model = next((item for item in _JANUS_PROVIDER_MODELS if item["id"] == model_id), None)
        if not model:
            return JSONResponse(status_code=404, content={"error": {"message": "Model not found", "type": "invalid_request_error"}})
        return model

    @app.post("/v1/embeddings")
    async def provider_embeddings(request: Request, body: dict):
        from fastapi.responses import JSONResponse

        _check_provider_auth(request)
        model = body.get("model", "janus-embed")
        input_payload = body.get("input", "")
        dimensions = int(body.get("dimensions", 256) or 256)

        if isinstance(input_payload, str):
            texts = [input_payload]
        elif isinstance(input_payload, list):
            texts = [
                _message_content_to_text(item).strip() if not isinstance(item, str) else item
                for item in input_payload
            ]
        else:
            texts = [_message_content_to_text(input_payload).strip()]

        texts = [text for text in texts if str(text).strip()]
        if not texts:
            return JSONResponse(
                status_code=400,
                content={"error": {"message": "Missing input", "type": "invalid_request_error"}},
            )

        data = []
        total_tokens = 0
        for index, text in enumerate(texts):
            embedding = _embed_text(text, dimensions=dimensions)
            total_tokens += _approx_tokens(text)
            data.append(
                {
                    "object": "embedding",
                    "index": index,
                    "embedding": embedding,
                }
            )

        return {
            "object": "list",
            "data": data,
            "model": model,
            "usage": {"prompt_tokens": total_tokens, "total_tokens": total_tokens},
        }

    @app.post("/v1/chat/completions")
    async def provider_chat_completions(request: Request, body: dict):
        from fastapi.responses import JSONResponse, StreamingResponse

        _check_provider_auth(request)
        model = body.get("model", "janus-chat")

        messages = body.get("messages") or []
        user_input = _extract_user_input_from_messages(messages)
        if not user_input:
            return JSONResponse(
                status_code=400,
                content={"error": {"message": "Missing messages/user content", "type": "invalid_request_error"}},
            )

        try:
            case_response = await _execute_case_request(
                app,
                {
                    "user_input": user_input,
                    "context": _provider_context_from_body(body),
                },
            )
            tool_call = _select_provider_tool_call(
                user_input,
                case_response.get("route", {}),
                body.get("tools") or [],
                body.get("tool_choice", "auto"),
            )
            if body.get("janus_execute_tools") and tool_call:
                execution = await _execute_provider_tool_call(
                    app, tool_call, user_input, case_response.get("route", {})
                )
                if body.get("janus_reason_over_tools", True):
                    tool_summary = await asyncio.to_thread(
                        _reason_over_tool_execution, user_input, execution
                    )
                else:
                    tool_summary = _summarize_provider_tool_execution(execution, user_input)
                executed_case_response = {
                    **case_response,
                    "final": {
                        **case_response.get("final", {}),
                        "response": tool_summary,
                    },
                    "final_answer": tool_summary,
                }
                if body.get("stream"):
                    return StreamingResponse(
                        _stream_chat_completion_response(model, executed_case_response),
                        media_type="text/event-stream",
                    )
                response = _build_chat_completion_response(model, executed_case_response)
                response.setdefault("janus", {})["executed_tools"] = [execution]
                return response
            if body.get("stream"):
                return StreamingResponse(
                    _stream_chat_completion_response(model, case_response, tool_call),
                    media_type="text/event-stream",
                )
            return _build_chat_completion_response(model, case_response, tool_call)
        except HTTPException as e:
            return JSONResponse(status_code=e.status_code, content={"error": {"message": e.detail, "type": "invalid_request_error"}})
        except Exception as e:
            logger.error("Provider chat completion error: %s", e)
            return JSONResponse(status_code=500, content={"error": {"message": str(e), "type": "server_error"}})

    @app.post("/v1/responses")
    async def provider_responses(request: Request, body: dict):
        from fastapi.responses import JSONResponse, StreamingResponse

        _check_provider_auth(request)
        model = body.get("model", "janus-chat")

        input_payload = body.get("input", "")
        if isinstance(input_payload, str):
            user_input = input_payload.strip()
        elif isinstance(input_payload, list):
            user_input = _extract_user_input_from_messages(input_payload)
        else:
            user_input = _message_content_to_text(input_payload).strip()

        if not user_input:
            return JSONResponse(
                status_code=400,
                content={"error": {"message": "Missing input", "type": "invalid_request_error"}},
            )

        try:
            case_response = await _execute_case_request(
                app,
                {
                    "user_input": user_input,
                    "context": {
                        **_provider_context_from_body({"model": model, "messages": input_payload if isinstance(input_payload, list) else []}),
                        "responses_api": {"instructions": body.get("instructions", "")},
                    },
                },
            )
            tool_call = _select_provider_tool_call(
                user_input,
                case_response.get("route", {}),
                body.get("tools") or [],
                body.get("tool_choice", "auto"),
            )
            if body.get("janus_execute_tools") and tool_call:
                execution = await _execute_provider_tool_call(
                    app, tool_call, user_input, case_response.get("route", {})
                )
                if body.get("janus_reason_over_tools", True):
                    tool_summary = await asyncio.to_thread(
                        _reason_over_tool_execution, user_input, execution
                    )
                else:
                    tool_summary = _summarize_provider_tool_execution(execution, user_input)
                executed_case_response = {
                    **case_response,
                    "final": {
                        **case_response.get("final", {}),
                        "response": tool_summary,
                    },
                    "final_answer": tool_summary,
                }
                if body.get("stream"):
                    return StreamingResponse(
                        _stream_responses_api_response(model, executed_case_response),
                        media_type="text/event-stream",
                    )
                response = _build_responses_api_response(model, executed_case_response)
                response.setdefault("janus", {})["executed_tools"] = [execution]
                return response
            if body.get("stream"):
                return StreamingResponse(
                    _stream_responses_api_response(model, case_response, tool_call),
                    media_type="text/event-stream",
                )
            return _build_responses_api_response(model, case_response, tool_call)
        except HTTPException as e:
            return JSONResponse(status_code=e.status_code, content={"error": {"message": e.detail, "type": "invalid_request_error"}})
        except Exception as e:
            logger.error("Provider responses API error: %s", e)
            return JSONResponse(status_code=500, content={"error": {"message": str(e), "type": "server_error"}})

    @app.get("/cases")
    async def list_cases():
        from app.services.case_store import list_cases as list_saved_cases

        cases = list_saved_cases(limit=50)
        return {"cases": cases, "count": len(cases)}

    @app.get("/config/status")
    async def config_status():
        return {
            "primary_provider": os.getenv("PRIMARY_PROVIDER", "huggingface"),
            "space_id": os.getenv("SPACE_ID", "local"),
            "persistent_store": bool(os.getenv("HF_STORE_REPO")),
        }

    # ── Silence HF Space internal log-viewer poll ──────────────────────────
    @app.get("/")
    async def root(request: Request, logs: str = None):
        if _frontend_server_path() is not None:
            return await _proxy_frontend_request(request)
        return {"status": "ok", "service": "Janus"}

    # ── Daemon routes ──────────────────────────────────────────────────────
    @app.get("/daemon/status")
    async def daemon_status():
        daemon = _services.get("daemon")
        if daemon:
            from app.agents.smart_router import get_router_status
            status = daemon.get_status()
            status["router_health"] = get_router_status()
            return status
        return {"running": False, "message": "Daemon not started"}

    @app.post("/daemon/trigger")
    async def daemon_trigger():
        daemon = _services.get("daemon")
        if daemon:
            daemon._force_cycles = True
            daemon_id = getattr(daemon, "trigger_cycle", lambda: "legacy_trigger")()
            return {"status": "triggered", "id": daemon_id, "message": "Global daemon cycle forced."}
        return {"error": "Daemon not available"}

    @app.post("/daemon/analyze/dissonance")
    async def daemon_analyze_dissonance(
        file: UploadFile = File(..., description="Audio file"),
        transcript: str = Form(...),
        video: Optional[UploadFile] = File(None, description="Optional Video file for visual dissonance")
    ):
        """Analyze audio vs transcript for emotional conflict."""
        from app.services.mmsa_engine import mmsa_engine
        import tempfile
        import shutil
        from pathlib import Path

        # Save files to temp
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix) as tmp_audio:
            shutil.copyfileobj(file.file, tmp_audio)
            audio_path = tmp_audio.name

        video_path = None
        if video:
            with tempfile.NamedTemporaryFile(delete=False, suffix=Path(video.filename).suffix) as tmp_video:
                shutil.copyfileobj(video.file, tmp_video)
                video_path = tmp_video.name

        try:
            results = mmsa_engine.analyze(audio_path, transcript, video_path)
            return results
        finally:
            if os.path.exists(audio_path):
                os.remove(audio_path)
            if video_path and os.path.exists(video_path):
                os.remove(video_path)

    @app.post("/daemon/analyze/url")
    async def daemon_analyze_url(
        url: str = Form(...),
        transcript: str = Form(...)
    ):
        """Analyze a YouTube or Stream URL for emotional conflict."""
        from app.services.mmsa_engine import mmsa_engine
        return mmsa_engine.analyze_url(url, transcript)

    @app.post("/guardian/analyze/file")
    async def guardian_analyze_file(file: UploadFile = File(...)):
        """Analyze a screenshot or PDF for scam journey patterns."""
        from app.services.guardian_sensory import guardian_sensory
        import shutil
        import tempfile
        
        # Save to temp
        suffix = os.path.splitext(file.filename)[1].lower()
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            shutil.copyfileobj(file.file, tmp)
            tmp_path = tmp.name
        
        try:
            if suffix in ['.pdf']:
                return guardian_sensory.analyze_document(tmp_path)
            else:
                # Assume image for screenshot analysis
                return guardian_sensory.analyze_screenshot(tmp_path)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    @app.post("/guardian/analyze/url")
    async def guardian_analyze_url(url: str, transcript: Optional[str] = None):
        """Universal URL Probe: Fuses Phishing Heuristics with MMSA Dissonance for Video."""
        from app.services.guardian_sensory import guardian_sensory
        from app.services.mmsa_engine import mmsa_engine
        
        # 1. Base URL Forensics (LinkBrain)
        safety_report = guardian_sensory.analyze_url(url)
        
        # 2. Multimodal Dissonance (MMSA) if YouTube
        if "youtube.com" in url or "youtu.be" in url:
            mmsa_report = mmsa_engine.analyze_url(url, transcript or "Autonomous scan — no manual transcript provided.")
            if "error" not in mmsa_report:
                # Fuse reports
                safety_report["details"]["mmsa"] = mmsa_report
                safety_report["risk_score"] = float(max(safety_report["risk_score"], mmsa_report.get("deception_probability", 0)))
                safety_report["reason"] += f" | MMSA Detection: {mmsa_report.get('reliability_tier')} confidence dissonance detected."
                safety_report["safe_action"] = mmsa_report.get("safe_action", safety_report["safe_action"])
        
        return safety_report


    @app.post("/daemon/calibrate/dissonance")
    async def daemon_calibrate_dissonance():
        """Trigger threshold calibration and generate Accuracy Report."""
        from app.services.mmsa_engine import mmsa_engine
        return mmsa_engine.calibrate()

    @app.get("/daemon/alerts")
    async def daemon_alerts(limit: int = 20, min_severity: str = "low"):
        daemon = _services.get("daemon")
        if daemon:
            try:
                return daemon.signal_queue.get_alerts(
                    limit=limit, min_severity=min_severity
                )
            except Exception:
                return daemon.signal_queue.get_stats()
        return []

    @app.get("/daemon/adaptive")
    async def daemon_adaptive_status():
        adaptive = getattr(app.state, "adaptive", None)
        if adaptive:
            return adaptive.get_full_intelligence_report()
        return {"running": False, "message": "Adaptive engine not active"}

    @app.post("/daemon/adaptive/now")
    async def trigger_adaptive_now():
        adaptive = getattr(app.state, "adaptive", None)
        if adaptive and hasattr(adaptive, "run_evolution_cycle"):
            # Offload to task
            asyncio.create_task(adaptive.run_evolution_cycle())
            return {"status": "triggered", "message": "Adaptive evolution cycle started in background."}
        return {"error": "Adaptive evolution not available"}

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
    async def get_context(query: str = ""):
        daemon = _services.get("daemon")
        signals = []
        context_engine = getattr(app.state, "context_engine", None)
        if daemon:
            try:
                signals = (
                    list(daemon.signal_queue._queue)[-10:]
                    if hasattr(daemon.signal_queue, "_queue")
                    else []
                )
            except Exception:
                pass

        if query:
            return {
                "context": _build_runtime_context(app, query, None),
                "recent_signals": len(signals),
            }

        adaptive = getattr(app.state, "adaptive", None)
        memory_manager = getattr(app.state, "memory_manager", None)
        from app.services.scam_graph import scam_graph
        from app.services.guardian_interceptor import guardian_interceptor
        snapshot_query = query or getattr(context_engine, "_last_topic", "") or "system state"
        return {
            "context": "ok",
            "snapshot": _build_runtime_context(app, snapshot_query, None),
            "recent_signals": len(signals),
            "pending_thoughts": len(
                getattr(context_engine, "get_pending_thoughts", lambda: [])()
            ),
            "recent_discoveries": len(getattr(daemon, "last_curiosity_cycle", {}).get("discoveries", []))
            if daemon
            else 0,
            "memory_cases": memory_manager.total_cases()
            if memory_manager and hasattr(memory_manager, "total_cases")
            else 0,
            "memory_patterns": memory_manager.get_frequent_patterns(min_freq=2)[:5]
            if memory_manager and hasattr(memory_manager, "get_frequent_patterns")
            else [],
            "adaptive_cases": adaptive.total_cases if adaptive else 0,
            "guardian": {
                "active_interventions": len(guardian_interceptor.active_interventions),
                "graph_nodes": len(scam_graph.graph.nodes)
            }
        }

    # ── Memory routes ──────────────────────────────────────────────────────
    @app.get("/memory/stats")
    async def memory_stats():
        try:
            from app.memory import knowledge_store
            from app.services.case_store import memory_stats as get_case_memory_stats

            memory_manager = getattr(app.state, "memory_manager", None)
            stats = (
                knowledge_store.get_stats()
                if hasattr(knowledge_store, "get_stats")
                else {}
            )
            case_stats = get_case_memory_stats()
            return {
                "queries": stats.get("total_queries", 0),
                "entities": stats.get("total_entities", 0),
                "links": stats.get("total_links", 0),
                "insights": stats.get("total_links", 0),
                "domains": stats.get("domain_counts", {}),
                "total_cases": case_stats.get("total_cases", 0),
                "latest_case_id": case_stats.get("latest_case_id"),
                "disk_bytes": case_stats.get("disk_bytes", 0),
                "indexed_case_memory": memory_manager.total_cases()
                if memory_manager and hasattr(memory_manager, "total_cases")
                else 0,
                "domain_stats": memory_manager.get_domain_stats()
                if memory_manager and hasattr(memory_manager, "get_domain_stats")
                else {},
                "frequent_patterns": memory_manager.get_frequent_patterns(min_freq=2)[:10]
                if memory_manager and hasattr(memory_manager, "get_frequent_patterns")
                else [],
            }
        except Exception as e:
            return {
                "queries": 0,
                "entities": 0,
                "links": 0,
                "insights": 0,
                "domains": {},
                "total_cases": 0,
                "error": str(e),
            }

    @app.get("/memory/queries")
    async def memory_queries(limit: int = 20):
        try:
            from app.memory import knowledge_store

            return (
                knowledge_store.get_recent_queries(limit=limit)
                if hasattr(knowledge_store, "get_recent_queries")
                else []
            )
        except Exception:
            return []

    # ── Intelligence / Cache routes ────────────────────────────────────────
    @app.get("/intelligence/report")
    async def intelligence_report():
        cache = _services.get("cache")
        daemon = _services.get("daemon")
        adaptive = getattr(app.state, "adaptive", None)
        learning_engine = getattr(app.state, "learning_engine", None)
        memory_manager = getattr(app.state, "memory_manager", None)
        self_reflection = getattr(app.state, "self_reflection", None)
        tracer = getattr(app.state, "tracer", None)
        curator = getattr(app.state, "curator", None)

        from app.services.scam_graph import scam_graph
        from app.services.guardian_interceptor import guardian_interceptor
        sentinel_status = {}
        try:
            from app.routers.sentinel import engine as sentinel_engine
            sentinel_status = sentinel_engine.get_status()
        except Exception:
            sentinel_status = {}

        return {
            "status": "ok",
            "cache_stats": cache.get_stats()
            if cache and hasattr(cache, "get_stats")
            else {},
            "daemon_cycles": daemon.cycle_count if daemon else 0,
            "daemon_status": daemon.get_status() if daemon and hasattr(daemon, "get_status") else {},
            "adaptive_report": adaptive.get_full_intelligence_report()
            if adaptive and hasattr(adaptive, "get_full_intelligence_report")
            else {},
            "learning_status": learning_engine.get_status()
            if learning_engine and hasattr(learning_engine, "get_status")
            else {},
            "memory": {
                "total_cases": memory_manager.total_cases(),
                "domain_stats": memory_manager.get_domain_stats(),
                "frequent_patterns": memory_manager.get_frequent_patterns(min_freq=2)[:10],
            }
            if memory_manager and hasattr(memory_manager, "total_cases")
            else {},
            "self_reflection": {
                "dataset": self_reflection.get_dataset_stats(),
                "top_gaps": self_reflection.get_gaps()[:5],
                "top_opinions": self_reflection.get_opinions()[:5],
            }
            if self_reflection and hasattr(self_reflection, "get_dataset_stats")
            else {},
            "observation": tracer.get_stats() if tracer and hasattr(tracer, "get_stats") else {},
            "curation": curator.get_stats() if curator and hasattr(curator, "get_stats") else {},
            "sentinel": sentinel_status,
            "guardian": {
                "intervention_threshold": guardian_interceptor.intervention_threshold,
                "active_interventions": len(guardian_interceptor.active_interventions),
                "graph_nodes": len(scam_graph.graph.nodes),
                "graph_edges": len(scam_graph.graph.edges)
            },
            "space": os.getenv("SPACE_ID", "local"),
        }

    @app.get("/intelligence/domain/{domain}")
    async def intelligence_domain(domain: str):
        from app.services.case_store import list_cases as list_saved_cases

        adaptive = getattr(app.state, "adaptive", None)
        memory_manager = getattr(app.state, "memory_manager", None)
        tracer = getattr(app.state, "tracer", None)
        curator = getattr(app.state, "curator", None)

        expertise = {}
        if adaptive and hasattr(adaptive, "domain_expertise"):
            domain_expertise = adaptive.domain_expertise.get(domain)
            if domain_expertise:
                expertise = domain_expertise.get_expertise_summary()

        recent_cases = []
        for case in list_saved_cases(limit=50, full=True):
            case_domain = case.get("route", {}).get("domain", case.get("domain", "general"))
            if case_domain == domain:
                recent_cases.append(
                    {
                        "case_id": case.get("case_id"),
                        "user_input": case.get("user_input", ""),
                        "final_answer": str(case.get("final_answer") or case.get("final", {}).get("response", ""))[:240],
                        "saved_at": case.get("saved_at"),
                        "trace_score": case.get("trace_score"),
                    }
                )
            if len(recent_cases) >= 10:
                break

        return {
            "domain": domain,
            "adaptive_expertise": expertise,
            "memory_stats": memory_manager.get_domain_stats().get(domain, {})
            if memory_manager and hasattr(memory_manager, "get_domain_stats")
            else {},
            "recent_traces": tracer.get_traces(limit=10, domain=domain)
            if tracer and hasattr(tracer, "get_traces")
            else [],
            "curated_examples": curator.get_curated_examples(limit=10, domain=domain)
            if curator and hasattr(curator, "get_curated_examples")
            else [],
            "recent_cases": recent_cases,
        }

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
        saved = {}

        adaptive = getattr(app.state, "adaptive", None)
        if adaptive and hasattr(adaptive, "save"):
            adaptive.save()
            saved["adaptive"] = True

        context_engine = getattr(app.state, "context_engine", None)
        if context_engine and hasattr(context_engine, "_save"):
            context_engine._save()
            saved["context"] = True

        self_reflection = getattr(app.state, "self_reflection", None)
        if self_reflection and hasattr(self_reflection, "_save"):
            self_reflection._save()
            saved["self_reflection"] = True

        return {"status": "ok", "saved": saved}

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

            daemon = _services.get("daemon")
            context_engine = getattr(app.state, "context_engine", None)

            return {
                "opinions": self_reflection.get_opinions()[:10],
                "corrections": self_reflection.get_corrections()[:5],
                "gaps": self_reflection.get_gaps()[:5],
                "dataset": self_reflection.get_dataset_stats()
                if hasattr(self_reflection, "get_dataset_stats")
                else {},
                "self_model": getattr(self_reflection, "self_model", {}),
                "pending_thoughts": context_engine.get_pending_thoughts()[:5]
                if context_engine and hasattr(context_engine, "get_pending_thoughts")
                else [],
                "curiosity": daemon.curiosity.get_status()
                if daemon and hasattr(daemon, "curiosity")
                else {},
                "dreams": daemon.dream_processor.get_status()
                if daemon and hasattr(daemon, "dream_processor")
                else {},
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

            return {
                "corrections": self_reflection.get_corrections(topic)
                if topic
                else self_reflection.get_corrections()
            }
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

            return (
                self_reflection.get_dataset_stats()
                if hasattr(self_reflection, "get_dataset_stats")
                else {}
            )
        except Exception:
            return {}

    # ── Extended Cases routes ──────────────────────────────────────────────
    @app.get("/cases/{case_id}")
    async def case_detail(case_id: str):
        from fastapi.responses import JSONResponse
        from app.services.case_store import get_case

        data = get_case(case_id)
        if data:
            return data
        return JSONResponse(status_code=404, content={"detail": "Case not found"})

    @app.delete("/cases/{case_id}")
    async def case_delete(case_id: str):
        from fastapi.responses import JSONResponse
        from app.services.case_store import delete_case

        if delete_case(case_id):
            return {"deleted": True, "case_id": case_id}
        return JSONResponse(status_code=404, content={"detail": "Case not found"})

    @app.get("/cases/{case_id}/raw")
    async def case_raw(case_id: str):
        from fastapi.responses import JSONResponse
        from app.services.case_store import get_case

        data = get_case(case_id)
        if data:
            import json

            return {"raw": json.dumps(data, indent=2, ensure_ascii=False)}
        return JSONResponse(status_code=404, content={"detail": "Case not found"})

    # ── Agents / Pipeline / Debug routes ──────────────────────────────────
    @app.get("/agents")
    async def list_agents():
        from app.services.agent_registry import list_agents as list_registered_agents

        return list_registered_agents()

    @app.get("/agents/{agent_name}")
    async def agent_detail(agent_name: str):
        from fastapi.responses import JSONResponse
        from app.services.agent_registry import get_agent

        agent = get_agent(agent_name)
        if not agent:
            return JSONResponse(status_code=404, content={"detail": "Agent not found"})

        prompt_preview = None
        prompt_name = agent.get("prompt_name")
        if prompt_name:
            try:
                from app.config import load_prompt

                prompt_preview = load_prompt(prompt_name)[:400]
            except Exception:
                prompt_preview = None

        return {
            **agent,
            "status": "active",
            "prompt_preview": prompt_preview,
        }

    @app.get("/pipeline/stats")
    async def pipeline_stats():
        memory_manager = getattr(app.state, "memory_manager", None)
        tracer = getattr(app.state, "tracer", None)
        daemon = _services.get("daemon")
        return {
            "graph_ready": getattr(getattr(app, "state", None), "graph", None)
            is not None,
            "services": {
                "daemon": daemon is not None,
                "adaptive": getattr(app.state, "adaptive", None) is not None,
                "learning": getattr(app.state, "learning_engine", None) is not None,
                "tracing": tracer is not None,
            },
            "memory_cases": memory_manager.total_cases()
            if memory_manager and hasattr(memory_manager, "total_cases")
            else 0,
            "trace_stats": tracer.get_stats() if tracer and hasattr(tracer, "get_stats") else {},
            "space": os.getenv("SPACE_ID", "local"),
        }

    @app.get("/debug/state/{case_id}")
    async def debug_state(case_id: str):
        from fastapi.responses import JSONResponse
        from app.services.case_store import get_case

        case = get_case(case_id)
        if not case:
            return JSONResponse(status_code=404, content={"detail": "Case not found"})

        memory_manager = getattr(app.state, "memory_manager", None)
        tracer = getattr(app.state, "tracer", None)
        debug_trace = None
        if case.get("trace_id") and tracer and hasattr(tracer, "get_traces"):
            recent_traces = tracer.get_traces(limit=200)
            debug_trace = next(
                (trace for trace in recent_traces if trace.get("trace_id") == case.get("trace_id")),
                None,
            )

        return {
            "case_id": case_id,
            "case": case,
            "context_preview": _build_runtime_context(app, case.get("user_input", ""), None),
            "similar_cases": memory_manager.find_similar(case.get("user_input", ""), top_k=5)
            if memory_manager and hasattr(memory_manager, "find_similar")
            else [],
            "trace": debug_trace,
        }

    # ── Traces / Curation / Domain routes ─────────────────────────────────
    @app.get("/traces")
    async def list_traces(limit: int = 50, score_min: float = 0.0, domain: str = None):
        tracer = getattr(app.state, "tracer", None)
        traces = tracer.get_traces(limit=limit, score_min=score_min, domain=domain) if tracer and hasattr(tracer, "get_traces") else []
        return {"traces": traces, "count": len(traces)}

    @app.get("/traces/stats")
    async def traces_stats():
        tracer = getattr(app.state, "tracer", None)
        return tracer.get_stats() if tracer and hasattr(tracer, "get_stats") else {"total_traces": 0}

    @app.get("/curation/examples")
    async def curation_examples(limit: int = 50, domain: str = None, query_type: str = None):
        curator = getattr(app.state, "curator", None)
        examples = curator.get_curated_examples(limit=limit, domain=domain, query_type=query_type) if curator and hasattr(curator, "get_curated_examples") else []
        return {"examples": examples, "count": len(examples)}

    @app.get("/curation/stats")
    async def curation_stats():
        curator = getattr(app.state, "curator", None)
        return curator.get_stats() if curator and hasattr(curator, "get_stats") else {"curated_count": 0, "rejected_count": 0}

    @app.post("/curation/push-to-hf")
    async def curation_push(limit: int = 500):
        hf_pusher = getattr(app.state, "hf_pusher", None)
        if hf_pusher and hasattr(hf_pusher, "push_curated_dataset"):
            return hf_pusher.push_curated_dataset(limit=limit)
        return {"error": "HF dataset pusher unavailable"}

    @app.get("/domain/classify")
    async def domain_classify(query: str = ""):
        if not query.strip():
            return {"detail": "Missing query"}

        domain_classifier = getattr(app.state, "domain_classifier", None)
        query_classifier = getattr(app.state, "query_classifier", None)
        domain_result = domain_classifier.classify(query) if domain_classifier and hasattr(domain_classifier, "classify") else None
        query_result = query_classifier.classify(query) if query_classifier and hasattr(query_classifier, "classify") else None
        top_domains = domain_classifier.get_top_domains(query, top_n=3) if domain_classifier and hasattr(domain_classifier, "get_top_domains") else []
        top_domains_payload = [
            {"domain": item[0].value, "confidence": item[1]} for item in top_domains
        ]
        if (
            query_result
            and query_result[2].get("detected_domain")
            and query_result[2].get("detected_domain") != "general"
            and (not top_domains or top_domains[0][0].value == "general")
        ):
            top_domains_payload = [
                {
                    "domain": query_result[2]["detected_domain"],
                    "confidence": query_result[1],
                }
            ]

        resolved_domain = domain_result.domain.value if domain_result else "general"
        resolved_confidence = domain_result.confidence if domain_result else 0.5
        if (
            resolved_domain == "general"
            and query_result
            and query_result[2].get("detected_domain")
            and query_result[2].get("detected_domain") != "general"
        ):
            resolved_domain = query_result[2]["detected_domain"]
            resolved_confidence = max(resolved_confidence, query_result[1])

        return {
            "domain": resolved_domain,
            "confidence": resolved_confidence,
            "keywords_found": domain_result.keywords_found if domain_result else [],
            "reasoning": domain_result.reasoning if domain_result else "classifier unavailable",
            "query_type": getattr(query_result[0], "value", "unknown") if query_result else "unknown",
            "query_type_confidence": query_result[1] if query_result else 0.0,
            "query_metadata": query_result[2] if query_result else {},
            "top_domains": top_domains_payload,
        }

    @app.get("/domain/confidence")
    async def domain_confidence(query: str = ""):
        domain_classifier = getattr(app.state, "domain_classifier", None)
        memory_manager = getattr(app.state, "memory_manager", None)

        if not query.strip():
            return {
                "domains": memory_manager.get_domain_stats()
                if memory_manager and hasattr(memory_manager, "get_domain_stats")
                else {}
            }

        if not domain_classifier or not hasattr(domain_classifier, "domain_keywords"):
            return {"domains": {}}

        domain_scores = {}
        for domain_type in domain_classifier.domain_keywords.keys():
            try:
                domain_scores[domain_type.value] = domain_classifier.get_domain_confidence(query, domain_type)
            except Exception:
                continue

        return {"domains": domain_scores}

    @app.get("/domain/top")
    async def domain_top(query: str = "", limit: int = 5):
        domain_classifier = getattr(app.state, "domain_classifier", None)
        query_classifier = getattr(app.state, "query_classifier", None)
        memory_manager = getattr(app.state, "memory_manager", None)

        if not query.strip():
            top_domains = []
            if memory_manager and hasattr(memory_manager, "get_domain_stats"):
                domain_stats = memory_manager.get_domain_stats()
                top_domains = sorted(
                    [
                        {"domain": name, **stats}
                        for name, stats in domain_stats.items()
                    ],
                    key=lambda item: item.get("count", 0),
                    reverse=True,
                )[:limit]
            return {"top_domains": top_domains}

        top_domains = domain_classifier.get_top_domains(query, top_n=limit) if domain_classifier and hasattr(domain_classifier, "get_top_domains") else []
        if (
            query_classifier
            and hasattr(query_classifier, "classify")
            and (not top_domains or top_domains[0][0].value == "general")
        ):
            try:
                _, confidence, metadata = query_classifier.classify(query)
                detected_domain = metadata.get("detected_domain")
                if detected_domain and detected_domain != "general":
                    return {
                        "top_domains": [
                            {"domain": detected_domain, "confidence": confidence}
                        ]
                    }
            except Exception:
                pass
        return {
            "top_domains": [
                {"domain": domain.value, "confidence": confidence}
                for domain, confidence in top_domains
            ]
        }

    @app.get("/health/features")
    async def health_features():
        return {
            "simulation": os.getenv("SIMULATION_ENABLED", "true") == "true",
            "sentinel": os.getenv("SENTINEL_ENABLED", "true") == "true",
            "learning": os.getenv("LEARNING_ENABLED", "false") == "true",
            "curiosity": os.getenv("CURIOSITY_ENGINE_ENABLED", "false") == "true",
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

    @app.api_route(
        "/{full_path:path}", methods=_FRONTEND_PROXY_METHODS, include_in_schema=False
    )
    async def frontend_catchall(request: Request, full_path: str):
        return await _proxy_frontend_request(request, full_path)

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
        reload=False,  # Never reload in production/HF Space
        workers=1,  # Single worker — HF free tier has limited RAM
    )
