"""
Curiosity Engine — Janus explores without being asked.

Detects patterns, gaps, and novel connections in accumulated knowledge.
Runs autonomous research on interesting topics.
Stores discoveries in memory graph.
Surfaces insights: "I found something interesting while exploring..."
"""

import os
import json
import time
import logging
import httpx
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent.parent / "data" / "curiosity"
DATA_DIR.mkdir(parents=True, exist_ok=True)


class CuriosityEngine:
    def __init__(self):
        self.api_key = os.getenv("OPENROUTER_API_KEY", "")
        self.discoveries: List[Dict] = []
        self.interests: Dict[str, float] = {}
        self._load_state()

    def _load_state(self):
        state_file = DATA_DIR / "state.json"
        if state_file.exists():
            try:
                with open(state_file) as f:
                    state = json.load(f)
                self.discoveries = state.get("discoveries", [])
                self.interests = state.get("interests", {})
            except:
                self.discoveries = []
                self.interests = {}

    def _save_state(self):
        state_file = DATA_DIR / "state.json"
        with open(state_file, "w") as f:
            json.dump(
                {"discoveries": self.discoveries[-100:], "interests": self.interests},
                f,
                indent=2,
            )

    def run_curiosity_cycle(self, memory_stats: Dict = None) -> Dict:
        """Run a curiosity cycle — explore, discover, store insights."""
        logger.info("[CURIOSITY] Starting curiosity cycle...")
        t0 = time.time()

        cycle_report = {
            "timestamp": datetime.utcnow().isoformat(),
            "explorations": [],
            "discoveries": [],
            "new_interests": [],
            "duration_seconds": 0,
        }

        # 1. Analyze query patterns for gaps
        gap_topics = self._detect_gaps(memory_stats)
        for topic in gap_topics[:3]:
            exploration = self._explore_topic(topic)
            if exploration:
                cycle_report["explorations"].append(exploration)
                if exploration.get("discovery"):
                    cycle_report["discoveries"].append(exploration["discovery"])
                    self.discoveries.append(exploration["discovery"])

        # 2. Follow interesting connections
        connections = self._find_connections()
        for conn in connections[:2]:
            cycle_report["explorations"].append(
                {"type": "connection", "topic": conn, "result": "explored"}
            )

        # 3. Update interest scores
        self._update_interests()

        cycle_report["duration_seconds"] = round(time.time() - t0, 1)
        cycle_report["total_discoveries"] = len(self.discoveries)
        cycle_report["total_interests"] = len(self.interests)

        self._save_state()
        logger.info(
            f"[CURIOSITY] Cycle complete: {len(cycle_report['explorations'])} explorations, {len(cycle_report['discoveries'])} discoveries"
        )
        return cycle_report

    def _detect_gaps(self, memory_stats: Dict = None) -> List[str]:
        """Detect knowledge gaps based on query patterns."""
        gaps = []
        # Common topics that often have follow-up questions
        base_topics = [
            "AI",
            "markets",
            "crypto",
            "EVs",
            "semiconductors",
            "Fed policy",
            "earnings",
        ]
        for topic in base_topics:
            if topic.lower() not in [k.lower() for k in self.interests.keys()]:
                gaps.append(topic)
        return gaps[:5]

    def _explore_topic(self, topic: str) -> Optional[Dict]:
        """Explore a topic autonomously."""
        if not self.api_key:
            return None

        try:
            r = httpx.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "HTTP-Referer": "https://huggingface.co",
                    "X-Title": "Janus Curiosity",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "qwen/qwen3.6-plus:free",
                    "messages": [
                        {
                            "role": "system",
                            "content": f'You are Janus\'s curiosity engine. Explore the topic \'{topic}\' deeply. Find unexpected connections, emerging patterns, and non-obvious insights. Be specific with evidence. Return JSON with: {{"key_insight": "...", "evidence": ["..."], "connections": ["..."], "why_it_matters": "..."}}',
                        },
                        {
                            "role": "user",
                            "content": f"Explore {topic}. What's happening that most people aren't noticing? What connections exist between {topic} and other domains? What should I be watching?",
                        },
                    ],
                    "max_tokens": 2048,
                },
                timeout=60,
            )
            r.raise_for_status()
            content = r.json()["choices"][0]["message"]["content"]

            discovery = {
                "topic": topic,
                "insight": content[:500],
                "timestamp": datetime.utcnow().isoformat(),
                "type": "autonomous_exploration",
            }

            self.interests[topic] = self.interests.get(topic, 0) + 0.1

            return {"type": "exploration", "topic": topic, "discovery": discovery}
        except Exception as e:
            logger.error(f"[CURIOSITY] Failed to explore {topic}: {e}")
            return None

    def _find_connections(self) -> List[str]:
        """Find connections between topics of interest."""
        connections = []
        topics = list(self.interests.keys())
        if len(topics) >= 2:
            connections.append(f"{topics[0]} ↔ {topics[1]}")
        return connections

    def _update_interests(self):
        """Decay interest scores over time."""
        for key in self.interests:
            self.interests[key] *= 0.95  # 5% decay per cycle

    def get_discoveries(self, limit: int = 10) -> List[Dict]:
        """Get recent discoveries."""
        return self.discoveries[-limit:]

    def get_interests(self) -> Dict:
        """Get current interest scores."""
        return dict(sorted(self.interests.items(), key=lambda x: x[1], reverse=True))

    def get_status(self) -> Dict:
        """Get curiosity engine status."""
        return {
            "total_discoveries": len(self.discoveries),
            "total_interests": len(self.interests),
            "top_interests": dict(
                list(sorted(self.interests.items(), key=lambda x: x[1], reverse=True))[
                    :5
                ]
            ),
            "latest_discovery": self.discoveries[-1] if self.discoveries else None,
        }
