"""
Adaptive Intelligence Engine for MiroOrg v2.

This is the system's "meta-brain" — it learns from ALL past cases to:
1. Determine optimal pipeline depth per query type
2. Build domain expertise that accumulates over time
3. Recognize cross-case patterns no single query reveals
4. Develop a consistent analytical personality

This is what makes MiroOrg genuinely unique — it doesn't just answer questions,
it builds institutional intelligence that compounds with every interaction.
"""

import json
import os
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
from collections import defaultdict

DATA_DIR = Path(__file__).parent.parent / "data" / "adaptive"
DATA_DIR.mkdir(parents=True, exist_ok=True)


class DomainExpertise:
    """Tracks and accumulates domain expertise over time."""

    def __init__(self, domain: str):
        self.domain = domain
        self.case_count = 0
        self.success_rate = 0.0
        self.key_entities: Dict[str, int] = defaultdict(int)
        self.common_patterns: Dict[str, int] = defaultdict(int)
        self.trusted_sources: Dict[str, float] = defaultdict(lambda: 0.5)
        self.typical_confidence = 0.5
        self.last_updated = time.time()

    def update_from_case(self, case: Dict) -> None:
        """Absorb learning from a completed case."""
        self.case_count += 1

        # Update success rate (exponential moving average)
        final = case.get("final", {})
        confidence = final.get("confidence", 0.5)
        alpha = 0.3  # Learning rate
        self.success_rate = alpha * confidence + (1 - alpha) * self.success_rate
        self.typical_confidence = (
            alpha * confidence + (1 - alpha) * self.typical_confidence
        )

        # Extract entities from research
        research = case.get("research", {})
        for fact in research.get("key_facts", []):
            # Simple entity extraction - capitalized words
            words = fact.split()
            for word in words:
                cleaned = word.strip(".,;:()\"'")
                if cleaned and cleaned[0].isupper() and len(cleaned) > 2:
                    self.key_entities[cleaned] += 1

        # Track patterns from route
        route = case.get("route", {})
        complexity = route.get("complexity", "medium")
        self.common_patterns[f"complexity:{complexity}"] += 1

        # Update source trust
        for source in research.get("sources", []):
            source_name = (
                source.split("://")[-1].split("/")[0] if "://" in source else source
            )
            if source_name:
                current = self.trusted_sources[source_name]
                self.trusted_sources[source_name] = current + 0.05 * (
                    confidence - current
                )

        self.last_updated = time.time()

    def get_expertise_summary(self) -> Dict:
        """Get a summary of domain expertise for prompt enrichment."""
        top_entities = sorted(
            self.key_entities.items(), key=lambda x: x[1], reverse=True
        )[:10]
        top_sources = sorted(
            self.trusted_sources.items(), key=lambda x: x[1], reverse=True
        )[:5]

        return {
            "domain": self.domain,
            "case_count": self.case_count,
            "success_rate": round(self.success_rate, 2),
            "typical_confidence": round(self.typical_confidence, 2),
            "key_entities": [e for e, _ in top_entities],
            "trusted_sources": [
                {"source": s, "trust": round(t, 2)} for s, t in top_sources
            ],
            "common_patterns": dict(self.common_patterns),
        }

    def to_dict(self) -> Dict:
        return {
            "domain": self.domain,
            "case_count": self.case_count,
            "success_rate": self.success_rate,
            "key_entities": dict(self.key_entities),
            "common_patterns": dict(self.common_patterns),
            "trusted_sources": dict(self.trusted_sources),
            "typical_confidence": self.typical_confidence,
            "last_updated": self.last_updated,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "DomainExpertise":
        expertise = cls(data["domain"])
        expertise.case_count = data.get("case_count", 0)
        expertise.success_rate = data.get("success_rate", 0.0)
        expertise.key_entities = defaultdict(int, data.get("key_entities", {}))
        expertise.common_patterns = defaultdict(int, data.get("common_patterns", {}))
        expertise.trusted_sources = defaultdict(
            lambda: 0.5, data.get("trusted_sources", {})
        )
        expertise.typical_confidence = data.get("typical_confidence", 0.5)
        expertise.last_updated = data.get("last_updated", time.time())
        return expertise


class CrossCasePatternRecognizer:
    """Finds patterns across ALL cases that no single query reveals."""

    def __init__(self):
        self.domain_cooccurrence: Dict[str, Dict[str, int]] = defaultdict(
            lambda: defaultdict(int)
        )
        self.query_complexity_trend: List[Dict] = []
        self.source_effectiveness: Dict[str, Dict[str, float]] = defaultdict(
            lambda: {"hits": 0, "total": 0}
        )
        self.time_patterns: Dict[str, List[float]] = defaultdict(list)

    def update_from_case(self, case: Dict, elapsed: float) -> None:
        """Absorb case into pattern recognition."""
        route = case.get("route", {})
        domain = route.get("domain", "general")
        complexity = route.get("complexity", "medium")

        # Track complexity trends
        self.query_complexity_trend.append(
            {
                "domain": domain,
                "complexity": complexity,
                "timestamp": time.time(),
            }
        )

        # Track time patterns
        self.time_patterns[domain].append(elapsed)

        # Track source effectiveness
        research = case.get("research", {})
        final = case.get("final", {})
        confidence = final.get("confidence", 0.5)

        for source in research.get("sources", []):
            source_name = (
                source.split("://")[-1].split("/")[0] if "://" in source else source
            )
            if source_name:
                self.source_effectiveness[source_name]["hits"] += (
                    1 if confidence > 0.7 else 0
                )
                self.source_effectiveness[source_name]["total"] += 1

    def get_insights(self) -> Dict:
        """Get cross-case insights."""
        # Most effective sources
        effective_sources = {}
        for source, stats in self.source_effectiveness.items():
            if stats["total"] >= 2:
                effective_sources[source] = round(stats["hits"] / stats["total"], 2)

        # Average response times by domain
        avg_times = {}
        for domain, times in self.time_patterns.items():
            if times:
                avg_times[domain] = round(sum(times) / len(times), 1)

        # Recent complexity distribution
        recent = self.query_complexity_trend[-50:]
        complexity_dist = defaultdict(int)
        for q in recent:
            complexity_dist[q["complexity"]] += 1

        return {
            "effective_sources": effective_sources,
            "avg_response_times": avg_times,
            "complexity_distribution": dict(complexity_dist),
            "total_cases_analyzed": len(self.query_complexity_trend),
        }

    def to_dict(self) -> Dict:
        return {
            "domain_cooccurrence": {
                k: dict(v) for k, v in self.domain_cooccurrence.items()
            },
            "query_complexity_trend": self.query_complexity_trend[
                -100:
            ],  # Keep last 100
            "source_effectiveness": dict(self.source_effectiveness),
            "time_patterns": {
                k: v[-50:] for k, v in self.time_patterns.items()
            },  # Keep last 50 per domain
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "CrossCasePatternRecognizer":
        recognizer = cls()
        cooc = data.get("domain_cooccurrence", {})
        for k, v in cooc.items():
            for k2, v2 in v.items():
                recognizer.domain_cooccurrence[k][k2] = v2
        recognizer.query_complexity_trend = data.get("query_complexity_trend", [])
        se = data.get("source_effectiveness", {})
        for k, v in se.items():
            recognizer.source_effectiveness[k] = v
        tp = data.get("time_patterns", {})
        for k, v in tp.items():
            recognizer.time_patterns[k] = v
        return recognizer


class AdaptiveIntelligence:
    """The meta-brain of MiroOrg — learns, adapts, and accumulates intelligence."""

    def __init__(self, data_dir: Path = DATA_DIR):
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.domain_expertise: Dict[str, DomainExpertise] = {}
        self.pattern_recognizer = CrossCasePatternRecognizer()
        self.system_personality = {
            "analytical_depth": 0.7,  # How deep the analysis goes (0-1)
            "confidence_threshold": 0.6,  # Minimum confidence to state something as fact
            "skepticism_level": 0.3,  # How skeptical of unverified claims (0-1)
            "actionability_focus": 0.8,  # How much to focus on actionable insights (0-1)
        }
        self.total_cases = 0
        self._load()

    def _load(self) -> None:
        """Load persisted intelligence."""
        expertise_file = self.data_dir / "domain_expertise.json"
        if expertise_file.exists():
            try:
                with open(expertise_file) as f:
                    data = json.load(f)
                for domain_data in data:
                    expertise = DomainExpertise.from_dict(domain_data)
                    self.domain_expertise[expertise.domain] = expertise
            except Exception:
                pass

        patterns_file = self.data_dir / "patterns.json"
        if patterns_file.exists():
            try:
                with open(patterns_file) as f:
                    data = json.load(f)
                self.pattern_recognizer = CrossCasePatternRecognizer.from_dict(data)
            except Exception:
                pass

        personality_file = self.data_dir / "personality.json"
        if personality_file.exists():
            try:
                with open(personality_file) as f:
                    self.system_personality = json.load(f)
            except Exception:
                pass

        meta_file = self.data_dir / "meta.json"
        if meta_file.exists():
            try:
                with open(meta_file) as f:
                    meta = json.load(f)
                self.total_cases = meta.get("total_cases", 0)
            except Exception:
                pass

    def _save(self) -> None:
        """Persist intelligence to disk."""
        try:
            with open(self.data_dir / "domain_expertise.json", "w") as f:
                json.dump(
                    [e.to_dict() for e in self.domain_expertise.values()], f, indent=2
                )

            with open(self.data_dir / "patterns.json", "w") as f:
                json.dump(self.pattern_recognizer.to_dict(), f, indent=2)

            with open(self.data_dir / "personality.json", "w") as f:
                json.dump(self.system_personality, f, indent=2)

            with open(self.data_dir / "meta.json", "w") as f:
                json.dump({"total_cases": self.total_cases}, f, indent=2)
        except Exception as e:
            import logging

            logging.getLogger(__name__).error(
                f"Failed to save adaptive intelligence: {e}"
            )

    def learn_from_case(self, case: Dict, elapsed: float) -> None:
        """Absorb a completed case into the system's intelligence."""
        self.total_cases += 1

        route = case.get("route", {})
        domain = route.get("domain", "general")

        # Update domain expertise
        if domain not in self.domain_expertise:
            self.domain_expertise[domain] = DomainExpertise(domain)
        self.domain_expertise[domain].update_from_case(case)

        # Update cross-case patterns
        self.pattern_recognizer.update_from_case(case, elapsed)

        # Adapt system personality based on accumulated experience
        self._adapt_personality()

        # Save every 5 cases
        if self.total_cases % 5 == 0:
            self._save()

    def _adapt_personality(self) -> None:
        """Adapt system personality based on accumulated experience."""
        if self.total_cases < 10:
            return  # Need more data

        # Calculate overall system confidence
        all_confidences = []
        for expertise in self.domain_expertise.values():
            if expertise.case_count > 0:
                all_confidences.append(expertise.success_rate)

        if not all_confidences:
            return

        avg_confidence = sum(all_confidences) / len(all_confidences)

        # If system is consistently confident, increase analytical depth
        if avg_confidence > 0.75:
            self.system_personality["analytical_depth"] = min(
                0.95, self.system_personality["analytical_depth"] + 0.02
            )
        elif avg_confidence < 0.5:
            self.system_personality["analytical_depth"] = max(
                0.4, self.system_personality["analytical_depth"] - 0.02
            )
            self.system_personality["skepticism_level"] = min(
                0.7, self.system_personality["skepticism_level"] + 0.02
            )

    def get_context_for_query(self, query: str, domain: str) -> Dict:
        """Get accumulated intelligence context for a new query."""
        context = {
            "system_personality": self.system_personality,
            "total_cases_learned": self.total_cases,
        }

        # Add domain expertise if available
        if domain in self.domain_expertise:
            expertise = self.domain_expertise[domain]
            context["domain_expertise"] = expertise.get_expertise_summary()

        # Add cross-case insights
        context["cross_case_insights"] = self.pattern_recognizer.get_insights()

        return context

    def get_full_intelligence_report(self) -> Dict:
        """Get complete intelligence report."""
        return {
            "total_cases": self.total_cases,
            "system_personality": self.system_personality,
            "domain_expertise": {
                domain: expertise.get_expertise_summary()
                for domain, expertise in self.domain_expertise.items()
            },
            "cross_case_insights": self.pattern_recognizer.get_insights(),
        }

    def save(self) -> None:
        """Force save."""
        self._save()


# Global instance
adaptive_intelligence = AdaptiveIntelligence()
