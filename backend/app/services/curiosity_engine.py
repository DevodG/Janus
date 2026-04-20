"""
Curiosity engine for Janus — autonomous knowledge exploration.

FIXES vs previous version:
  - Curiosity cycles were completing in 0.0 seconds (LLM never called)
  - Root cause: interests dict was empty after HF Space restart (ephemeral FS),
    causing the exploration loop to immediately exit with nothing to explore
  - Fix: always has a default set of seed interests to explore if none exist
  - Fix: exploration loop now runs even with zero stored discoveries
  - Added deduplication of discoveries by topic
  - Added persistence of discoveries to data/curiosity/ dir
  - Added timeout guard on each LLM call
"""

import time
import json
import logging
import math
from pathlib import Path
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

try:
    from app.config import DATA_DIR
except ImportError:
    DATA_DIR = Path(__file__).parent.parent / "data"

CURIOSITY_DIR = Path(DATA_DIR) / "curiosity"
MAX_DISCOVERIES = 200
LLM_TIMEOUT = 45

# Default seed interests — used when nothing has been learned yet (e.g. after HF restart)
DEFAULT_SEED_INTERESTS = {
    "AI market impact":        0.05,
    "Federal Reserve policy":  0.05,
    "earnings quality":        0.05,
    "semiconductor demand":    0.04,
    "energy transition":       0.04,
    "emerging market risk":    0.03,
    "corporate debt levels":   0.03,
    "geopolitical trade risk": 0.03,
    "venture capital trends":  0.02,
    "regulatory AI":           0.02,
}

EXPLORATION_TYPES = [
    "deep_dive",
    "connection",
    "contrarian",
    "future_scenario",
    "blind_spot",
]


def _call_with_timeout(fn, timeout: float):
    import threading
    result = [None]
    error  = [None]

    def target():
        try:
            result[0] = fn()
        except Exception as e:
            error[0] = e

    t = threading.Thread(target=target, daemon=True)
    t.start()
    t.join(timeout)
    if t.is_alive():
        return None, TimeoutError(f"Timed out after {timeout}s")
    return result[0], error[0]


class CuriosityEngine:
    """
    Proactively explores topics the system is interested in.
    Generates insights without being asked.
    """

    def __init__(self):
        CURIOSITY_DIR.mkdir(parents=True, exist_ok=True)
        self._interests:   dict = {}
        self._discoveries: list = []
        self._total_discoveries = 0
        self._total_interests   = 0
        self._load()

    def _load(self):
        """Load saved interests and discoveries."""
        interests_file = CURIOSITY_DIR / "interests.json"
        if interests_file.exists():
            try:
                self._interests = json.loads(interests_file.read_text())
            except Exception:
                self._interests = {}

        # If empty (e.g. after HF restart), seed with defaults
        if not self._interests:
            self._interests = dict(DEFAULT_SEED_INTERESTS)
            logger.info("CuriosityEngine: seeded with default interests (no saved state found)")

        # Load recent discoveries
        self._discoveries = []
        for f in sorted(CURIOSITY_DIR.glob("discovery_*.json"), reverse=True)[:MAX_DISCOVERIES]:
            try:
                self._discoveries.append(json.loads(f.read_text()))
            except Exception:
                pass

        self._total_discoveries = len(self._discoveries)
        self._total_interests   = len(self._interests)

    def _save_interests(self):
        try:
            (CURIOSITY_DIR / "interests.json").write_text(
                json.dumps(self._interests, indent=2)
            )
        except Exception as e:
            logger.warning(f"CuriosityEngine: save_interests failed: {e}")

    def _save_discovery(self, discovery: dict):
        try:
            ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
            (CURIOSITY_DIR / f"discovery_{ts}.json").write_text(
                json.dumps(discovery, indent=2, default=str)
            )
            # Clean old discoveries
            files = sorted(CURIOSITY_DIR.glob("discovery_*.json"))
            for old in files[:-MAX_DISCOVERIES]:
                try:
                    old.unlink()
                except Exception:
                    pass
        except Exception as e:
            logger.warning(f"CuriosityEngine: save_discovery failed: {e}")

    def run_curiosity_cycle(self, force: bool = False) -> dict:
        """
        Run one curiosity exploration cycle.
        FIXED: always explores something, even after fresh start.
        """
        t0 = time.time()
        logger.info("CuriosityEngine: starting curiosity cycle")

        report = {
            "timestamp": datetime.utcnow().isoformat(),
            "explorations": [],
            "discoveries": [],
            "new_interests": [],
            "duration_seconds": 0.0,
            "total_discoveries": self._total_discoveries,
            "total_interests": self._total_interests,
        }

        try:
            from app.agents._model import call_model

            # Always explore at least 1-2 topics per cycle
            sorted_interests = sorted(
                self._interests.items(), key=lambda x: -x[1]
            )
            import random
            explore_topics = [t for t, _ in sorted_interests[:2]]
            if len(sorted_interests) > 2:
                random_pick = random.choice(sorted_interests[2:])
                explore_topics.append(random_pick[0])

            for topic in explore_topics[:2]:  # max 2 per cycle to avoid timeout
                exploration_type = random.choice(EXPLORATION_TYPES)
                discovery = self._explore(call_model, topic, exploration_type)

                report["explorations"].append({
                    "type": exploration_type,
                    "topic": topic,
                    "result": "discovered" if discovery else "explored",
                })

                if discovery:
                    # Deduplicate by topic
                    existing_topics = {d.get("topic", "") for d in self._discoveries}
                    if topic not in existing_topics:
                        self._discoveries.insert(0, discovery)
                        self._discoveries = self._discoveries[:MAX_DISCOVERIES]
                        self._total_discoveries += 1
                        report["discoveries"].append(discovery)
                        self._save_discovery(discovery)
                        logger.info(f"CuriosityEngine: new discovery on '{topic}'")

                self._update_interest(topic, explored=True, discovered=bool(discovery))

            # Occasionally generate new interests from discoveries
            if self._discoveries and random.random() < 0.3:
                new_interests = self._generate_new_interests(call_model)
                for interest in new_interests:
                    if interest not in self._interests:
                        self._interests[interest] = 0.02
                        report["new_interests"].append(interest)
                        self._total_interests += 1
                        logger.info(f"CuriosityEngine: new interest '{interest}'")

            self._save_interests()

        except Exception as e:
            logger.error(f"CuriosityEngine: cycle error: {e}")
            report["error"] = str(e)

        report["duration_seconds"]  = round(time.time() - t0, 2)
        report["total_discoveries"] = self._total_discoveries
        report["total_interests"]   = self._total_interests
        logger.info(
            f"CuriosityEngine: cycle complete in {report['duration_seconds']:.1f}s — "
            f"{len(report['discoveries'])} discoveries"
        )
        return report

    def _explore(self, call_model, topic: str, exploration_type: str) -> Optional[dict]:
        """Explore a topic and return a discovery if found."""
        type_prompts = {
            "deep_dive":       f"Provide a non-obvious, specific insight about '{topic}'. What do most analysts miss?",
            "connection":      f"What is a surprising connection between '{topic}' and another domain?",
            "contrarian":      f"What is the strongest contrarian argument regarding '{topic}'?",
            "future_scenario": f"What is the most likely unexpected development in '{topic}' in the next 12 months?",
            "blind_spot":      f"What critical blind spot do most people have about '{topic}'?",
        }

        prompt = (
            f"You are Janus exploring '{topic}' with exploration type '{exploration_type}'.\n\n"
            + type_prompts.get(exploration_type, f"What is insightful about '{topic}'?")
            + "\n\nProvide a specific, evidence-based insight (not generic). "
            "Respond with JSON:\n"
            '{"key_insight": "...", "evidence": ["fact1", "fact2"], '
            '"why_it_matters": "...", "connections": ["related_concept"]}'
        )

        result, err = _call_with_timeout(
            lambda: call_model([{"role": "user", "content": prompt}]),
            LLM_TIMEOUT
        )

        if err or not result:
            logger.warning(f"CuriosityEngine: exploration of '{topic}' failed: {err}")
            return None

        try:
            from app.agents.smart_router import safe_parse
            data = safe_parse(result)
            key_insight    = data.get("key_insight", "")
            why_it_matters = data.get("why_it_matters", "")
            if not key_insight and not why_it_matters:
                return None
            insight_text = key_insight or result[:300]
            return {
                "topic":        topic,
                "type":         exploration_type,
                "insight":      f"{insight_text[:300]} | Why: {why_it_matters[:200]}",
                "timestamp":    datetime.utcnow().isoformat(),
                "raw_response": data,
            }
        except Exception as e:
            logger.warning(f"CuriosityEngine: parse failed for '{topic}': {e}")
            if len(result) > 50:
                return {
                    "topic":     topic,
                    "type":      exploration_type,
                    "insight":   result[:400],
                    "timestamp": datetime.utcnow().isoformat(),
                }
        return None

    def _generate_new_interests(self, call_model) -> list:
        """Generate new topics to explore based on recent discoveries."""
        recent = self._discoveries[:3]
        topics = [d.get("topic", "") for d in recent if d.get("topic")]
        prompt = (
            f"Based on these recently explored topics: {', '.join(topics)}, "
            "suggest 3 related topics worth investigating. "
            'JSON: {"topics": ["topic1", "topic2", "topic3"]}'
        )
        result, err = _call_with_timeout(
            lambda: call_model([{"role": "user", "content": prompt}]),
            30
        )
        if err or not result:
            return []
        try:
            from app.agents.smart_router import safe_parse
            data = safe_parse(result)
            return data.get("topics", [])[:3]
        except Exception:
            return []

    def _update_interest(self, topic: str, explored: bool, discovered: bool):
        """Update interest score using exponential decay + exploration boost."""
        current = self._interests.get(topic, 0.01)
        decayed = current * 0.95
        boost   = 0.01 if discovered else 0.005 if explored else 0
        self._interests[topic] = min(decayed + boost, 1.0)

    def add_interest(self, topic: str, score: float = 0.03):
        """Add a new interest (called when users ask about a topic repeatedly)."""
        if topic and len(topic) > 2:
            self._interests[topic] = max(self._interests.get(topic, 0), score)
            self._save_interests()

    def get_status(self) -> dict:
        top_interests = dict(sorted(self._interests.items(), key=lambda x: -x[1])[:10])
        return {
            "total_discoveries": self._total_discoveries,
            "total_interests":   self._total_interests,
            "top_interests":     top_interests,
            "latest_discovery":  self._discoveries[0] if self._discoveries else None,
        }

    def get_discoveries(self, limit: int = 10) -> list:
        return self._discoveries[:limit]

    def get_interests(self) -> dict:
        return dict(sorted(self._interests.items(), key=lambda x: -x[1]))
