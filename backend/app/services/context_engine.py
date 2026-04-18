"""
Context engine for Janus — provides rich context injection into every LLM call.

FIXES vs previous version:
  - pending_thoughts queue was growing unboundedly (one malformed thought per daemon cycle)
  - Topic extraction was cutting off queries at "what is the" instead of extracting meaning
  - Deduplication: identical thoughts no longer accumulate
  - Hard cap: max 20 pending thoughts, oldest dropped when full
  - Better topic extraction: skip stopwords, take the meaningful noun phrase
"""

import time
import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

try:
    from app.config import DATA_DIR
except ImportError:
    DATA_DIR = Path(__file__).parent.parent / "data"

CONTEXT_FILE = Path(DATA_DIR) / "daemon" / "context.json"

# Stopwords to skip when extracting topic from a query
_TOPIC_STOPWORDS = {
    "what", "is", "the", "a", "an", "are", "was", "were", "how", "why",
    "when", "where", "who", "which", "will", "can", "could", "should",
    "would", "do", "does", "did", "tell", "me", "about", "explain",
    "give", "show", "find", "get", "make", "help", "please", "i", "we",
    "my", "our", "your", "their", "its", "this", "that", "these", "those",
    "some", "any", "all", "more", "most", "much", "many", "few", "little",
    "of", "in", "on", "at", "to", "for", "by", "from", "with", "and",
    "or", "but", "not", "no", "if", "than", "then", "so", "yet",
}

MAX_PENDING_THOUGHTS = 20  # hard cap — was unbounded
MAX_THOUGHT_AGE_HOURS = 24  # drop thoughts older than 24h


def _extract_topic(query: str) -> str:
    """
    Extract the meaningful topic from a query, skipping leading stopwords.

    Examples:
      "what is the stock market"     → "stock market"
      "how does inflation work"      → "inflation"
      "tell me about AAPL earnings"  → "AAPL earnings"
      "what is the"                  → "general query"  (was causing the bug)
    """
    import re
    # Clean and tokenize
    words = re.findall(r"[a-zA-Z0-9$€£%]+", query.lower())
    # Skip leading stopwords
    meaningful = []
    for w in words:
        if w not in _TOPIC_STOPWORDS or meaningful:
            if w not in _TOPIC_STOPWORDS:
                meaningful.append(w)
    # Take up to 4 meaningful words
    topic = " ".join(meaningful[:4])
    return topic if topic and len(topic) > 2 else "general query"


class ContextEngine:
    """Manages system-wide context for LLM injection."""

    def __init__(self):
        self._pending_thoughts: list = []
        self._context_cache: dict = {}
        self._conversation_count: int = 0
        self._last_topic: str = ""
        self._last_interaction: float = 0
        self._recurring_interests: list = []
        self._load()

    def _load(self):
        import json
        if CONTEXT_FILE.exists():
            try:
                data = json.loads(CONTEXT_FILE.read_text())
                raw_thoughts = data.get("pending_thoughts", [])
                # FIXED: deduplicate on load, enforce cap and age limit
                self._pending_thoughts = self._clean_thoughts(raw_thoughts)
                self._conversation_count = data.get("conversation_count", 0)
                self._last_topic = data.get("last_topic", "")
                self._last_interaction = data.get("last_interaction", 0)
                self._recurring_interests = data.get("recurring_interests", [])
            except Exception as e:
                logger.warning(f"ContextEngine: load failed: {e}")

    def _save(self):
        import json
        CONTEXT_FILE.parent.mkdir(parents=True, exist_ok=True)
        try:
            CONTEXT_FILE.write_text(json.dumps({
                "pending_thoughts": self._pending_thoughts,
                "conversation_count": self._conversation_count,
                "last_topic": self._last_topic,
                "last_interaction": self._last_interaction,
                "recurring_interests": self._recurring_interests,
            }, indent=2))
        except Exception as e:
            logger.warning(f"ContextEngine: save failed: {e}")

    def _clean_thoughts(self, thoughts: list) -> list:
        """
        Deduplicate, enforce age limit, enforce count cap.
        Returns list sorted by priority desc, newest first within same priority.
        """
        now = time.time()
        seen_texts = set()
        clean = []
        for t in thoughts:
            text = t.get("thought", "").strip()
            if not text:
                continue
            # Skip duplicates
            if text in seen_texts:
                continue
            # Skip ancient thoughts
            age_hours = (now - t.get("created_at", now)) / 3600
            if age_hours > MAX_THOUGHT_AGE_HOURS:
                continue
            seen_texts.add(text)
            clean.append(t)
        # Sort by priority desc
        clean.sort(key=lambda x: (-x.get("priority", 0), -x.get("created_at", 0)))
        # Enforce cap
        return clean[:MAX_PENDING_THOUGHTS]

    def add_pending_thought(self, thought: str, priority: float = 0.5, source: str = "system"):
        """Add a thought to the pending queue — with dedup and cap enforcement."""
        thought = thought.strip()
        if not thought or len(thought) < 10:
            return

        # Deduplicate by exact text
        existing_texts = {t.get("thought", "") for t in self._pending_thoughts}
        if thought in existing_texts:
            logger.debug(f"ContextEngine: duplicate thought skipped: {thought[:60]}")
            return

        self._pending_thoughts.append({
            "thought": thought,
            "priority": priority,
            "created_at": time.time(),
            "source": source,
        })

        # Apply cleaning after each add to enforce cap
        self._pending_thoughts = self._clean_thoughts(self._pending_thoughts)
        self._save()

    def get_pending_thoughts(self) -> list:
        """Return current pending thoughts (deduplicated, capped)."""
        self._pending_thoughts = self._clean_thoughts(self._pending_thoughts)
        return self._pending_thoughts

    def clear_delivered_thoughts(self, count: int = 3):
        """Mark the top N thoughts as delivered (remove them from queue)."""
        self._pending_thoughts = self._pending_thoughts[count:]
        self._save()

    def build_context(self, user_input: str) -> dict:
        """Build the full context dict for injection into LLM calls."""
        now = time.time()
        hours_away = (now - self._last_interaction) / 3600 if self._last_interaction else None

        # Extract topic properly — FIXED
        topic = _extract_topic(user_input) if user_input else ""

        # Update recurring interests
        if topic and topic != "general query":
            if topic not in self._recurring_interests:
                self._recurring_interests.insert(0, topic)
                self._recurring_interests = self._recurring_interests[:10]

        return {
            "user": {
                "is_returning": self._conversation_count > 0,
                "conversation_count": self._conversation_count,
                "last_topic": self._last_topic,
                "time_away": f"{hours_away:.0f}h" if hours_away and hours_away > 1 else None,
                "recurring_interests": self._recurring_interests[:5],
            },
            "system_self": {
                "pending_thoughts": self.get_pending_thoughts()[:3],
                "recent_discoveries": [],
            },
            "self_reflection": {},
            "current_topic": topic,
        }

    def update_after_interaction(self, user_input: str, response: str, context: dict):
        """Update state after each interaction."""
        topic = _extract_topic(user_input)
        if topic and topic != "general query":
            self._last_topic = topic
        self._last_interaction = time.time()
        self._conversation_count += 1
        self._save()

    def record_performance(self, success: bool, confidence: float, elapsed: float):
        pass  # Telemetry hook — can be extended


# Module-level singleton
context_engine = ContextEngine()
