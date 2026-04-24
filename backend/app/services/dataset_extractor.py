"""
Dataset Extractor for Janus.

Streams datasets from HF Hub, extracts facts and patterns,
converts to knowledge entries for the knowledge base.
"""

import json
import logging
import time
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class DatasetExtractor:
    """
    Extracts knowledge from HF datasets and converts to knowledge entries.
    Works with streaming datasets to avoid full downloads.
    """

    def __init__(self):
        self.extraction_stats = {
            "total_datasets_processed": 0,
            "total_entries_extracted": 0,
            "last_extraction": None,
        }

    def extract_facts_from_samples(self, samples: List[Dict], topic: str) -> List[Dict]:
        """
        Extract knowledge facts from dataset samples.

        Args:
            samples: List of dataset records
            topic: Topic for the extracted knowledge

        Returns:
            List of knowledge entry dicts
        """
        if not samples:
            return []

        facts = []
        for sample in samples:
            # Extract text fields
            text_fields = self._extract_text_fields(sample)
            for field_name, text in text_fields.items():
                if len(text) > 50:  # Only meaningful content
                    facts.append(
                        {
                            "text": text[:1000],
                            "source": f"dataset:{topic}",
                            "topic": topic,
                            "field": field_name,
                            "timestamp": time.time(),
                            "confidence": 0.7,  # Dataset quality varies
                        }
                    )

        self.extraction_stats["total_entries_extracted"] += len(facts)
        self.extraction_stats["total_datasets_processed"] += 1
        self.extraction_stats["last_extraction"] = time.time()

        logger.info(f"Extracted {len(facts)} facts from {topic} dataset")
        return facts

    def extract_instruction_pairs(self, samples: List[Dict]) -> List[Dict]:
        """
        Extract instruction-tuning pairs from dataset samples.

        Args:
            samples: List of dataset records

        Returns:
            List of {"instruction", "input", "output"} dicts
        """
        pairs = []

        for sample in samples:
            pair = self._convert_to_instruction_pair(sample)
            if pair:
                pairs.append(pair)

        logger.info(
            f"Extracted {len(pairs)} instruction pairs from {len(samples)} samples"
        )
        return pairs

    def _extract_text_fields(self, sample: Dict) -> Dict[str, str]:
        """Extract all text fields from a sample."""
        text_fields = {}

        for key, value in sample.items():
            if isinstance(value, str) and len(value) > 50:
                text_fields[key] = value
            elif isinstance(value, list):
                # Join list items if they're strings
                text_items = [str(item) for item in value if isinstance(item, str)]
                if text_items:
                    combined = " ".join(text_items)
                    if len(combined) > 50:
                        text_fields[key] = combined

        return text_fields

    def _convert_to_instruction_pair(self, sample: Dict) -> Optional[Dict]:
        """
        Convert a dataset sample to instruction-tuning format.
        Handles common dataset formats.
        """
        # Common field patterns for instruction tuning
        instruction_fields = ["instruction", "prompt", "question", "query", "input"]
        output_fields = ["output", "response", "answer", "completion", "target"]

        instruction = None
        output = None

        # Find instruction
        for field in instruction_fields:
            if (
                field in sample
                and isinstance(sample[field], str)
                and len(sample[field]) > 10
            ):
                instruction = sample[field]
                break

        # Find output
        for field in output_fields:
            if (
                field in sample
                and isinstance(sample[field], str)
                and len(sample[field]) > 10
            ):
                output = sample[field]
                break

        # Handle nested formats (e.g., conversations)
        if instruction is None and "conversations" in sample:
            convos = sample["conversations"]
            if isinstance(convos, list) and len(convos) >= 2:
                # First message is instruction, second is output
                if isinstance(convos[0], dict):
                    instruction = convos[0].get("value", "")
                if isinstance(convos[1], dict):
                    output = convos[1].get("value", "")

        # Handle Q&A format
        if instruction is None and "question" in sample:
            instruction = sample["question"]
            if "answer" in sample:
                output = sample["answer"]

        if instruction and output:
            return {
                "instruction": instruction[:2000],
                "input": "",
                "output": output[:2000],
                "source": "dataset_extract",
            }

        return None

    def get_extraction_stats(self) -> Dict:
        """Get extraction statistics."""
        return self.extraction_stats.copy()


dataset_extractor = DatasetExtractor()
