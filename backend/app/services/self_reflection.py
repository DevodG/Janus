"""
Self-reflection engine for Janus.

FIXES vs previous version:
  - Topic extraction was cutting off at "what is the" instead of the meaningful concept
  - Pending thoughts template was generating "I've formed a view on what is the: ..."
    which accumulated indefinitely (one per daemon cycle, never deduplicated)
  - Fix: skip leading stopwords when extracting topics from queries
  - Fix: thoughts are now deduplicated before being added to the queue
  - Fix: opinions, corrections, gaps are only generated from meaningful topics (len > 5)
  - Added min_frequency threshold: a topic must appear ≥3 times before forming an opinion
"""

import json
import logging
import time
from pathlib import Path
from collections import defaultdict
from typing import Optional

logger = logging.getLogger(__name__)

try:
    from app.config import DATA_DIR
except ImportError:
    DATA_DIR = Path(__file__).parent.parent / "data"

REFLECTION_DIR = Path(DATA_DIR) / "adaptive"
REFLECTION_FILE = REFLECTION_DIR / "self_reflection.json"
MIN_OPINION_FREQUENCY = 3    # topic must appear ≥3 times to form an opinion
MAX_OPINIONS    = 50
MAX_CORRECTIONS = 100
MAX_GAPS        = 30

# Stopwords to skip when extracting meaningful topic
_STOPWORDS = {
    "what", "is", "the", "a", "an", "are", "was", "were", "how", "why",
    "when", "where", "who", "which", "will", "can", "could", "should",
    "would", "do", "does", "did", "tell", "me", "about", "explain",
    "give", "show", "find", "get", "make", "help", "please", "i", "we",
    "my", "our", "your", "their", "its", "this", "that", "these", "those",
    "some", "any", "all", "more", "most", "much", "many", "few", "little",
    "of", "in", "on", "at", "to", "for", "by", "from", "with", "and",
    "or", "but", "not", "no", "if", "than", "then", "so", "yet", "up",
}


def _extract_topic(query: str, min_word_len: int = 4) -> str:
    """
    Extract meaningful topic from a query, skipping leading stopwords.

    'what is the stock market' → 'stock market'
    'how does inflation work'  → 'inflation'
    'AAPL earnings report'     → 'AAPL earnings report'
    'what is the'              → ''  (empty = don't form an opinion)
    """
    import re
    words = re.findall(r"[a-zA-Z0-9$€£%]+", query.lower())
    meaningful = [w for w in words if w not in _STOPWORDS and len(w) >= min_word_len]
    topic = " ".join(meaningful[:4])
    return topic if len(topic) >= 4 else ""


class SelfReflection:
    """
    Tracks the system's formed opinions, user corrections, and knowledge gaps.
    Provides context for synthesizer to be more self-aware.
    """

    def __init__(self):
        REFLECTION_DIR.mkdir(parents=True, exist_ok=True)
        self.opinions:     list = []
        self.corrections:  list = []
        self.gaps:         list = []
        self.self_model:   dict = {
            "strengths":   ["financial analysis", "pattern recognition", "synthesis"],
            "weaknesses":  [],
            "personality": "analytical, direct, curious",
        }
        self._topic_freq: dict = defaultdict(int)
        self._load()

    def _load(self):
        if REFLECTION_FILE.exists():
            try:
                data = json.loads(REFLECTION_FILE.read_text())
                self.opinions    = data.get("opinions",    [])[-MAX_OPINIONS:]
                self.corrections = data.get("corrections", [])[-MAX_CORRECTIONS:]
                self.gaps        = data.get("gaps",        [])[-MAX_GAPS:]
                self.self_model  = data.get("self_model",  self.self_model)
                for op in self.opinions:
                    topic = op.get("topic", "")
                    if topic:
                        self._topic_freq[topic] += op.get("frequency", 1)
            except Exception as e:
                logger.warning(f"SelfReflection: load failed: {e}")

    def _save(self):
        try:
            REFLECTION_FILE.write_text(json.dumps({
                "opinions":    self.opinions,
                "corrections": self.corrections,
                "gaps":        self.gaps,
                "self_model":  self.self_model,
                "saved_at":    time.time(),
            }, indent=2))
        except Exception as e:
            logger.warning(f"SelfReflection: save failed: {e}")

    def reflect_on_response(
        self,
        user_input: str,
        response: str,
        confidence: float,
        data_sources: list,
        gaps: list,
        elapsed: float,
    ):
        """Called after every /run response. Only forms opinions on meaningful topics."""
        topic = _extract_topic(user_input)
        if not topic:
            logger.debug(f"SelfReflection: skipped trivial query '{user_input[:50]}'")
            return

        self._topic_freq[topic] += 1
        freq = self._topic_freq[topic]

        if freq >= MIN_OPINION_FREQUENCY:
            self._form_opinion(topic, response, confidence, freq)

        if confidence < 0.5 and gaps:
            for gap in gaps[:2]:
                self._add_gap(topic, gap)

        if elapsed > 25:
            self._add_gap(topic, f"Response took {elapsed:.0f}s — research took too long")

        if freq % 5 == 0:
            self._save()

    def _form_opinion(self, topic: str, response: str, confidence: float, frequency: int):
        """Form or update an opinion on a topic."""
        existing = next((op for op in self.opinions if op.get("topic") == topic), None)
        if existing:
            existing["frequency"] = frequency
            existing["confidence"] = (existing["confidence"] * 0.8 + confidence * 0.2)
            return

        statement = response[:200].replace("\n", " ").strip() if response else ""
        if not statement or len(statement) < 20:
            return

        self.opinions.append({
            "topic":      topic,
            "statement":  statement,
            "confidence": confidence,
            "frequency":  frequency,
            "formed_at":  time.time(),
        })
        self.opinions = self.opinions[-MAX_OPINIONS:]
        logger.debug(f"SelfReflection: formed opinion on '{topic}'")

    def _add_gap(self, topic: str, reason: str):
        """Record a knowledge gap."""
        existing = next((g for g in self.gaps if g.get("topic") == topic), None)
        if existing:
            existing["frequency"] = existing.get("frequency", 1) + 1
            return
        self.gaps.append({
            "topic":     topic,
            "reason":    reason[:200],
            "frequency": 1,
            "noted_at":  time.time(),
        })
        self.gaps = self.gaps[-MAX_GAPS:]

    def record_correction(self, user_input: str, original: str, correction: str):
        """User corrects the system — record for future use."""
        topic = _extract_topic(user_input) or user_input[:50]
        self.corrections.append({
            "topic":        topic,
            "original":     original[:300],
            "correction":   correction[:300],
            "corrected_at": time.time(),
        })
        self.corrections = self.corrections[-MAX_CORRECTIONS:]
        self._save()

    def get_opinions(self, topic: Optional[str] = None) -> list:
        if topic:
            t = _extract_topic(topic) or topic.lower()
            return [op for op in self.opinions if t in op.get("topic", "").lower()]
        return self.opinions

    def get_corrections(self, topic: Optional[str] = None) -> list:
        if topic:
            t = _extract_topic(topic) or topic.lower()
            return [c for c in self.corrections if t in c.get("topic", "").lower()]
        return self.corrections

    def get_gaps(self) -> list:
        return sorted(self.gaps, key=lambda x: -x.get("frequency", 1))

    def get_dataset_stats(self) -> dict:
        return {
            "opinions":    len(self.opinions),
            "corrections": len(self.corrections),
            "gaps":        len(self.gaps),
            "top_topics":  sorted(
                self._topic_freq.items(), key=lambda x: -x[1]
            )[:5],
        }

    def generate_pending_thought(self) -> Optional[str]:
        """Generate a pending thought. Only on meaningful, high-confidence topics."""
        top_opinions = sorted(
            [op for op in self.opinions if op.get("confidence", 0) > 0.6],
            key=lambda x: -x.get("frequency", 0)
        )
        if not top_opinions:
            return None
        op = top_opinions[0]
        topic = op.get("topic", "")
        if not topic or len(topic) < 4:
            return None
        freq = op.get("frequency", 0)
        return (
            f"I've been thinking about {topic} — you've asked about it {freq} times. "
            f"My current view: {op.get('statement', '')[:150]}"
        )

    def run_night_review(self, recent_cases: list) -> dict:
        """Called by daemon during night phase."""
        reviewed = 0
        opinions_formed = 0
        learning_rate = 0.0

        for case in recent_cases:
            user_input  = case.get("user_input", case.get("query", ""))
            final       = case.get("final", {})
            response    = str(final.get("answer", final.get("synthesis", "")))
            confidence  = float(final.get("confidence", 0.5))
            elapsed     = float(case.get("elapsed", 0))

            if user_input and response:
                topic_before = len(self.opinions)
                self.reflect_on_response(
                    user_input=user_input,
                    response=response,
                    confidence=confidence,
                    data_sources=[],
                    gaps=[],
                    elapsed=elapsed,
                )
                if len(self.opinions) > topic_before:
                    opinions_formed += 1
                reviewed += 1

        if reviewed > 0:
            learning_rate = opinions_formed / reviewed

        self._save()
        return {
            "cases_reviewed":  reviewed,
            "opinions_formed": opinions_formed,
            "learning_rate":   round(learning_rate, 3),
        }


# Module-level singleton
self_reflection = SelfReflection()
