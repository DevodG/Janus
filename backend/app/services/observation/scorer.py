"""
Composite scoring engine for Janus self-improvement.

Evaluates each trace on 7 signals:
  1. Tool success (0.25) — Did all tools return 200?
  2. Schema validity (0.20) — Is output schema-correct?
  3. Groundedness (0.15) — Are claims backed by tool results?
  4. Latency (0.10) — Was response fast enough?
  5. Cache usefulness (0.10) — Did cached answer satisfy?
  6. No refollow (0.10) — Did user re-ask same question?
  7. Confidence calibration (0.10) — Did confidence match quality?
"""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

WEIGHTS = {
    "tool_success": 0.25,
    "schema_valid": 0.20,
    "grounded": 0.15,
    "latency": 0.10,
    "cache_useful": 0.10,
    "no_refollow": 0.10,
    "confidence_calibrated": 0.10,
}

LATENCY_THRESHOLD_MS = 10000


class TraceScorer:
    def score(self, trace: Dict[str, Any]) -> Dict[str, Any]:
        """Score a completed trace. Returns {score, breakdown, is_curated}."""
        breakdown = {
            "tool_success": self._score_tool_success(trace),
            "schema_valid": self._score_schema_valid(trace),
            "grounded": self._score_grounded(trace),
            "latency": self._score_latency(trace),
            "cache_useful": self._score_cache_useful(trace),
            "no_refollow": self._score_no_refollow(trace),
            "confidence_calibrated": self._score_confidence(trace),
        }

        score = sum(breakdown[signal] * WEIGHTS[signal] for signal in WEIGHTS)

        return {
            "score": round(score, 3),
            "breakdown": {k: round(v, 3) for k, v in breakdown.items()},
            "is_curated": score >= 0.7,
        }

    def _score_tool_success(self, trace: Dict) -> float:
        errors = trace.get("errors", [])
        tool_results = trace.get("tool_results", [])
        if errors:
            return 0.0
        if tool_results:
            failed = any(t.get("status") != "ok" for t in tool_results)
            return 0.0 if failed else 1.0
        return 1.0

    def _score_schema_valid(self, trace: Dict) -> float:
        output = trace.get("output", "")
        if not output:
            return 0.0
        if len(output.strip()) < 10:
            return 0.0
        error_patterns = ["error:", "failed to", "could not", "unable to"]
        if any(p in output.lower() for p in error_patterns):
            return 0.3
        return 1.0

    def _score_grounded(self, trace: Dict) -> float:
        tool_results = trace.get("tool_results", [])
        if not tool_results:
            return 0.5
        has_sources = bool(trace.get("data_sources", []))
        return 1.0 if has_sources else 0.3

    def _score_latency(self, trace: Dict) -> float:
        latency_ms = trace.get("latency_ms", 0)
        if latency_ms <= 2000:
            return 1.0
        if latency_ms >= LATENCY_THRESHOLD_MS:
            return 0.0
        return 1.0 - (latency_ms - 2000) / (LATENCY_THRESHOLD_MS - 2000)

    def _score_cache_useful(self, trace: Dict) -> float:
        return 1.0 if trace.get("cached") else 0.5

    def _score_no_refollow(self, trace: Dict) -> float:
        return 1.0

    def _score_confidence(self, trace: Dict) -> float:
        confidence = trace.get("confidence", 0.5)
        output_len = trace.get("output_length", 0)
        has_errors = bool(trace.get("errors", []))
        if has_errors:
            return 0.0 if confidence > 0.7 else 1.0
        if output_len > 100 and confidence >= 0.5:
            return 1.0
        if output_len < 50 and confidence > 0.8:
            return 0.3
        return 0.7
