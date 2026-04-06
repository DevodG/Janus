"""
Context Engine for Janus.

Builds rich context for every interaction — the system's "mind".
No emotion labels, no rules. Just facts about:
- What the system knows about itself
- What it knows about the user
- What the daemon has been discovering
- The current environment (time, etc.)

This context makes responses feel natural without any explicit emotion tracking.
"""

import json
import time
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional, List

from app.config import DATA_DIR

logger = logging.getLogger(__name__)

CONTEXT_DIR = DATA_DIR / "context"
CONTEXT_DIR.mkdir(parents=True, exist_ok=True)

USER_STATE_FILE = CONTEXT_DIR / "user_state.json"
SYSTEM_STATE_FILE = CONTEXT_DIR / "system_state.json"


class ContextEngine:
    """Builds and maintains rich contextual state for every interaction."""

    def __init__(self):
        self._user_state = self._load_user_state()
        self._system_state = self._load_system_state()
        self._start_time = time.time()

    def _load_user_state(self) -> Dict:
        if USER_STATE_FILE.exists():
            try:
                with open(USER_STATE_FILE) as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "conversations": [],
            "last_interaction": None,
            "last_topic": None,
            "interests": {},
            "total_interactions": 0,
        }

    def _save_user_state(self):
        try:
            with open(USER_STATE_FILE, "w") as f:
                json.dump(self._user_state, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save user state: {e}")

    def _load_system_state(self) -> Dict:
        if SYSTEM_STATE_FILE.exists():
            try:
                with open(SYSTEM_STATE_FILE) as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "pending_thoughts": [],
            "recent_discoveries": [],
            "performance_history": [],
            "capabilities": [
                "market analysis and financial research",
                "scenario simulation and what-if analysis",
                "web research and content extraction",
                "pattern recognition across data",
                "adaptive learning from past conversations",
            ],
            "weaknesses": [],
        }

    def _save_system_state(self):
        try:
            with open(SYSTEM_STATE_FILE, "w") as f:
                json.dump(self._system_state, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save system state: {e}")

    def build_context(
        self, user_input: str, user_id: str = "default"
    ) -> Dict[str, Any]:
        """Build the full context picture for an interaction."""
        now = time.time()
        last_interaction = self._user_state.get("last_interaction")
        time_away = (
            self._format_time_away(last_interaction, now) if last_interaction else None
        )

        return {
            "system_self": {
                "capabilities": self._system_state.get("capabilities", []),
                "weaknesses": self._system_state.get("weaknesses", []),
                "pending_thoughts": self._system_state.get("pending_thoughts", [])[:5],
                "recent_discoveries": self._system_state.get("recent_discoveries", [])[
                    :3
                ],
                "uptime": self._get_uptime(),
                "total_cases_analyzed": self._user_state.get("total_interactions", 0),
            },
            "self_reflection": self._get_self_reflection_context(),
            "user": {
                "last_topic": self._user_state.get("last_topic"),
                "time_away": time_away,
                "recurring_interests": self._get_top_interests(),
                "conversation_count": self._user_state.get("total_interactions", 0),
                "is_returning": last_interaction is not None,
            },
            "daemon": self._get_daemon_context(),
            "environment": {
                "time_of_day": self._get_time_context(),
                "day_of_week": datetime.now().strftime("%A"),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        }

    def update_after_interaction(self, user_input: str, response: str, context: Dict):
        """Update state after a successful interaction."""
        now = time.time()

        self._user_state["last_interaction"] = now
        self._user_state["last_topic"] = self._extract_topic(user_input)
        self._user_state["total_interactions"] = (
            self._user_state.get("total_interactions", 0) + 1
        )

        topic = self._extract_topic(user_input)
        if topic:
            interests = self._user_state.get("interests", {})
            interests[topic] = interests.get(topic, 0) + 1
            self._user_state["interests"] = interests

        self._user_state["conversations"].append(
            {
                "input": user_input[:200],
                "response_preview": response[:200],
                "timestamp": now,
            }
        )
        self._user_state["conversations"] = self._user_state["conversations"][-50:]

        self._save_user_state()

    def add_pending_thought(self, thought: str, priority: float = 0.5):
        """Add a thought the system wants to share."""
        self._system_state["pending_thoughts"].append(
            {
                "thought": thought,
                "priority": priority,
                "created_at": time.time(),
            }
        )
        self._system_state["pending_thoughts"] = sorted(
            self._system_state["pending_thoughts"],
            key=lambda x: x["priority"],
            reverse=True,
        )[:20]
        self._save_system_state()

    def add_discovery(self, discovery: str, source: str = "daemon"):
        """Record a discovery from the daemon or research."""
        self._system_state["recent_discoveries"].append(
            {
                "discovery": discovery,
                "source": source,
                "created_at": time.time(),
            }
        )
        self._system_state["recent_discoveries"] = self._system_state[
            "recent_discoveries"
        ][-30:]
        self._save_system_state()

    def record_performance(self, success: bool, confidence: float, elapsed: float):
        """Track how well the system performed."""
        self._system_state["performance_history"].append(
            {
                "success": success,
                "confidence": confidence,
                "elapsed": elapsed,
                "timestamp": time.time(),
            }
        )
        self._system_state["performance_history"] = self._system_state[
            "performance_history"
        ][-100:]
        self._save_system_state()

    def get_pending_thoughts(self) -> List[Dict]:
        """Get pending thoughts the system wants to share."""
        return self._system_state.get("pending_thoughts", [])[:5]

    def consume_pending_thought(self, thought_text: str):
        """Remove a thought after it's been shared."""
        thoughts = self._system_state.get("pending_thoughts", [])
        self._system_state["pending_thoughts"] = [
            t for t in thoughts if t.get("thought") != thought_text
        ]
        self._save_system_state()

    def _get_top_interests(self) -> List[str]:
        interests = self._user_state.get("interests", {})
        return sorted(interests.keys(), key=lambda x: interests[x], reverse=True)[:5]

    def _get_daemon_context(self) -> Dict:
        """Get context from the daemon's recent activity."""
        try:
            from app.services.daemon import janus_daemon

            status = janus_daemon.get_status()
            return {
                "running": status.get("running", False),
                "cycle_count": status.get("cycle_count", 0),
                "circadian_phase": status.get("circadian", {}).get(
                    "phase_name", "unknown"
                ),
                "signal_queue": status.get("signal_queue", {}),
                "watchlist": status.get("watchlist", []),
            }
        except Exception:
            return {"running": False}

    def _get_self_reflection_context(self) -> Dict:
        """Get self-reflection context — opinions, corrections, gaps."""
        try:
            from app.services.self_reflection import self_reflection

            return {
                "opinions": self_reflection.get_opinions()[:5],
                "corrections": self_reflection.get_corrections()[:3],
                "gaps": self_reflection.get_gaps()[:3],
                "dataset_size": self_reflection.get_dataset_stats().get(
                    "total_entries", 0
                ),
                "learning_rate": self_reflection.self_model.get("learning_rate", 0),
                "total_reflections": self_reflection.self_model.get(
                    "total_reflections", 0
                ),
            }
        except Exception:
            return {}

    def _get_uptime(self) -> str:
        elapsed = time.time() - self._start_time
        if elapsed < 60:
            return "just started"
        elif elapsed < 3600:
            return f"{int(elapsed // 60)} minutes"
        elif elapsed < 86400:
            return f"{int(elapsed // 3600)} hours"
        else:
            return f"{int(elapsed // 86400)} days"

    def _get_time_context(self) -> str:
        hour = datetime.now().hour
        if 5 <= hour < 12:
            return "morning"
        elif 12 <= hour < 17:
            return "afternoon"
        elif 17 <= hour < 21:
            return "evening"
        else:
            return "late night"

    def _format_time_away(self, last_ts: float, now: float) -> Optional[str]:
        diff = now - last_ts
        if diff < 60:
            return None
        elif diff < 3600:
            mins = int(diff // 60)
            return f"{mins} minute{'s' if mins != 1 else ''}"
        elif diff < 86400:
            hours = int(diff // 3600)
            return f"{hours} hour{'s' if hours != 1 else ''}"
        else:
            days = int(diff // 86400)
            return f"{days} day{'s' if days != 1 else ''}"

    def _extract_topic(self, text: str) -> Optional[str]:
        words = text.lower().split()
        if len(words) < 3:
            return None
        return " ".join(words[:3])


context_engine = ContextEngine()
