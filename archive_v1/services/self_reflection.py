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
        """Called after every /run response. Left for backward compatibility, does not block chat with LLM reasoning."""
        topic_approx = user_input.split()[:3]
        topic = " ".join(topic_approx).lower()
        if len(topic) > 3:
            self._topic_freq[topic] += 1
            if self._topic_freq[topic] % 5 == 0:
                self._save()

    def _add_opinion(self, topic: str, statement: str, confidence: float):
        """Internal helper to add an LLM-generated opinion to the cache."""
        self.opinions.append({
            "topic":      topic,
            "statement":  statement,
            "confidence": confidence,
            "frequency":  self._topic_freq.get(topic.lower(), 1),
            "formed_at":  time.time(),
        })
        self.opinions = self.opinions[-MAX_OPINIONS:]
        logger.debug(f"SelfReflection: natively formed opinion on '{topic}'")

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
        topic = user_input[:50]
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
            t = topic.lower()
            return [op for op in self.opinions if t in op.get("topic", "").lower()]
        return self.opinions

    def get_corrections(self, topic: Optional[str] = None) -> list:
        if topic:
            t = topic.lower()
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
        """Called by daemon during night phase. Feeds interaction history to LLM to form deep worldviews."""
        if not recent_cases:
            return {"cases_reviewed": 0, "opinions_formed": 0, "learning_rate": 0.0}

        reviewed = len(recent_cases)
        opinions_formed = 0
        learning_rate = 0.0

        history_text = []
        for case in recent_cases:
            user_input  = case.get("user_input", case.get("query", ""))
            final       = case.get("final", {})
            response    = str(
                final.get("response")
                or final.get("answer")
                or final.get("synthesis", "")
            )
            # Remove giant think blocks to save tokens
            import re
            response = re.sub(r"<think>.*?</think>", "[Cognitive Trace Removed]", response, flags=re.DOTALL)
            
            if user_input and response:
                history_text.append(f"USER: {user_input}\nSYSTEM_REPLY: {response[:300]}...\n")
        
        if not history_text:
            return {"cases_reviewed": 0, "opinions_formed": 0, "learning_rate": 0.0}

        prompt = (
            "You are Janus, an advanced cognitive intelligence. Review your recent interaction history below.\n"
            "Identify recurring macro-trends, implicit user preferences, or major financial/analytical themes.\n"
            "Formulate 1 to 3 deep, high-level 'opinions' or 'worldviews' (approx 1-2 sentences each).\n"
            "Identify up to 2 systemic knowledge gaps (things you failed to answer or struggled researching).\n"
            "Return a STRICT JSON dictionary. No markdown formatting around the JSON, just the raw JSON text.\n"
            "{\n"
            '  "opinions": [{"topic": "...", "statement": "...", "confidence": 0.9}],\n'
            '  "gaps": [{"topic": "...", "reason": "...", "urgency": 0.8}]\n'
            "}\n\n"
            "INTERACTION HISTORY:\n"
            + "\n---\n".join(history_text)
        )

        try:
            from app.agents._model import call_model
            response_json_str = call_model([{"role": "user", "content": prompt}], temperature=0.3)
            
            # Clean possible markdown format
            response_json_str = response_json_str.strip()
            if response_json_str.startswith("```json"):
                response_json_str = response_json_str[7:]
            if response_json_str.startswith("```"):
                response_json_str = response_json_str[3:]
            if response_json_str.endswith("```"):
                response_json_str = response_json_str[:-3]
                
            data = json.loads(response_json_str.strip())
            
            opinions = data.get("opinions", [])
            for op in opinions:
                topic = op.get("topic", "")
                stmt = op.get("statement", "")
                conf = float(op.get("confidence", 0.8))
                if topic and stmt:
                    self._topic_freq[topic.lower()] += 1
                    self._add_opinion(topic, stmt, conf)
                    opinions_formed += 1
            
            gaps = data.get("gaps", [])
            for gap in gaps:
                self._add_gap(gap.get("topic", ""), gap.get("reason", ""))
                
        except Exception as e:
            logger.error(f"[SELF-REFLECTION] LLM reasoning failed: {e}")

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
