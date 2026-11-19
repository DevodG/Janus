"""
Core learning engine that coordinates all learning activities.

Orchestrates knowledge ingestion, experience learning, prompt evolution,
skill distillation, trust management, and freshness management.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from collections import Counter

from .knowledge_ingestor import KnowledgeIngestor
from .knowledge_store import KnowledgeStore
from .prompt_optimizer import PromptOptimizer
from .skill_distiller import SkillDistiller
from .trust_manager import TrustManager

logger = logging.getLogger(__name__)


class LearningEngine:
    """Coordinates all learning activities."""

    def __init__(
        self,
        knowledge_store: KnowledgeStore,
        knowledge_ingestor: KnowledgeIngestor,
        prompt_optimizer: Optional[PromptOptimizer] = None,
        skill_distiller: Optional[SkillDistiller] = None,
        trust_manager: Optional[TrustManager] = None,
    ):
        self.knowledge_store = knowledge_store
        self.knowledge_ingestor = knowledge_ingestor
        self.prompt_optimizer = prompt_optimizer
        self.skill_distiller = skill_distiller
        self.trust_manager = trust_manager
        self.last_run: Dict[str, str] = {}

        # In-memory learning metadata (flushed periodically)
        self._case_learnings: List[Dict[str, Any]] = []
        self._route_stats: Counter = Counter()
        self._provider_stats: Dict[str, Dict[str, int]] = {}
        self._prompt_performance: Dict[str, Dict[str, Any]] = {}

    # ── Knowledge Ingestion ──────────────────────────────────────────────────

    async def run_knowledge_ingestion(self, topics: list[str]) -> Dict[str, Any]:
        """
        Run knowledge ingestion for specified topics.

        Args:
            topics: List of topics to ingest knowledge about

        Returns:
            Ingestion results
        """
        logger.info(f"Running knowledge ingestion for topics: {topics}")

        total_items = 0
        results = []

        for topic in topics:
            search_items = await self.knowledge_ingestor.ingest_from_search(topic)
            for item in search_items:
                self.knowledge_store.save_knowledge(item)
                total_items += 1

            news_items = await self.knowledge_ingestor.ingest_from_news(topic)
            for item in news_items:
                self.knowledge_store.save_knowledge(item)
                total_items += 1

            results.append({
                "topic": topic,
                "search_items": len(search_items),
                "news_items": len(news_items),
            })

        self.last_run["knowledge_ingestion"] = datetime.utcnow().isoformat()

        logger.info(f"Knowledge ingestion complete: {total_items} items ingested")

        return {
            "total_items": total_items,
            "results": results,
            "timestamp": self.last_run["knowledge_ingestion"],
        }

    async def run_cleanup(self, expiration_days: int = 30) -> Dict[str, Any]:
        """Run cleanup of expired knowledge."""
        logger.info("Running knowledge cleanup")

        deleted_count = self.knowledge_store.delete_expired_knowledge(expiration_days)
        self.last_run["cleanup"] = datetime.utcnow().isoformat()

        return {
            "deleted_count": deleted_count,
            "timestamp": self.last_run["cleanup"],
        }

    # ── Experience Learning (Task 34) ────────────────────────────────────────

    def learn_from_case(self, case_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract learning metadata from a completed case execution.

        Args:
            case_data: Complete case payload

        Returns:
            Learning metadata extracted
        """
        case_id = case_data.get("case_id", "unknown")
        logger.info(f"Learning from case {case_id}")

        route = case_data.get("route", {})
        outputs = case_data.get("outputs") or self._derive_outputs(case_data)

        # 1. Track route effectiveness
        route_key = f"{route.get('domain_pack', 'general')}:{route.get('execution_mode', 'standard')}"
        self._route_stats[route_key] += 1

        # 2. Track which agents produced useful output
        agents_used = []
        agent_quality = {}
        for output in outputs:
            if isinstance(output, dict):
                agent_name = output.get("agent", "unknown")
                summary = output.get("summary", "")
                confidence = output.get("confidence", 0.0)
                agents_used.append(agent_name)
                agent_quality[agent_name] = {
                    "output_length": len(summary),
                    "confidence": confidence,
                    "produced_output": len(summary) > 10,
                }

        # 3. Build learning record
        learning = {
            "case_id": case_id,
            "route": route,
            "agents_used": agents_used,
            "agent_quality": agent_quality,
            "domain": route.get("domain_pack", "general"),
            "complexity": route.get("complexity", "medium"),
            "execution_mode": route.get("execution_mode", "standard"),
            "learned_at": datetime.utcnow().isoformat(),
        }

        self._case_learnings.append(learning)

        # Keep only last 500 learnings in memory
        if len(self._case_learnings) > 500:
            self._case_learnings = self._case_learnings[-500:]

        # 4. Update trust scores for sources mentioned in research
        if self.trust_manager:
            for output in outputs:
                if isinstance(output, dict) and output.get("agent") == "research":
                    sources = output.get("details", {}).get("sources", [])
                    for source in sources:
                        if isinstance(source, str):
                            self.trust_manager.update_trust(source, True, weight=0.5)

        logger.info(f"Learned from case {case_id}: route={route_key}, agents={agents_used}")
        return learning

    def _derive_outputs(self, case_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Backfill agent outputs from the current case shape."""
        outputs: List[Dict[str, Any]] = []

        def _append(agent: str, details: Dict[str, Any]) -> None:
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

        _append("research", case_data.get("research", {}))
        _append("planner", case_data.get("planner", {}))
        _append("verifier", case_data.get("verifier", {}))
        _append("synthesizer", case_data.get("final", {}))
        return outputs

    def detect_patterns(self, min_frequency: int = 3) -> List[Dict[str, Any]]:
        """
        Detect patterns in recent case executions.

        Args:
            min_frequency: Minimum occurrences to count as a pattern

        Returns:
            List of detected patterns
        """
        if len(self._case_learnings) < min_frequency:
            return []

        patterns = []

        # Pattern 1: Domain frequency
        domain_counts = Counter(l["domain"] for l in self._case_learnings)
        for domain, count in domain_counts.items():
            if count >= min_frequency:
                patterns.append({
                    "type": "domain_frequency",
                    "domain": domain,
                    "count": count,
                    "percentage": count / len(self._case_learnings) * 100,
                })

        # Pattern 2: Execution mode frequency
        mode_counts = Counter(l["execution_mode"] for l in self._case_learnings)
        for mode, count in mode_counts.items():
            if count >= min_frequency:
                patterns.append({
                    "type": "execution_mode_frequency",
                    "mode": mode,
                    "count": count,
                    "percentage": count / len(self._case_learnings) * 100,
                })

        # Pattern 3: Agent combinations that produce high confidence
        high_confidence_combos = Counter()
        for learning in self._case_learnings:
            quality = learning.get("agent_quality", {})
            high_conf_agents = [
                a for a, q in quality.items()
                if q.get("confidence", 0) > 0.7
            ]
            if high_conf_agents:
                high_confidence_combos[tuple(sorted(high_conf_agents))] += 1

        for combo, count in high_confidence_combos.items():
            if count >= min_frequency:
                patterns.append({
                    "type": "high_confidence_agents",
                    "agents": list(combo),
                    "count": count,
                })

        self.last_run["pattern_detection"] = datetime.utcnow().isoformat()
        logger.info(f"Detected {len(patterns)} patterns from {len(self._case_learnings)} cases")
        return patterns

    def get_route_effectiveness(self) -> Dict[str, Any]:
        """Get route effectiveness insights."""
        total = sum(self._route_stats.values())
        if total == 0:
            return {"total_cases": 0, "routes": {}}

        return {
            "total_cases": total,
            "routes": {
                route: {
                    "count": count,
                    "percentage": round(count / total * 100, 1),
                }
                for route, count in self._route_stats.most_common()
            },
        }

    def get_prompt_performance(self) -> Dict[str, Any]:
        """Get prompt performance insights from case learnings."""
        if not self._case_learnings:
            return {"total_cases": 0, "agents": {}}

        agent_stats: Dict[str, Dict[str, Any]] = {}
        for learning in self._case_learnings:
            for agent, quality in learning.get("agent_quality", {}).items():
                if agent not in agent_stats:
                    agent_stats[agent] = {
                        "total_runs": 0,
                        "total_confidence": 0.0,
                        "produced_output_count": 0,
                    }
                agent_stats[agent]["total_runs"] += 1
                agent_stats[agent]["total_confidence"] += quality.get("confidence", 0)
                if quality.get("produced_output", False):
                    agent_stats[agent]["produced_output_count"] += 1

        # Calculate averages
        for agent, stats in agent_stats.items():
            runs = stats["total_runs"]
            stats["avg_confidence"] = round(stats["total_confidence"] / runs, 3) if runs > 0 else 0
            stats["output_rate"] = round(stats["produced_output_count"] / runs, 3) if runs > 0 else 0

        return {
            "total_cases": len(self._case_learnings),
            "agents": agent_stats,
        }

    # ── Prompt Evolution (Task 35) ───────────────────────────────────────────

    async def run_prompt_optimization(self, prompt_names: List[str]) -> Dict[str, Any]:
        """
        Run prompt optimization for specified prompts.

        Uses prompt_optimizer to create improved variants based on
        prompt performance data.
        """
        if not self.prompt_optimizer:
            return {"status": "skipped", "reason": "prompt_optimizer not configured"}

        results = []
        performance = self.get_prompt_performance()

        for name in prompt_names:
            agent_perf = performance.get("agents", {}).get(name, {})
            avg_conf = agent_perf.get("avg_confidence", 0.5)

            # Only optimize prompts with low average confidence
            if avg_conf > 0.8:
                results.append({"prompt": name, "status": "skipped", "reason": "already high performance"})
                continue

            try:
                from app.services.prompt_store import get_prompt
                prompt_data = get_prompt(name)
                if not prompt_data:
                    continue

                goal = f"Improve output quality (current avg confidence: {avg_conf:.2f})"
                variant = await self.prompt_optimizer.create_prompt_variant(
                    name, prompt_data["content"], goal
                )
                results.append({"prompt": name, "status": "variant_created", "variant_id": variant["id"]})
            except Exception as e:
                logger.error(f"Failed to optimize prompt {name}: {e}")
                results.append({"prompt": name, "status": "error", "error": str(e)})

        self.last_run["prompt_optimization"] = datetime.utcnow().isoformat()
        return {"results": results, "timestamp": self.last_run["prompt_optimization"]}

    def get_active_prompt(self, prompt_name: str) -> Optional[str]:
        """
        Get the active production prompt text, if one has been promoted.

        Args:
            prompt_name: Prompt name (e.g., "research", "verifier")

        Returns:
            Production prompt text, or None if no production version exists
        """
        if not self.prompt_optimizer:
            return None

        production = self.prompt_optimizer._get_production_variant(prompt_name)
        if production:
            return production.get("prompt_text")
        return None

    # ── Skill Distillation (Task 36) ─────────────────────────────────────────

    async def run_skill_distillation(self, min_frequency: int = 3) -> Dict[str, Any]:
        """
        Run skill distillation from recent case patterns.
        """
        if not self.skill_distiller:
            return {"status": "skipped", "reason": "skill_distiller not configured"}

        # Use in-memory case learnings as source data
        candidates = self.skill_distiller.detect_skill_candidates(
            self._case_learnings, min_frequency=min_frequency
        )

        skills_created = []
        for candidate in candidates[:5]:
            example_cases = [
                l for l in self._case_learnings
                if l.get("domain") == candidate.get("domain")
            ][:3]
            try:
                skill = await self.skill_distiller.distill_skill(candidate, example_cases)
                skills_created.append(skill)
            except Exception as e:
                logger.error(f"Failed to distill skill: {e}")

        self.last_run["skill_distillation"] = datetime.utcnow().isoformat()

        return {
            "candidates_found": len(candidates),
            "skills_created": len(skills_created),
            "skills": skills_created,
            "timestamp": self.last_run["skill_distillation"],
        }

    # ── Trust & Freshness (Task 37) ──────────────────────────────────────────

    async def run_freshness_refresh(self) -> Dict[str, Any]:
        """
        Check freshness of all knowledge items and flag stale ones.
        """
        if not self.trust_manager:
            return {"status": "skipped", "reason": "trust_manager not configured"}

        all_items = self.knowledge_store.list_all()
        stale = self.trust_manager.get_stale_items(all_items, threshold=0.3)
        recommendations = self.trust_manager.recommend_refresh(stale, max_recommendations=10)

        # Update freshness scores
        for item in all_items:
            freshness = self.trust_manager.calculate_freshness(item)
            item_id = item.get("id")
            if item_id:
                self.trust_manager.update_freshness(item_id, freshness)

        self.last_run["freshness_refresh"] = datetime.utcnow().isoformat()

        return {
            "total_items": len(all_items),
            "stale_items": len(stale),
            "refresh_recommendations": len(recommendations),
            "recommendations": recommendations,
            "timestamp": self.last_run["freshness_refresh"],
        }

    # ── Status & Insights ────────────────────────────────────────────────────

    def get_status(self) -> Dict[str, Any]:
        """Get learning engine status."""
        storage_stats = self.knowledge_store.get_storage_stats()

        return {
            "storage": storage_stats,
            "last_run": self.last_run,
            "enabled": True,
            "cases_learned": len(self._case_learnings),
            "components": {
                "knowledge_store": True,
                "knowledge_ingestor": True,
                "prompt_optimizer": self.prompt_optimizer is not None,
                "skill_distiller": self.skill_distiller is not None,
                "trust_manager": self.trust_manager is not None,
            },
        }

    def get_insights(self) -> Dict[str, Any]:
        """Get comprehensive learning insights."""
        recent_items = self.knowledge_store.list_all(limit=10)

        return {
            "recent_knowledge": [
                {
                    "id": item.get("id"),
                    "title": item.get("title"),
                    "source": item.get("source"),
                    "saved_at": item.get("saved_at"),
                }
                for item in recent_items
            ],
            "storage_stats": self.knowledge_store.get_storage_stats(),
            "route_effectiveness": self.get_route_effectiveness(),
            "prompt_performance": self.get_prompt_performance(),
            "patterns": self.detect_patterns(),
        }
