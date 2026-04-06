"""
Fine-Tuning Dataset Builder for Janus.

Combines conversation data, self-reflection insights, and HF dataset extracts
into instruction-tuning pairs ready for model fine-tuning.
"""

import json
import time
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone

from app.config import DATA_DIR

logger = logging.getLogger(__name__)

FINE_TUNING_DIR = DATA_DIR / "fine_tuning"
FINE_TUNING_DIR.mkdir(parents=True, exist_ok=True)

TRAINING_FILE = FINE_TUNING_DIR / "training_data.jsonl"
METADATA_FILE = FINE_TUNING_DIR / "metadata.json"


class FineTuningBuilder:
    """
    Builds instruction-tuning dataset from:
    1. Conversation data (user input + system response)
    2. Self-reflection insights (corrections, opinions)
    3. HF dataset extracts (facts, patterns)
    """

    def __init__(self):
        self._metadata = self._load_metadata()

    def _load_metadata(self) -> Dict:
        if METADATA_FILE.exists():
            try:
                with open(METADATA_FILE) as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "total_pairs": 0,
            "sources": {},
            "last_updated": None,
            "quality_threshold": 0.6,
        }

    def _save_metadata(self):
        try:
            self._metadata["last_updated"] = datetime.now(timezone.utc).isoformat()
            with open(METADATA_FILE, "w") as f:
                json.dump(self._metadata, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save metadata: {e}")

    def add_conversation_pair(
        self,
        user_input: str,
        response: str,
        confidence: float,
        sources: List[str] = None,
    ):
        """
        Add a conversation as an instruction-tuning pair.
        Only adds if confidence is above threshold.
        """
        if confidence < self._metadata.get("quality_threshold", 0.6):
            return False

        pair = {
            "instruction": user_input,
            "input": "",
            "output": response,
            "source": "conversation",
            "confidence": confidence,
            "sources": sources or [],
            "timestamp": time.time(),
            "iso_time": datetime.now(timezone.utc).isoformat(),
        }

        self._append_pair(pair)
        self._metadata["total_pairs"] = self._metadata.get("total_pairs", 0) + 1
        self._metadata["sources"]["conversation"] = (
            self._metadata["sources"].get("conversation", 0) + 1
        )
        self._save_metadata()
        return True

    def add_correction_pair(self, original_input: str, correction: str, topic: str):
        """
        Add a user correction as a high-quality training pair.
        These are the most valuable — user-verified improvements.
        """
        pair = {
            "instruction": f"Correct your previous response about: {original_input[:200]}",
            "input": "",
            "output": correction,
            "source": "user_correction",
            "confidence": 1.0,  # User-verified
            "topic": topic,
            "timestamp": time.time(),
            "iso_time": datetime.now(timezone.utc).isoformat(),
        }

        self._append_pair(pair)
        self._metadata["total_pairs"] = self._metadata.get("total_pairs", 0) + 1
        self._metadata["sources"]["user_correction"] = (
            self._metadata["sources"].get("user_correction", 0) + 1
        )
        self._save_metadata()
        logger.info(f"Added correction pair for topic: {topic}")

    def add_dataset_pairs(self, pairs: List[Dict], source_dataset: str):
        """
        Add instruction pairs extracted from a HF dataset.
        """
        added = 0
        for pair in pairs:
            pair["source"] = f"dataset:{source_dataset}"
            pair["confidence"] = pair.get("confidence", 0.7)
            pair["timestamp"] = time.time()
            pair["iso_time"] = datetime.now(timezone.utc).isoformat()

            if pair.get("confidence", 0) >= self._metadata.get(
                "quality_threshold", 0.6
            ):
                self._append_pair(pair)
                added += 1

        self._metadata["total_pairs"] = self._metadata.get("total_pairs", 0) + added
        dataset_key = f"dataset:{source_dataset}"
        self._metadata["sources"][dataset_key] = (
            self._metadata["sources"].get(dataset_key, 0) + added
        )
        self._save_metadata()

        logger.info(f"Added {added}/{len(pairs)} pairs from {source_dataset}")
        return added

    def _append_pair(self, pair: Dict):
        """Append a training pair to the JSONL file."""
        try:
            with open(TRAINING_FILE, "a") as f:
                f.write(json.dumps(pair) + "\n")
        except Exception as e:
            logger.error(f"Failed to append training pair: {e}")

    def get_stats(self) -> Dict:
        """Get fine-tuning dataset statistics."""
        total = self._metadata.get("total_pairs", 0)
        sources = self._metadata.get("sources", {})

        # Calculate quality distribution
        quality_dist = {"high": 0, "medium": 0, "low": 0}
        if TRAINING_FILE.exists():
            try:
                with open(TRAINING_FILE) as f:
                    for line in f:
                        if line.strip():
                            entry = json.loads(line)
                            conf = entry.get("confidence", 0.5)
                            if conf >= 0.8:
                                quality_dist["high"] += 1
                            elif conf >= 0.6:
                                quality_dist["medium"] += 1
                            else:
                                quality_dist["low"] += 1
            except Exception:
                pass

        return {
            "total_pairs": total,
            "sources": sources,
            "quality_distribution": quality_dist,
            "file_size_mb": round(TRAINING_FILE.stat().st_size / 1024 / 1024, 2)
            if TRAINING_FILE.exists()
            else 0,
            "last_updated": self._metadata.get("last_updated"),
            "ready_for_training": total >= 1000,  # Minimum for meaningful fine-tuning
        }

    def export_for_training(self, min_confidence: float = 0.7) -> str:
        """
        Export high-quality pairs for model training.
        Returns the path to the exported file.
        """
        export_file = FINE_TUNING_DIR / "export_high_quality.jsonl"
        count = 0

        try:
            with open(TRAINING_FILE) as fin, open(export_file, "w") as fout:
                for line in fin:
                    if line.strip():
                        entry = json.loads(line)
                        if entry.get("confidence", 0) >= min_confidence:
                            # Convert to standard format
                            training_entry = {
                                "messages": [
                                    {
                                        "role": "user",
                                        "content": entry.get("instruction", ""),
                                    },
                                    {
                                        "role": "assistant",
                                        "content": entry.get("output", ""),
                                    },
                                ]
                            }
                            fout.write(json.dumps(training_entry) + "\n")
                            count += 1

            logger.info(f"Exported {count} high-quality pairs to {export_file}")
            return str(export_file)

        except Exception as e:
            logger.error(f"Failed to export training data: {e}")
            return ""


fine_tuning_builder = FineTuningBuilder()
