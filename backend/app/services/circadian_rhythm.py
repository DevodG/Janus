"""
Circadian Rhythm Engine — Janus operates on natural cycles.

🌅 Morning (6-9 AM)   → Market Open Prep
☀️ Daytime (9 AM-4 PM) → Active Intelligence
🌆 Evening (4-8 PM)   → Reflection & Synthesis
🌙 Night (8 PM-6 AM)  → Dreaming Phase

Each phase has different behaviors, priorities, and processing modes.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class Phase(Enum):
    MORNING = "morning"
    DAYTIME = "daytime"
    EVENING = "evening"
    NIGHT = "night"


class CircadianRhythm:
    def __init__(self, timezone: str = "UTC"):
        self.timezone = timezone
        self.current_phase = None
        self.phase_history: List[Dict] = []

    def get_current_phase(self) -> Phase:
        """Get the current circadian phase based on time."""
        hour = datetime.utcnow().hour

        if 6 <= hour < 9:
            phase = Phase.MORNING
        elif 9 <= hour < 16:
            phase = Phase.DAYTIME
        elif 16 <= hour < 20:
            phase = Phase.EVENING
        else:
            phase = Phase.NIGHT

        if self.current_phase != phase:
            self.current_phase = phase
            self.phase_history.append(
                {
                    "phase": phase.value,
                    "timestamp": datetime.utcnow().isoformat(),
                }
            )
            logger.info(f"[CIRCADIAN] Phase changed to {phase.value}")

        return phase

    def get_phase_config(self, phase: Phase = None) -> Dict:
        """Get configuration for a phase."""
        if phase is None:
            phase = self.get_current_phase()

        configs = {
            Phase.MORNING: {
                "name": "Market Open Prep",
                "description": "Overnight digest, pre-market analysis, daily briefing",
                "poll_interval": 120,
                "news_interval": 300,
                "tasks": [
                    "overnight_news_digest",
                    "pre_market_analysis",
                    "daily_briefing",
                    "watchlist_status",
                ],
                "priority": "high",
            },
            Phase.DAYTIME: {
                "name": "Active Intelligence",
                "description": "Real-time market watching, news monitoring, event detection",
                "poll_interval": 180,
                "news_interval": 600,
                "tasks": [
                    "market_watch",
                    "news_pulse",
                    "event_detection",
                    "alert_generation",
                ],
                "priority": "medium",
            },
            Phase.EVENING: {
                "name": "Reflection & Synthesis",
                "description": "Daily wrap-up, cross-query analysis, pattern recognition",
                "poll_interval": 300,
                "news_interval": 900,
                "tasks": [
                    "daily_wrap",
                    "pattern_analysis",
                    "query_review",
                    "insight_generation",
                ],
                "priority": "low",
            },
            Phase.NIGHT: {
                "name": "Dreaming Phase",
                "description": "Deep pattern recognition, hypothesis generation, self-improvement",
                "poll_interval": 600,
                "news_interval": 1800,
                "tasks": [
                    "dream_cycle",
                    "hypothesis_generation",
                    "self_improvement",
                    "knowledge_consolidation",
                ],
                "priority": "background",
            },
        }

        return configs[phase]

    def get_status(self) -> Dict:
        """Get circadian status."""
        phase = self.get_current_phase()
        config = self.get_phase_config(phase)

        return {
            "current_phase": phase.value,
            "phase_name": config["name"],
            "phase_description": config["description"],
            "priority": config["priority"],
            "current_tasks": config["tasks"],
            "poll_interval": config["poll_interval"],
            "news_interval": config["news_interval"],
            "timezone": self.timezone,
            "phase_history": self.phase_history[-10:],
        }
