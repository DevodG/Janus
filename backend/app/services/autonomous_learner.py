"""
Autonomous Learner for Janus.

Orchestrates the full self-improvement loop:
1. Identify gaps from self-reflection
2. Search HF Hub for relevant datasets (lightweight, no downloads)
3. Extract dataset metadata as knowledge
4. Build fine-tuning dataset from conversations
5. Reduce gap urgency

Runs during daemon night cycles. Uses ONLY huggingface_hub API - no heavy libraries.
"""

import json
import time
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone

from app.services.self_reflection import self_reflection
from app.services.hf_dataset_searcher import hf_dataset_searcher
from app.services.fine_tuning_builder import fine_tuning_builder
from app.memory import knowledge_store

logger = logging.getLogger(__name__)


class AutonomousLearner:
    """
    Autonomous self-improvement system.
    Identifies gaps, finds datasets, extracts knowledge, builds training data.
    Lightweight - uses only HF Hub API, no dataset downloads.
    """

    def __init__(self):
        self.last_learning_cycle = None
        self.total_cycles = 0
        self.total_knowledge_added = 0

    def run_learning_cycle(
        self,
        max_gaps: int = 3,
        max_datasets_per_gap: int = 3,
    ) -> Dict:
        """
        Run a complete autonomous learning cycle.
        Lightweight - only uses HF Hub API for dataset search and metadata.
        """
        self.total_cycles += 1
        start_time = time.time()
        logger.info(
            f"[AUTONOMOUS LEARNER] Starting learning cycle #{self.total_cycles}"
        )

        # Step 1: Get knowledge gaps
        gaps = self_reflection.get_gaps()[:max_gaps]
        if not gaps:
            logger.info("[AUTONOMOUS LEARNER] No gaps to address")
            return {"status": "skipped", "reason": "no gaps"}

        results = {
            "cycle": self.total_cycles,
            "gaps_addressed": 0,
            "datasets_found": 0,
            "knowledge_added": 0,
            "training_pairs_added": 0,
            "details": [],
        }

        # Step 2: For each gap, search HF Hub for relevant datasets
        for gap in gaps:
            gap_topic = gap.get("topic", "")
            if not gap_topic:
                continue

            logger.info(f"[AUTONOMOUS LEARNER] Addressing gap: {gap_topic[:100]}")

            # Search for relevant datasets (lightweight API call)
            datasets = hf_dataset_searcher.search_for_gap(
                gap_topic, max_datasets_per_gap
            )
            results["datasets_found"] += len(datasets)

            if not datasets:
                logger.info(
                    f"[AUTONOMOUS LEARNER] No datasets found for: {gap_topic[:50]}"
                )
                continue

            # Step 3: Store dataset metadata as knowledge
            for ds_info in datasets:
                ds_name = ds_info.get("name", "")
                if not ds_name:
                    continue

                logger.info(f"[AUTONOMOUS LEARNER] Found dataset: {ds_name}")

                # Create knowledge entry from dataset metadata
                knowledge_entry = {
                    "text": f"Relevant dataset for {gap_topic}: {ds_name}. "
                    f"Description: {ds_info.get('description', 'N/A')[:200]}. "
                    f"Downloads: {ds_info.get('downloads', 0)}. "
                    f"Tags: {', '.join(ds_info.get('tags', [])[:5])}.",
                    "source": f"hf_dataset:{ds_name}",
                    "topic": gap_topic,
                    "timestamp": time.time(),
                    "confidence": ds_info.get("relevance_score", 0.5),
                }

                try:
                    knowledge_store.save_knowledge(knowledge_entry)
                    results["knowledge_added"] += 1
                    self.total_knowledge_added += 1
                except Exception as e:
                    logger.error(f"Failed to save knowledge: {e}")

                results["details"].append(
                    {
                        "gap": gap_topic[:100],
                        "dataset": ds_name,
                        "downloads": ds_info.get("downloads", 0),
                        "relevance": ds_info.get("relevance_score", 0),
                    }
                )

            results["gaps_addressed"] += 1

        # Step 4: Add conversation data to training dataset
        self._add_recent_conversations_to_training()

        elapsed = time.time() - start_time
        results["elapsed_seconds"] = round(elapsed, 1)
        results["status"] = "completed"

        self.last_learning_cycle = datetime.now(timezone.utc).isoformat()

        logger.info(
            f"[AUTONOMOUS LEARNER] Cycle #{self.total_cycles} complete in {elapsed:.1f}s: "
            f"{results['gaps_addressed']} gaps, {results['knowledge_added']} knowledge, "
            f"{results['training_pairs_added']} training pairs"
        )

        return results

    def _add_recent_conversations_to_training(self):
        """Add recent high-quality conversations to training dataset."""
        try:
            from app.services.case_store import list_cases

            recent_cases = list_cases(limit=10)
            for case in recent_cases:
                user_input = case.get("user_input", "")
                final = case.get("final", {})
                response = final.get("response", "")
                confidence = final.get("confidence", 0.5)
                sources = final.get("data_sources", [])

                if user_input and response and confidence >= 0.6:
                    fine_tuning_builder.add_conversation_pair(
                        user_input, response, confidence, sources
                    )

        except Exception as e:
            logger.error(f"Failed to add conversations to training: {e}")

    def get_status(self) -> Dict:
        """Get autonomous learner status."""
        return {
            "total_cycles": self.total_cycles,
            "total_knowledge_added": self.total_knowledge_added,
            "last_learning_cycle": self.last_learning_cycle,
            "fine_tuning_dataset": fine_tuning_builder.get_stats(),
        }


autonomous_learner = AutonomousLearner()
