"""
Learning API endpoints for autonomous knowledge evolution.
"""

import asyncio
import logging
from fastapi import APIRouter, HTTPException
from typing import List, Optional

from ..schemas import (
    LearningStatusResponse,
    LearningInsightsResponse,
    KnowledgeIngestionRequest,
    KnowledgeItem,
    Skill,
    SkillDistillRequest,
    SourceTrust,
    PromptVersion,
)
from ..config import get_config
from ..services.learning import (
    KnowledgeIngestor,
    KnowledgeStore,
    LearningEngine,
    PromptOptimizer,
    SkillDistiller,
    TrustManager,
    LearningScheduler,
)
from ..agents._model import call_model

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/learning", tags=["learning"])

# Global instances - initialized via init_learning_services()
learning_engine: Optional[LearningEngine] = None
knowledge_store: Optional[KnowledgeStore] = None
prompt_optimizer: Optional[PromptOptimizer] = None
skill_distiller: Optional[SkillDistiller] = None
trust_manager: Optional[TrustManager] = None
scheduler: Optional[LearningScheduler] = None


async def _async_call_model(prompt: str, max_tokens: int = 1000) -> str:
    """Async wrapper around synchronous call_model."""
    return call_model(prompt, mode="chat")


def init_learning_services(config):
    """Initialize all learning services. Called from main.py on startup."""
    global learning_engine, knowledge_store, prompt_optimizer, skill_distiller, trust_manager, scheduler

    knowledge_store = KnowledgeStore(
        data_dir=config.data_dir,
        max_size_mb=config.knowledge_max_size_mb,
    )

    knowledge_ingestor = KnowledgeIngestor(
        tavily_key=config.tavily_api_key,
        newsapi_key=config.newsapi_key,
        model_fn=_async_call_model,
    )

    prompt_optimizer = PromptOptimizer(
        data_dir=config.data_dir,
        model_fn=_async_call_model,
    )

    skill_distiller = SkillDistiller(
        data_dir=config.data_dir,
        model_fn=_async_call_model,
    )

    trust_manager = TrustManager(data_dir=config.data_dir)

    learning_engine = LearningEngine(
        knowledge_store=knowledge_store,
        knowledge_ingestor=knowledge_ingestor,
        prompt_optimizer=prompt_optimizer,
        skill_distiller=skill_distiller,
        trust_manager=trust_manager,
    )

    scheduler = LearningScheduler(
        max_cpu_percent=50.0,
        min_battery_percent=30.0,
        check_interval_seconds=60,
    )

    if config.learning_enabled:
        # Task 1: Knowledge ingestion (every 6 hours)
        scheduler.schedule_task(
            "knowledge_ingestion",
            lambda: learning_engine.run_knowledge_ingestion(config.learning_topics),
            interval_hours=config.learning_schedule_interval,
        )
        # Task 2: Expired knowledge cleanup (daily)
        scheduler.schedule_task(
            "cleanup",
            lambda: learning_engine.run_cleanup(expiration_days=30),
            interval_hours=24,
        )
        # Task 3: Pattern detection (daily)
        async def _run_pattern_detection():
            return learning_engine.detect_patterns()

        scheduler.schedule_task(
            "pattern_detection",
            _run_pattern_detection,
            interval_hours=24,
        )
        # Task 4: Skill distillation (weekly)
        scheduler.schedule_task(
            "skill_distillation",
            lambda: learning_engine.run_skill_distillation(min_frequency=3),
            interval_hours=168,
        )
        # Task 5: Prompt optimization (weekly)
        scheduler.schedule_task(
            "prompt_optimization",
            lambda: learning_engine.run_prompt_optimization(
                ["research", "planner", "verifier", "synthesizer"]
            ),
            interval_hours=168,
        )

    logger.info("Learning services initialized with all scheduled tasks")


def start_scheduler_background():
    """Start the learning scheduler as a background asyncio task."""
    if scheduler and not scheduler.running:
        asyncio.create_task(scheduler.start())
        logger.info("Learning scheduler started in background")


# ── Status ────────────────────────────────────────────────────────────────────

@router.get("/status")
async def get_learning_status():
    if not learning_engine:
        raise HTTPException(status_code=503, detail="Learning engine not initialized")

    status = learning_engine.get_status()

    # Include scheduler status
    if scheduler:
        status["scheduler"] = scheduler.get_status()

    return status


@router.post("/run-once")
async def run_learning_once(task_name: str):
    if not scheduler:
        raise HTTPException(status_code=503, detail="Scheduler not initialized")
    try:
        return await scheduler.run_once(task_name)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/insights")
async def get_learning_insights():
    if not learning_engine:
        raise HTTPException(status_code=503, detail="Learning engine not initialized")
    return learning_engine.get_insights()


# ── Knowledge  (fixed-path routes BEFORE parameterised ones) ─────────────────

@router.get("/knowledge")
async def list_knowledge(limit: Optional[int] = 50):
    if not knowledge_store:
        raise HTTPException(status_code=503, detail="Knowledge store not initialized")
    return knowledge_store.list_all(limit=limit)


@router.post("/knowledge/ingest")
async def ingest_knowledge(request: KnowledgeIngestionRequest):
    if not learning_engine:
        raise HTTPException(status_code=503, detail="Learning engine not initialized")
    return await learning_engine.run_knowledge_ingestion(request.topics)


@router.get("/knowledge/search")
async def search_knowledge(query: str, limit: int = 10):
    if not knowledge_store:
        raise HTTPException(status_code=503, detail="Knowledge store not initialized")
    return knowledge_store.search_knowledge(query, limit=limit)


@router.get("/knowledge/{item_id}")
async def get_knowledge_item(item_id: str):
    if not knowledge_store:
        raise HTTPException(status_code=503, detail="Knowledge store not initialized")
    item = knowledge_store.get_knowledge(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Knowledge item not found")
    return item


# ── Skills  (fixed-path routes BEFORE parameterised ones) ────────────────────

@router.get("/skills")
async def list_skills():
    if not skill_distiller:
        raise HTTPException(status_code=503, detail="Skill distiller not initialized")
    return skill_distiller.list_skills()


@router.post("/skills/distill")
async def distill_skills(request: SkillDistillRequest):
    if not skill_distiller:
        raise HTTPException(status_code=503, detail="Skill distiller not initialized")
    from ..services.case_store import list_cases
    cases = list_cases(limit=100)
    candidates = skill_distiller.detect_skill_candidates(cases, min_frequency=request.min_frequency)
    skills = []
    for candidate in candidates[:5]:
        example_cases = [c for c in cases if c.get("route", {}) and c.get("route", {}).get("domain_pack") == candidate.get("domain")][:3]
        skill = await skill_distiller.distill_skill(candidate, example_cases)
        skills.append(skill)
    return {"candidates_found": len(candidates), "skills_distilled": len(skills), "skills": skills}


@router.get("/skills/{skill_id}")
async def get_skill(skill_id: str):
    if not skill_distiller:
        raise HTTPException(status_code=503, detail="Skill distiller not initialized")
    skill = skill_distiller.get_skill(skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    return skill


# ── Trust & Freshness ─────────────────────────────────────────────────────────

@router.get("/sources/trust")
async def get_trusted_sources(min_trust: float = 0.7, min_verifications: int = 3):
    if not trust_manager:
        raise HTTPException(status_code=503, detail="Trust manager not initialized")
    return trust_manager.list_trusted_sources(min_trust=min_trust, min_verifications=min_verifications)


@router.get("/sources/freshness")
async def get_stale_items(threshold: float = 0.3):
    if not trust_manager or not knowledge_store:
        raise HTTPException(status_code=503, detail="Services not initialized")
    items = knowledge_store.list_all()
    return trust_manager.get_stale_items(items, threshold=threshold)


# ── Prompt Evolution  (fixed-path routes BEFORE parameterised ones) ───────────

@router.post("/prompts/optimize/{name}")
async def optimize_prompt(name: str, goal: str):
    if not prompt_optimizer:
        raise HTTPException(status_code=503, detail="Prompt optimizer not initialized")
    from ..services.prompt_store import get_prompt
    prompt_data = get_prompt(name)
    if not prompt_data:
        raise HTTPException(status_code=404, detail=f"Prompt '{name}' not found")
    current_prompt = prompt_data["content"]
    return await prompt_optimizer.create_prompt_variant(name, current_prompt, goal)


@router.post("/prompts/promote/{name}/{version}")
async def promote_prompt_version(name: str, version: str):
    if not prompt_optimizer:
        raise HTTPException(status_code=503, detail="Prompt optimizer not initialized")
    success = prompt_optimizer.promote_prompt(version)
    if not success:
        raise HTTPException(status_code=400, detail="Promotion criteria not met (need ≥10 tests and ≥70% win rate)")
    return {"status": "promoted", "variant_id": version}


@router.get("/prompts/versions/{name}")
async def get_prompt_versions(name: str):
    if not prompt_optimizer:
        raise HTTPException(status_code=503, detail="Prompt optimizer not initialized")
    return prompt_optimizer.list_versions(name)
