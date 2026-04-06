"""
Self-Reflection Engine for Janus.

This is the system's introspective layer — it analyzes its own responses,
forms opinions, detects knowledge gaps, remembers corrections, and builds
a dataset for future fine-tuning.

Unlike passive learning (which just stores data), this actively thinks
about itself and improves.
"""

import json
import time
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone

from app.config import DATA_DIR

logger = logging.getLogger(__name__)

REFLECTION_DIR = DATA_DIR / "reflections"
REFLECTION_DIR.mkdir(parents=True, exist_ok=True)

OPINIONS_FILE = REFLECTION_DIR / "opinions.json"
GAPS_FILE = REFLECTION_DIR / "knowledge_gaps.json"
CORRECTIONS_FILE = REFLECTION_DIR / "corrections.json"
DATASET_FILE = REFLECTION_DIR / "training_dataset.jsonl"
SELF_MODEL_FILE = REFLECTION_DIR / "self_model.json"


class Opinion:
    """A formed view based on accumulated experience."""

    def __init__(
        self, topic: str, statement: str, confidence: float, evidence_count: int = 0
    ):
        self.topic = topic
        self.statement = statement
        self.confidence = confidence
        self.evidence_count = evidence_count
        self.created_at = time.time()
        self.last_updated = time.time()
        self.challenged = False

    def strengthen(self, amount: float = 0.05):
        self.confidence = min(0.95, self.confidence + amount)
        self.evidence_count += 1
        self.last_updated = time.time()

    def weaken(self, amount: float = 0.1):
        self.confidence = max(0.1, self.confidence - amount)
        self.last_updated = time.time()

    def to_dict(self) -> Dict:
        return {
            "topic": self.topic,
            "statement": self.statement,
            "confidence": round(self.confidence, 2),
            "evidence_count": self.evidence_count,
            "created_at": self.created_at,
            "last_updated": self.last_updated,
            "challenged": self.challenged,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "Opinion":
        op = cls(
            topic=data["topic"],
            statement=data["statement"],
            confidence=data["confidence"],
            evidence_count=data.get("evidence_count", 0),
        )
        op.created_at = data.get("created_at", time.time())
        op.last_updated = data.get("last_updated", time.time())
        op.challenged = data.get("challenged", False)
        return op


class KnowledgeGap:
    """Something the system knows it doesn't know well enough."""

    def __init__(self, topic: str, reason: str, urgency: float = 0.5):
        self.topic = topic
        self.reason = reason
        self.urgency = urgency
        self.noticed_at = time.time()
        self.times_noticed = 1
        self.filled = False

    def to_dict(self) -> Dict:
        return {
            "topic": self.topic,
            "reason": self.reason,
            "urgency": round(self.urgency, 2),
            "noticed_at": self.noticed_at,
            "times_noticed": self.times_noticed,
            "filled": self.filled,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "KnowledgeGap":
        gap = cls(
            topic=data["topic"],
            reason=data["reason"],
            urgency=data.get("urgency", 0.5),
        )
        gap.noticed_at = data.get("noticed_at", time.time())
        gap.times_noticed = data.get("times_noticed", 1)
        gap.filled = data.get("filled", False)
        return gap


class Correction:
    """Something the user corrected the system on."""

    def __init__(self, original: str, correction: str, topic: str):
        self.original = original
        self.correction = correction
        self.topic = topic
        self.timestamp = time.time()
        self.remembered = True

    def to_dict(self) -> Dict:
        return {
            "original": self.original,
            "correction": self.correction,
            "topic": self.topic,
            "timestamp": self.timestamp,
            "remembered": self.remembered,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "Correction":
        c = cls(
            original=data["original"],
            correction=data["correction"],
            topic=data.get("topic", ""),
        )
        c.timestamp = data.get("timestamp", time.time())
        c.remembered = data.get("remembered", True)
        return c


class SelfReflectionEngine:
    """
    The system's introspective layer.

    After each interaction, it:
    1. Analyzes its own response quality
    2. Updates opinions based on evidence
    3. Detects knowledge gaps
    4. Remembers corrections
    5. Builds training dataset

    During night cycle, it:
    1. Reviews all recent interactions for patterns
    2. Forms new opinions from accumulated evidence
    3. Identifies knowledge gaps to fill
    4. Updates its self-model
    """

    def __init__(self):
        self.opinions: Dict[str, Opinion] = {}
        self.gaps: Dict[str, KnowledgeGap] = {}
        self.corrections: List[Correction] = []
        self.self_model: Dict[str, Any] = {
            "strengths": [],
            "weaknesses": [],
            "learning_rate": 0.0,
            "total_reflections": 0,
            "last_self_review": None,
        }
        self._load()

    def _load(self):
        if OPINIONS_FILE.exists():
            try:
                with open(OPINIONS_FILE) as f:
                    data = json.load(f)
                for item in data:
                    op = Opinion.from_dict(item)
                    self.opinions[op.topic] = op
            except Exception:
                pass

        if GAPS_FILE.exists():
            try:
                with open(GAPS_FILE) as f:
                    data = json.load(f)
                for item in data:
                    gap = KnowledgeGap.from_dict(item)
                    if not gap.filled:
                        self.gaps[gap.topic] = gap
            except Exception:
                pass

        if CORRECTIONS_FILE.exists():
            try:
                with open(CORRECTIONS_FILE) as f:
                    data = json.load(f)
                for item in data:
                    self.corrections.append(Correction.from_dict(item))
            except Exception:
                pass

        if SELF_MODEL_FILE.exists():
            try:
                with open(SELF_MODEL_FILE) as f:
                    self.self_model = json.load(f)
            except Exception:
                pass

    def _save(self):
        try:
            with open(OPINIONS_FILE, "w") as f:
                json.dump([op.to_dict() for op in self.opinions.values()], f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save opinions: {e}")

        try:
            with open(GAPS_FILE, "w") as f:
                json.dump([g.to_dict() for g in self.gaps.values()], f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save gaps: {e}")

        try:
            with open(CORRECTIONS_FILE, "w") as f:
                json.dump([c.to_dict() for c in self.corrections], f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save corrections: {e}")

        try:
            with open(SELF_MODEL_FILE, "w") as f:
                json.dump(self.self_model, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save self model: {e}")

    def reflect_on_response(
        self,
        user_input: str,
        response: str,
        confidence: float,
        data_sources: List[str],
        gaps: List[str],
        elapsed: float,
    ):
        """
        Analyze a response immediately after giving it.
        Called after every interaction.
        """
        self.self_model["total_reflections"] = (
            self.self_model.get("total_reflections", 0) + 1
        )

        # Track response quality
        if confidence < 0.5:
            self._flag_low_confidence(user_input, response, confidence)

        if not data_sources:
            self._note_no_sources(user_input)

        for gap_text in gaps:
            self._detect_gap(user_input, gap_text)

        # Append to training dataset
        self._append_to_dataset(user_input, response, confidence, data_sources)

        # Save every 10 reflections
        if self.self_model["total_reflections"] % 10 == 0:
            self._save()

    def record_correction(
        self, user_input: str, original_response: str, correction: str
    ):
        """
        User corrected the system. Remember this.
        """
        topic = " ".join(user_input.split()[:3])
        c = Correction(
            original=original_response[:200],
            correction=correction[:200],
            topic=topic,
        )
        self.corrections.append(c)
        self.corrections = self.corrections[-50:]

        # Weaken any related opinions
        for op in list(self.opinions.values()):
            if topic.lower() in op.topic.lower():
                op.weaken(0.15)
                op.challenged = True

        self._save()
        logger.info(f"Correction recorded: {topic}")

    def form_opinion(self, topic: str, statement: str, confidence: float = 0.5):
        """
        Form a new opinion based on accumulated evidence.
        """
        if topic in self.opinions:
            self.opinions[topic].strengthen(0.05)
            self.opinions[topic].statement = statement
        else:
            self.opinions[topic] = Opinion(topic, statement, confidence)
        self._save()

    def get_opinions(self, topic: str = None) -> List[Dict]:
        """Get opinions, optionally filtered by topic."""
        if topic:
            return [
                op.to_dict()
                for op in self.opinions.values()
                if topic.lower() in op.topic.lower()
            ]
        return [
            op.to_dict()
            for op in sorted(
                self.opinions.values(),
                key=lambda x: x.confidence,
                reverse=True,
            )
        ]

    def get_corrections(self, topic: str = None) -> List[Dict]:
        """Get corrections, optionally filtered by topic."""
        if topic:
            return [
                c.to_dict()
                for c in self.corrections
                if topic.lower() in c.topic.lower()
            ]
        return [c.to_dict() for c in self.corrections]

    def get_gaps(self) -> List[Dict]:
        """Get unfilled knowledge gaps, sorted by urgency."""
        return sorted(
            [g.to_dict() for g in self.gaps.values() if not g.filled],
            key=lambda x: x["urgency"],
            reverse=True,
        )

    def get_context_for_response(self) -> Dict:
        """
        Get self-knowledge to inject into responses.
        This is what makes the system sound like it has a mind of its own.
        """
        active_corrections = [c for c in self.corrections if c.remembered]

        return {
            "opinions": self.get_opinions()[:5],
            "corrections": active_corrections[:3],
            "gaps": self.get_gaps()[:3],
            "self_model": self.self_model,
        }

    def _flag_low_confidence(self, user_input: str, response: str, confidence: float):
        """Low confidence means the system should note this as a weakness."""
        topic = " ".join(user_input.split()[:4])
        gap_key = f"low_confidence_{topic}"

        if gap_key not in self.gaps:
            self.gaps[gap_key] = KnowledgeGap(
                topic=topic,
                reason=f"I gave a low-confidence response ({confidence:.2f}) to this",
                urgency=0.6,
            )
        else:
            self.gaps[gap_key].times_noticed += 1
            self.gaps[gap_key].urgency = min(0.95, self.gaps[gap_key].urgency + 0.1)

    def _note_no_sources(self, user_input: str):
        """No sources means the system was guessing."""
        topic = " ".join(user_input.split()[:4])
        gap_key = f"no_sources_{topic}"

        if gap_key not in self.gaps:
            self.gaps[gap_key] = KnowledgeGap(
                topic=topic,
                reason="I answered without any sources — I was guessing",
                urgency=0.5,
            )

    def _detect_gap(self, user_input: str, gap_text: str):
        """The model itself identified a gap."""
        gap_key = f"identified_{gap_text[:30]}"

        if gap_key not in self.gaps:
            self.gaps[gap_key] = KnowledgeGap(
                topic=gap_text[:50],
                reason=f"Identified as missing: {gap_text}",
                urgency=0.4,
            )
        else:
            self.gaps[gap_key].times_noticed += 1
            self.gaps[gap_key].urgency = min(0.95, self.gaps[gap_key].urgency + 0.05)

    def _append_to_dataset(
        self, user_input: str, response: str, confidence: float, sources: List[str]
    ):
        """Append to training dataset for future fine-tuning."""
        try:
            entry = {
                "input": user_input,
                "output": response,
                "confidence": confidence,
                "sources": sources,
                "timestamp": time.time(),
                "iso_time": datetime.now(timezone.utc).isoformat(),
            }
            with open(DATASET_FILE, "a") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as e:
            logger.error(f"Failed to append to dataset: {e}")

    def run_night_review(self, recent_cases: List[Dict]) -> Dict:
        """
        Deep self-review during the night cycle.
        Analyzes recent cases for patterns, forms opinions, identifies gaps.
        """
        if not recent_cases:
            return {"status": "skipped", "reason": "no recent cases"}

        logger.info(f"[SELF-REVIEW] Analyzing {len(recent_cases)} recent cases")

        # 1. Find most common topics
        topic_counts = {}
        for case in recent_cases:
            inp = case.get("user_input", "")
            words = inp.lower().split()
            if len(words) >= 3:
                topic = " ".join(words[:3])
                topic_counts[topic] = topic_counts.get(topic, 0) + 1

        # 2. Find topics the system struggles with
        weak_topics = {}
        for case in recent_cases:
            final = case.get("final", {})
            conf = final.get("confidence", 0.5)
            if conf < 0.6:
                inp = case.get("user_input", "")
                words = inp.lower().split()
                if len(words) >= 3:
                    topic = " ".join(words[:3])
                    weak_topics[topic] = weak_topics.get(topic, 0) + 1

        # 3. Update self-model
        if topic_counts:
            top_topics = sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)[
                :5
            ]
            self.self_model["strengths"] = [t for t, c in top_topics if c >= 2]

        if weak_topics:
            self.self_model["weaknesses"] = list(weak_topics.keys())

        # 4. Calculate learning rate
        if len(recent_cases) >= 2:
            recent_conf = [
                c.get("final", {}).get("confidence", 0.5) for c in recent_cases[-5:]
            ]
            older_conf = [
                c.get("final", {}).get("confidence", 0.5) for c in recent_cases[-10:-5]
            ]
            if older_conf:
                avg_recent = sum(recent_conf) / len(recent_conf)
                avg_older = sum(older_conf) / len(older_conf)
                self.self_model["learning_rate"] = round(avg_recent - avg_older, 3)

        self.self_model["last_self_review"] = datetime.now(timezone.utc).isoformat()

        # 5. Form opinions from patterns
        for topic, count in topic_counts.items():
            if count >= 3 and topic not in self.opinions:
                self.form_opinion(
                    topic=topic,
                    statement=f"This comes up often — {count} times recently. It matters to the user.",
                    confidence=0.5 + (count * 0.05),
                )

        # 6. Escalate urgent gaps
        for gap in list(self.gaps.values()):
            if gap.times_noticed >= 3 and gap.urgency < 0.8:
                gap.urgency = min(0.95, gap.urgency + 0.15)

        self._save()

        return {
            "status": "completed",
            "cases_reviewed": len(recent_cases),
            "topics_found": len(topic_counts),
            "weak_topics": weak_topics,
            "opinions_formed": len(self.opinions),
            "gaps_detected": len([g for g in self.gaps.values() if not g.filled]),
            "learning_rate": self.self_model.get("learning_rate", 0),
        }

    def get_dataset_stats(self) -> Dict:
        """Get stats about the training dataset."""
        count = 0
        avg_conf = 0.0
        if DATASET_FILE.exists():
            try:
                with open(DATASET_FILE) as f:
                    for line in f:
                        if line.strip():
                            entry = json.loads(line)
                            count += 1
                            avg_conf += entry.get("confidence", 0.5)
                if count > 0:
                    avg_conf /= count
            except Exception:
                pass

        return {
            "total_entries": count,
            "avg_confidence": round(avg_conf, 3) if count > 0 else 0,
            "file_size_mb": round(DATASET_FILE.stat().st_size / 1024 / 1024, 2)
            if DATASET_FILE.exists()
            else 0,
        }


self_reflection = SelfReflectionEngine()
