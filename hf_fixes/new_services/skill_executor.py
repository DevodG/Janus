"""
New service: SkillExecutor

Janus's "self-improving" layer. After accumulating enough cases, it distils
reusable skills — pre-computed answer patterns for common query types.

A skill = a (trigger_pattern, cached_answer_template, customisation_fn) tuple.
On each /run call, SkillExecutor checks if a skill applies and short-circuits
the full pipeline, returning in milliseconds instead of 10-30 seconds.

This is how Janus genuinely gets smarter and faster over time without needing
fine-tuning or GPU resources.

Skills are stored in data/skills/*.json and rebuilt automatically when patterns
hit a frequency threshold (default: 5 similar queries).
"""
from __future__ import annotations

import json
import logging
import pathlib
import re
import time
from dataclasses import dataclass, asdict
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)

try:
    from app.config import DATA_DIR
    from app.services.memory_manager import memory_manager
except ImportError:
    DATA_DIR = pathlib.Path(__file__).parent.parent / "data"
    memory_manager = None  # type: ignore

SKILLS_DIR = pathlib.Path(DATA_DIR) / "skills"


@dataclass
class Skill:
    id:              str
    name:            str
    trigger_pattern: str          # regex
    domain:          str
    template:        str          # answer template with {placeholders}
    example_queries: list[str]
    usage_count:     int = 0
    success_rate:    float = 1.0
    created_at:      float = 0.0
    last_used:       float = 0.0

    def matches(self, query: str) -> bool:
        try:
            return bool(re.search(self.trigger_pattern, query, re.IGNORECASE))
        except re.error:
            return False

    def to_dict(self) -> dict:
        return asdict(self)


class SkillExecutor:
    """
    Check skills before running the full pipeline.
    Build new skills from accumulated case patterns.
    """

    FREQUENCY_THRESHOLD = 5      # min similar queries to create a skill
    MIN_QUALITY         = 0.65   # min quality score to learn from

    def __init__(self):
        SKILLS_DIR.mkdir(parents=True, exist_ok=True)
        self._skills: list[Skill] = []
        self._load_skills()
        logger.info("SkillExecutor: loaded %d skills", len(self._skills))

    # ── Public API ─────────────────────────────────────────────────────────

    def check(self, query: str, context: Optional[dict] = None) -> Optional[dict]:
        """
        Check if a skill matches the query.
        Returns a pre-built answer dict, or None to run the full pipeline.
        """
        for skill in self._skills:
            if skill.matches(query):
                skill.usage_count += 1
                skill.last_used    = time.time()
                self._save_skill(skill)
                logger.info("SkillExecutor: skill '%s' matched query", skill.name)
                return {
                    "answer":        skill.template,
                    "skill_used":    skill.id,
                    "skill_name":    skill.name,
                    "from_cache":    True,
                    "pipeline_skipped": True,
                }
        return None

    def maybe_build_skill(self, query: str, answer: str, quality: float = 0.7):
        """
        Called after each successful pipeline run.
        If similar queries have been seen enough times, distil a skill.
        """
        if quality < self.MIN_QUALITY:
            return
        if memory_manager is None:
            return
        similar = memory_manager.find_similar(query, top_k=10)
        high_quality = [s for s in similar if s.get("quality", 0) >= self.MIN_QUALITY]
        if len(high_quality) < self.FREQUENCY_THRESHOLD:
            return

        # Check we don't already have a skill for this pattern
        for skill in self._skills:
            if skill.matches(query):
                return  # skill already exists

        # Build a new skill from the pattern
        skill = self._distil_skill(query, answer, high_quality)
        if skill:
            self._skills.append(skill)
            self._save_skill(skill)
            logger.info("SkillExecutor: new skill created — '%s'", skill.name)

    def list_skills(self) -> list[dict]:
        return [s.to_dict() for s in self._skills]

    def skill_stats(self) -> dict:
        return {
            "total":      len(self._skills),
            "total_uses": sum(s.usage_count for s in self._skills),
            "top_skills": sorted(
                [{"name": s.name, "uses": s.usage_count} for s in self._skills],
                key=lambda x: -x["uses"]
            )[:5],
        }

    # ── Internals ──────────────────────────────────────────────────────────

    def _distil_skill(self, query: str, answer: str, similar: list[dict]) -> Optional[Skill]:
        """Extract a generalised pattern from the query cluster."""
        import hashlib

        # Generalise the query into a regex pattern
        pattern = _generalise_to_pattern(query, [s.get("query", "") for s in similar])
        if not pattern:
            return None

        skill_id = hashlib.md5(pattern.encode()).hexdigest()[:8]
        name     = _infer_skill_name(query)

        # Infer domain from similar cases
        domains = [s.get("domain", "general") for s in similar]
        domain  = max(set(domains), key=domains.count)

        return Skill(
            id=skill_id,
            name=name,
            trigger_pattern=pattern,
            domain=domain,
            template=answer[:2000],   # cap to 2KB
            example_queries=[s.get("query", "")[:100] for s in similar[:3]],
            created_at=time.time(),
        )

    def _load_skills(self):
        for f in SKILLS_DIR.glob("*.json"):
            try:
                data = json.loads(f.read_text())
                self._skills.append(Skill(**data))
            except Exception as exc:
                logger.warning("SkillExecutor: failed to load %s — %s", f.name, exc)

    def _save_skill(self, skill: Skill):
        try:
            (SKILLS_DIR / f"{skill.id}.json").write_text(
                json.dumps(skill.to_dict(), indent=2)
            )
        except Exception as exc:
            logger.warning("SkillExecutor: save failed for %s — %s", skill.id, exc)


# ── Pattern generalisation helpers ───────────────────────────────────────────

def _generalise_to_pattern(primary: str, similar_queries: list[str]) -> Optional[str]:
    """
    Find common n-gram skeleton across queries and build a regex.
    Very conservative — only creates patterns with high confidence.
    """
    if not similar_queries:
        return None

    # Find common significant words
    primary_words = set(re.findall(r'\b\w{4,}\b', primary.lower()))
    common_words  = primary_words.copy()
    for q in similar_queries[:5]:
        q_words = set(re.findall(r'\b\w{4,}\b', q.lower()))
        common_words &= q_words

    # Remove stopwords
    stopwords = {"what","when","where","which","will","tell","explain",
                 "about","does","have","that","this","with","your"}
    common_words -= stopwords

    if not common_words:
        return None

    # Build pattern from top 3 common words (in order of appearance)
    ordered = [w for w in re.findall(r'\b\w{4,}\b', primary.lower())
               if w in common_words][:3]
    if len(ordered) < 2:
        return None

    return r'\b' + r'\b.*?\b'.join(re.escape(w) for w in ordered) + r'\b'


def _infer_skill_name(query: str) -> str:
    """Infer a human-readable skill name from a query."""
    words  = re.findall(r'\b[A-Za-z]{4,}\b', query)[:4]
    stopwords = {"what","when","where","tell","give","show","explain","about","does"}
    words  = [w for w in words if w.lower() not in stopwords]
    return " ".join(words[:3]).title() or "General Query"


# Singleton
skill_executor = SkillExecutor()
