"""
Example curator for Janus self-improvement.

Filters traces by quality score, buckets by domain/query_type,
and prepares curated examples for training.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent.parent.parent / "data" / "curation"
CURATED_FILE = DATA_DIR / "curated_examples.jsonl"
REJECTED_FILE = DATA_DIR / "rejected_examples.jsonl"

QUALITY_THRESHOLD = 0.7


class ExampleCurator:
    def __init__(self):
        self._init_dirs()

    def _init_dirs(self):
        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.error(f"Failed to create curation dir: {e}")

    def curate_trace(self, trace: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate a trace and decide whether to keep or reject it."""
        score = trace.get("score", 0.0)
        is_curated = score >= QUALITY_THRESHOLD
        has_errors = bool(trace.get("errors", []))
        output_len = trace.get("output_length", 0)

        if has_errors:
            is_curated = False
        if output_len < 20:
            is_curated = False

        decision = {
            "trace_id": trace.get("trace_id"),
            "score": score,
            "is_curated": is_curated,
            "reason": self._get_reason(score, has_errors, output_len),
            "domain": trace.get("domain"),
            "query_type": trace.get("query_type"),
        }

        if is_curated:
            self._save_example(trace, CURATED_FILE)
        else:
            self._save_example(trace, REJECTED_FILE)

        return decision

    def _get_reason(self, score: float, has_errors: bool, output_len: int) -> str:
        if has_errors:
            return "has_errors"
        if output_len < 20:
            return "output_too_short"
        if score >= 0.9:
            return "excellent"
        if score >= QUALITY_THRESHOLD:
            return "good"
        return "below_threshold"

    def _save_example(self, trace: Dict[str, Any], filepath: Path):
        """Append example to JSONL file."""
        try:
            example = {
                "trace_id": trace.get("trace_id"),
                "query": trace.get("query", ""),
                "query_type": trace.get("query_type"),
                "domain": trace.get("domain"),
                "output": trace.get("output", ""),
                "score": trace.get("score", 0.0),
                "score_breakdown": trace.get("score_breakdown", {}),
                "routing_path": trace.get("routing_path"),
                "latency_ms": trace.get("latency_ms", 0),
                "confidence": trace.get("confidence", 0.5),
                "cached": trace.get("cached", False),
                "tool_results": trace.get("tool_results", []),
                "curated_at": datetime.utcnow().isoformat(),
            }
            with open(filepath, "a") as f:
                f.write(json.dumps(example) + "\n")
        except Exception as e:
            logger.error(f"Failed to save example: {e}")

    def get_curated_examples(
        self,
        limit: int = 50,
        domain: Optional[str] = None,
        query_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get curated examples with optional filters."""
        examples = []
        if not CURATED_FILE.exists():
            return examples

        try:
            with open(CURATED_FILE) as f:
                for line in f:
                    if line.strip():
                        examples.append(json.loads(line))

            if domain:
                examples = [e for e in examples if e.get("domain") == domain]
            if query_type:
                examples = [e for e in examples if e.get("query_type") == query_type]

            return examples[-limit:]
        except Exception as e:
            logger.error(f"Failed to read curated examples: {e}")
            return []

    def get_stats(self) -> Dict[str, Any]:
        """Get curation statistics."""
        curated_count = 0
        rejected_count = 0
        by_domain = {}
        by_query_type = {}

        if CURATED_FILE.exists():
            try:
                with open(CURATED_FILE) as f:
                    for line in f:
                        if line.strip():
                            curated_count += 1
                            example = json.loads(line)
                            domain = example.get("domain", "unknown")
                            query_type = example.get("query_type", "unknown")
                            by_domain[domain] = by_domain.get(domain, 0) + 1
                            by_query_type[query_type] = (
                                by_query_type.get(query_type, 0) + 1
                            )
            except Exception as e:
                logger.error(f"Failed to read curated file: {e}")

        if REJECTED_FILE.exists():
            try:
                with open(REJECTED_FILE) as f:
                    for line in f:
                        if line.strip():
                            rejected_count += 1
            except Exception as e:
                logger.error(f"Failed to read rejected file: {e}")

        return {
            "curated_count": curated_count,
            "rejected_count": rejected_count,
            "quality_threshold": QUALITY_THRESHOLD,
            "by_domain": by_domain,
            "by_query_type": by_query_type,
            "ready_for_training": curated_count >= 200,
        }
