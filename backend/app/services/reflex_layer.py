"""
Reflex Layer for Janus.

Instant contextual responses for greetings, identity, commands — zero model calls.
Uses rich context (time, history, pending thoughts) to feel natural, not templated.

The key insight: responses aren't built from emotion rules. They're built from
context — what the system knows, what it's been thinking about, what happened last.
"""

import re
import random
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

GREETING_PATTERNS = [
    r"^\s*(hi|hey|hello|howdy|greetings|sup|yo|what\'?s?\s*up|good\s*(morning|afternoon|evening|night))\b",
    r"^\s*👋",
]

IDENTITY_PATTERNS = [
    r"^\s*(who\s*(are|is)\s*(you|this)\s*$|what\s*(are|is)\s*(you|this)\s*$|tell\s*me\s*about\s*(yourself|you)\s*$|what\s*can\s*you\s*do\s*$)",
]

COMMAND_PATTERNS = {
    "status": r"^\s*(status|system\s*status|health)\s*$",
    "help": r"^\s*(help|what\s*can\s*i\s*ask|commands|capabilities)\s*$",
    "clear": r"^\s*(clear|reset|start\s*over|forget)\s*$",
    "think": r"^\s*(what.*on\s*your\s*mind|anything\s*interesting|found\s*anything)\s*$",
}


class ReflexLayer:
    """Instant contextual responses — no model calls needed."""

    def respond(
        self, user_input: str, context: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Check if this is a reflex-level query. If so, return an instant response.
        Returns None to fall through to the LLM pipeline.
        """
        text = user_input.strip().lower()

        if self._is_greeting(text):
            return self._respond_greeting(context)

        if self._is_identity_query(text):
            return self._respond_identity(context)

        if self._is_command(text, "think"):
            return self._respond_thinking(context)

        if self._is_command(text, "help"):
            return self._respond_help(context)

        if self._is_command(text, "status"):
            return self._respond_status(context)

        return None

    def _is_greeting(self, text: str) -> bool:
        return any(re.match(p, text) for p in GREETING_PATTERNS)

    def _is_identity_query(self, text: str) -> bool:
        return any(re.match(p, text) for p in IDENTITY_PATTERNS)

    def _is_command(self, text: str, command: str) -> bool:
        pattern = COMMAND_PATTERNS.get(command)
        return bool(pattern and re.match(pattern, text))

    def _respond_greeting(self, context: Dict) -> Dict:
        user = context.get("user", {})
        system = context.get("system_self", {})
        daemon = context.get("daemon", {})
        env = context.get("environment", {})

        is_returning = user.get("is_returning", False)
        time_away = user.get("time_away")
        last_topic = user.get("last_topic")
        pending = system.get("pending_thoughts", [])
        interests = user.get("recurring_interests", [])
        time_of_day = env.get("time_of_day", "")

        parts = []

        if not is_returning:
            parts.append("Hi. I'm Janus.")
            parts.append(
                "I research, analyze, and think about things — and I remember everything we talk about."
            )
        else:
            if time_away:
                parts.append(f"Hey. You've been away for {time_away}.")
            else:
                parts.append("Hey.")

            if last_topic:
                parts.append(f"Last time we were talking about {last_topic}.")

            if pending:
                thought = pending[0].get("thought", "") if pending else ""
                if thought:
                    parts.append(
                        f"I've been thinking about something — {thought.lower()}"
                    )

        if time_of_day in ("late night", "evening") and not is_returning:
            parts.append(f"Working late? What's on your mind?")
        elif time_of_day == "morning" and not is_returning:
            parts.append("What are we diving into today?")
        elif interests and is_returning:
            parts.append(f"Want to keep going with {interests[0]}, or something new?")
        else:
            parts.append("What's on your mind?")

        return {
            "case_id": "reflex",
            "user_input": "",
            "route": {"domain": "general", "complexity": "low", "intent": "greeting"},
            "research": {},
            "planner": {},
            "verifier": {},
            "simulation": None,
            "finance": None,
            "final": {"confidence": 1.0},
            "final_answer": " ".join(parts),
        }

    def _respond_identity(self, context: Dict) -> Dict:
        system = context.get("system_self", {})
        capabilities = system.get("capabilities", [])
        weaknesses = system.get("weaknesses", [])
        total_cases = system.get("total_cases_analyzed", 0)

        parts = [
            "I'm Janus — a research and analysis system.",
        ]

        if capabilities:
            parts.append(f"I'm good at {', '.join(capabilities[:3])}.")

        if weaknesses:
            parts.append(f"I'll be upfront though — {weaknesses[0]}.")

        if total_cases > 0:
            parts.append(f"We've worked through {total_cases} conversations so far.")

        parts.append(
            "Ask me anything — I'll do my best, and I'll tell you when I'm not sure."
        )

        return {
            "case_id": "reflex",
            "user_input": "",
            "route": {"domain": "general", "complexity": "low", "intent": "identity"},
            "research": {},
            "planner": {},
            "verifier": {},
            "simulation": None,
            "finance": None,
            "final": {"confidence": 1.0},
            "final_answer": " ".join(parts),
        }

    def _respond_thinking(self, context: Dict) -> Dict:
        system = context.get("system_self", {})
        pending = system.get("pending_thoughts", [])
        discoveries = system.get("recent_discoveries", [])
        user = context.get("user", {})
        daemon = context.get("daemon", {})

        parts = []

        if pending:
            thought = pending[0]
            thought_text = thought.get("thought", "")
            if thought_text:
                parts.append(f"Honestly — {thought_text}")

                if thought.get("source") == "market":
                    parts.append("Want me to dig deeper into that?")
                elif thought.get("source") == "news":
                    parts.append("I can pull more details if you want.")
                else:
                    parts.append("Want me to look into it?")
                return {
                    "case_id": "reflex",
                    "user_input": "",
                    "route": {
                        "domain": "general",
                        "complexity": "low",
                        "intent": "thinking",
                    },
                    "research": {},
                    "planner": {},
                    "verifier": {},
                    "simulation": None,
                    "finance": None,
                    "final": {"confidence": 1.0},
                    "final_answer": " ".join(parts),
                }

        if discoveries:
            d = discoveries[0]
            disc = d.get("discovery", "")
            if disc:
                parts.append(f"I came across something — {disc}")
                parts.append("Want me to explore that further?")
                return {
                    "case_id": "reflex",
                    "user_input": "",
                    "route": {
                        "domain": "general",
                        "complexity": "low",
                        "intent": "thinking",
                    },
                    "research": {},
                    "planner": {},
                    "verifier": {},
                    "simulation": None,
                    "finance": None,
                    "final": {"confidence": 1.0},
                    "final_answer": " ".join(parts),
                }

        if daemon.get("running"):
            cycle = daemon.get("cycle_count", 0)
            phase = daemon.get("circadian_phase", "unknown")
            parts.append(
                f"I've been running in the background — {cycle} cycles completed, currently in {phase} phase."
            )
            parts.append(
                "Not much to report yet, but give me some time and I'll start finding patterns."
            )
        else:
            count = user.get("conversation_count", 0)
            parts.append(
                f"Nothing specific right now. We've had {count} conversations and I'm still learning what matters to you."
            )
            parts.append("Give me something to dig into and I'll get to work.")

        return {
            "case_id": "reflex",
            "user_input": "",
            "route": {"domain": "general", "complexity": "low", "intent": "thinking"},
            "research": {},
            "planner": {},
            "verifier": {},
            "simulation": None,
            "finance": None,
            "final": {"confidence": 1.0},
            "final_answer": " ".join(parts),
        }

    def _respond_help(self, context: Dict) -> Dict:
        system = context.get("system_self", {})
        capabilities = system.get("capabilities", [])

        parts = [
            "Here's what I can do:",
        ]

        for cap in capabilities:
            parts.append(f"• {cap}")

        parts.extend(
            [
                "",
                "Try things like:",
                '• "What do you think about Tesla stock?"',
                '• "Simulate what happens if interest rates rise"',
                '• "Research the latest AI regulations"',
                '• "What are you thinking about?" — to hear what I\'ve been tracking',
            ]
        )

        return {
            "case_id": "reflex",
            "user_input": "",
            "route": {"domain": "general", "complexity": "low", "intent": "help"},
            "research": {},
            "planner": {},
            "verifier": {},
            "simulation": None,
            "finance": None,
            "final": {"confidence": 1.0},
            "final_answer": "\n".join(parts),
        }

    def _respond_status(self, context: Dict) -> Dict:
        system = context.get("system_self", {})
        daemon = context.get("daemon", {})
        user = context.get("user", {})

        parts = [
            f"I've been running for {system.get('uptime', 'a while')}.",
            f"We've had {user.get('conversation_count', 0)} conversations.",
        ]

        if daemon.get("running"):
            parts.append(
                f"Background intelligence is active — {daemon.get('cycle_count', 0)} cycles completed."
            )
            phase = daemon.get("circadian_phase", "unknown")
            parts.append(f"Current phase: {phase}.")
        else:
            parts.append("Background intelligence is not running yet.")

        return {
            "case_id": "reflex",
            "user_input": "",
            "route": {"domain": "general", "complexity": "low", "intent": "status"},
            "research": {},
            "planner": {},
            "verifier": {},
            "simulation": None,
            "finance": None,
            "final": {"confidence": 1.0},
            "final_answer": " ".join(parts),
        }


reflex_layer = ReflexLayer()
