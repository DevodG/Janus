"""
Adaptive Pipeline — Dynamic query routing for Janus.
Routes queries based on complexity to optimize response time.

Generic (definitions, facts) → Cache or direct model call (5-10s)
Simple (single-domain)       → Research only, skip deep synthesis (30-60s)
Complex (multi-domain)       → Full pipeline with simulation (2-4min)
"""

import logging
import time
from typing import Dict, Any, Optional
from app.services.query_classifier import QueryClassifier, QueryType
from app.agents import switchboard, research, synthesizer
from app.agents import mirofish_node, finance_node

logger = logging.getLogger(__name__)


class AdaptivePipeline:
    def __init__(self):
        self.classifier = QueryClassifier()
        self.stats = {
            "generic": {"count": 0, "total_time": 0},
            "simple": {"count": 0, "total_time": 0},
            "complex": {"count": 0, "total_time": 0},
        }

    def run(self, user_input: str) -> Dict[str, Any]:
        """Run the adaptive pipeline on user input."""
        query_type, confidence, meta = self.classifier.classify(user_input)
        domain = meta.get("detected_domain", "general")

        logger.info(f"[PIPELINE] Query: {user_input[:80]}...")
        logger.info(
            f"[PIPELINE] Type: {query_type.value}, Domain: {domain}, Confidence: {confidence:.2f}"
        )

        t0 = time.perf_counter()

        if query_type == QueryType.GENERIC:
            result = self._run_generic(user_input, domain, meta)
        elif query_type == QueryType.SPECIFIC:
            result = self._run_specific(user_input, domain, meta)
        else:  # HYBRID
            result = self._run_complex(user_input, domain, meta)

        elapsed = time.perf_counter() - t0
        result["elapsed_seconds"] = round(elapsed, 1)
        result["query_type"] = query_type.value
        result["domain"] = domain

        # Update stats
        key = query_type.value
        if key in self.stats:
            self.stats[key]["count"] += 1
            self.stats[key]["total_time"] += elapsed

        logger.info(f"[PIPELINE] Completed in {elapsed:.1f}s")
        return result

    def _run_generic(self, user_input: str, domain: str, meta: Dict) -> Dict:
        """Generic query — fast path."""
        logger.info("[PIPELINE] Generic path — fast response")

        # Route through switchboard for classification
        state = {
            "user_input": user_input,
            "route": {},
            "research": {},
            "final": {},
        }

        route = switchboard.run(state)
        state.update(route)

        # Direct research → synthesis (skip simulation/finance)
        research_result = research.run(state)
        state.update(research_result)

        synthesis = synthesizer.run(state)
        state.update(synthesis)

        final = state.get("final", {})
        return {
            "user_input": user_input,
            "route": state.get("route", {}),
            "research": state.get("research", {}),
            "final": final,
            "final_answer": final.get("response", final.get("summary", "")),
            "pipeline_depth": "generic",
        }

    def _run_specific(self, user_input: str, domain: str, meta: Dict) -> Dict:
        """Specific query — medium path with domain enhancement."""
        logger.info(f"[PIPELINE] Specific path — domain: {domain}")

        state = {
            "user_input": user_input,
            "route": {},
            "research": {},
            "final": {},
        }

        # Route through switchboard
        route = switchboard.run(state)
        state.update(route)

        # Run finance if domain requires it
        if domain == "finance" or route.get("route", {}).get("requires_finance_data"):
            finance_result = finance_node.run(state)
            state.update(finance_result)

        # Research with domain context
        research_result = research.run(state)
        state.update(research_result)

        # Synthesis
        synthesis = synthesizer.run(state)
        state.update(synthesis)

        final = state.get("final", {})
        return {
            "user_input": user_input,
            "route": state.get("route", {}),
            "research": state.get("research", {}),
            "finance": state.get("finance"),
            "final": final,
            "final_answer": final.get("response", final.get("summary", "")),
            "pipeline_depth": "specific",
        }

    def _run_complex(self, user_input: str, domain: str, meta: Dict) -> Dict:
        """Complex query — full pipeline with simulation."""
        logger.info(f"[PIPELINE] Complex path — full pipeline")

        state = {
            "user_input": user_input,
            "route": {},
            "research": {},
            "final": {},
        }

        # Route through switchboard
        route = switchboard.run(state)
        state.update(route)

        route_data = state.get("route", {})

        # Run simulation if required
        if route_data.get("requires_simulation"):
            sim_result = mirofish_node.run(state)
            state.update(sim_result)

        # Run finance if required
        if route_data.get("requires_finance_data"):
            finance_result = finance_node.run(state)
            state.update(finance_result)

        # Research with full context
        research_result = research.run(state)
        state.update(research_result)

        # Synthesis
        synthesis = synthesizer.run(state)
        state.update(synthesis)

        final = state.get("final", {})
        return {
            "user_input": user_input,
            "route": state.get("route", {}),
            "research": state.get("research", {}),
            "simulation": state.get("simulation"),
            "finance": state.get("finance"),
            "final": final,
            "final_answer": final.get("response", final.get("summary", "")),
            "pipeline_depth": "complex",
        }

    def get_stats(self) -> Dict:
        """Get pipeline statistics."""
        stats = {}
        for key, data in self.stats.items():
            count = data["count"]
            total = data["total_time"]
            stats[key] = {
                "count": count,
                "total_time": round(total, 1),
                "avg_time": round(total / count, 1) if count > 0 else 0,
            }
        return stats


# Global instance
adaptive_pipeline = AdaptivePipeline()
