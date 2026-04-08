"""
Domain Classifier for Janus Self-Improvement System.

Classifies queries into specific domains to enable:
1. Domain-specific model routing
2. Specialized prompt selection
3. Targeted knowledge retrieval
4. Expert system activation
"""

import re
import logging
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

# Import existing domain packs
try:
    from app.domain_packs import registry as domain_registry

    DOMAIN_PACKS_AVAILABLE = True
except ImportError:
    DOMAIN_PACKS_AVAILABLE = False
    logger.warning("Domain packs not available, using fallback classification")


class DomainType(Enum):
    """Supported domain types for classification."""

    FINANCE = "finance"
    TECHNOLOGY = "technology"
    HEALTHCARE = "healthcare"
    POLICY = "policy"
    SCIENCE = "science"
    GEOPOLITICS = "geopolitics"
    ENERGY = "energy"
    CRITICAL_THINKING = "critical_thinking"
    EMOTIONAL_INTELLIGENCE = "emotional_intelligence"
    PHILOSOPHY = "philosophy"
    BUSINESS = "business"
    EDUCATION = "education"
    GENERAL = "general"


@dataclass
class DomainClassification:
    """Result of domain classification."""

    domain: DomainType
    confidence: float
    keywords_found: List[str]
    reasoning: str


class DomainClassifier:
    """
    Classifies user queries into specific domains for improved routing
    and specialized processing.
    """

    def __init__(self):
        """Initialize the domain classifier."""
        self.domain_keywords = self._load_domain_keywords()
        self.compiled_patterns = self._compile_domain_patterns()

    def _load_domain_keywords(self) -> Dict[DomainType, List[str]]:
        """Load domain-specific keywords from domain packs or fallback."""
        if DOMAIN_PACKS_AVAILABLE:
            return self._load_from_domain_packs()
        else:
            return self._load_fallback_keywords()

    def _load_from_domain_packs(self) -> Dict[DomainType, List[str]]:
        """Load keywords from existing domain packs."""
        keywords = {}

        # Map domain pack names to our DomainType enum
        domain_mapping = {
            "finance": DomainType.FINANCE,
            "technology": DomainType.TECHNOLOGY,
            "healthcare": DomainType.HEALTHCARE,
            "policy": DomainType.POLICY,
            "science": DomainType.SCIENCE,
            "geopolitics": DomainType.GEOPOLITICS,
            "energy": DomainType.ENERGY,
            "critical_thinking": DomainType.CRITICAL_THINKING,
            "emotional_intelligence": DomainType.EMOTIONAL_INTELLIGENCE,
            "philosophy": DomainType.PHILOSOPHY,
            "business": DomainType.BUSINESS,
            "education": DomainType.EDUCATION,
        }

        try:
            registry = domain_registry.get_registry()
        except Exception as e:
            logger.warning(f"Could not get domain registry: {e}")
            registry = None

        for pack_name, domain_type in domain_mapping.items():
            try:
                if registry is not None:
                    pack = registry.get_pack(pack_name)
                else:
                    pack = None

                if pack and hasattr(pack, "get_keywords"):
                    keywords[domain_type] = pack.get_keywords()
                elif pack and hasattr(pack, "DOMAIN_KEYWORDS"):
                    keywords[domain_type] = pack.DOMAIN_KEYWORDS
                else:
                    # Fallback to empty list if no keywords method
                    keywords[domain_type] = []
            except Exception as e:
                logger.warning(f"Could not load keywords for {pack_name}: {e}")
                keywords[domain_type] = []

        # Always include general domain
        keywords[DomainType.GENERAL] = []

        return keywords

    def _load_fallback_keywords(self) -> Dict[DomainType, List[str]]:
        """Load fallback keyword definitions."""
        # Import from query_classifier as fallback
        try:
            from app.services.query_classifier import DOMAIN_KEYWORDS

            keywords = {}
            for domain_str, word_list in DOMAIN_KEYWORDS.items():
                try:
                    domain_type = DomainType(domain_str)
                    keywords[domain_type] = word_list
                except ValueError:
                    # Skip domains not in our enum
                    continue
            keywords[DomainType.GENERAL] = []
            return keywords
        except ImportError:
            # Ultimate fallback - minimal keyword sets
            logger.warning("Using ultimate fallback domain keywords")
            return {
                DomainType.FINANCE: [
                    "stock",
                    "market",
                    "investment",
                    "trading",
                    "finance",
                    "economic",
                ],
                DomainType.TECHNOLOGY: [
                    "ai",
                    "software",
                    "technology",
                    "programming",
                    "computer",
                ],
                DomainType.HEALTHCARE: [
                    "health",
                    "medical",
                    "disease",
                    "treatment",
                    "healthcare",
                ],
                DomainType.POLICY: [
                    "policy",
                    "government",
                    "law",
                    "regulation",
                    "politics",
                ],
                DomainType.SCIENCE: [
                    "science",
                    "research",
                    "study",
                    "experiment",
                    "theory",
                ],
                DomainType.GEOPOLITICS: [
                    "war",
                    "conflict",
                    "country",
                    "international",
                    "diplomacy",
                ],
                DomainType.ENERGY: [
                    "energy",
                    "power",
                    "electricity",
                    "oil",
                    "gas",
                    "renewable",
                ],
                DomainType.CRITICAL_THINKING: [
                    "analyze",
                    "evaluate",
                    "critique",
                    "assess",
                    "reason",
                ],
                DomainType.EMOTIONAL_INTELLIGENCE: [
                    "feel",
                    "emotion",
                    "relationship",
                    "communication",
                ],
                DomainType.PHILOSOPHY: [
                    "ethics",
                    "meaning",
                    "purpose",
                    "existence",
                    "consciousness",
                ],
                DomainType.BUSINESS: [
                    "business",
                    "company",
                    "management",
                    "strategy",
                    "marketing",
                ],
                DomainType.EDUCATION: [
                    "learn",
                    "education",
                    "study",
                    "teach",
                    "student",
                ],
                DomainType.GENERAL: [],
            }

    def _compile_domain_patterns(self) -> Dict[DomainType, List[re.Pattern]]:
        """Compile regex patterns for each domain."""
        patterns = {}
        for domain, keywords in self.domain_keywords.items():
            domain_patterns = []
            for keyword in keywords:
                # Create word boundary pattern for accurate matching
                pattern = re.compile(rf"\b{re.escape(keyword)}\b", re.IGNORECASE)
                domain_patterns.append(pattern)
            patterns[domain] = domain_patterns
        return patterns

    def classify(self, query: str) -> DomainClassification:
        """
        Classify a query into a domain.

        Args:
            query: User query string

        Returns:
            DomainClassification with domain, confidence, and details
        """
        query_lower = query.lower().strip()

        # Score each domain
        domain_scores = {}
        matched_keywords = {}

        for domain, patterns in self.compiled_patterns.items():
            score = 0
            matched = []

            for pattern in patterns:
                matches = pattern.findall(query_lower)
                if matches:
                    score += len(matches)
                    matched.extend(matches)

            if score > 0:
                domain_scores[domain] = score
                matched_keywords[domain] = list(set(matched))  # Remove duplicates

        # Determine domain
        if not domain_scores:
            # No domain keywords found - default to general
            domain_scores[DomainType.GENERAL] = 1
            matched_keywords[DomainType.GENERAL] = []
            detected_domain = DomainType.GENERAL
            confidence = 0.5  # Low confidence for default
            reasoning = "No domain-specific keywords found"
        else:
            # Find domain with highest score
            detected_domain = max(domain_scores, key=domain_scores.get)
            max_score = domain_scores[detected_domain]

            # Calculate confidence based on score relative to query length
            query_word_count = max(len(query.split()), 1)
            raw_confidence = min(max_score / (query_word_count * 0.5), 1.0)  # Normalize

            # Boost confidence if we found multiple keyword matches
            keyword_bonus = min(len(matched_keywords[detected_domain]) * 0.1, 0.3)
            confidence = min(raw_confidence + keyword_bonus, 0.95)

            # Ensure minimum confidence for detected domain
            confidence = max(confidence, 0.6)

            reasoning = f"Found {max_score} keyword matches for {detected_domain.value}"

        return DomainClassification(
            domain=detected_domain,
            confidence=confidence,
            keywords_found=matched_keywords.get(detected_domain, []),
            reasoning=reasoning,
        )

    def get_domain_confidence(self, query: str, domain: DomainType) -> float:
        """
        Get confidence score for a specific domain.

        Args:
            query: User query string
            domain: Domain to check confidence for

        Returns:
            Confidence score between 0.0 and 1.0
        """
        classification = self.classify(query)
        if classification.domain == domain:
            return classification.confidence
        else:
            # Return inverse confidence for other domains
            return max(0.0, 1.0 - classification.confidence)

    def get_top_domains(
        self, query: str, top_n: int = 3
    ) -> List[Tuple[DomainType, float]]:
        """
        Get top N domain classifications for a query.

        Args:
            query: User query string
            top_n: Number of top domains to return

        Returns:
            List of (domain, confidence) tuples sorted by confidence
        """
        query_lower = query.lower().strip()
        domain_scores = {}

        # Score each domain
        for domain, patterns in self.compiled_patterns.items():
            score = 0
            for pattern in patterns:
                matches = pattern.findall(query_lower)
                score += len(matches)

            if score > 0:
                domain_scores[domain] = score

        if not domain_scores:
            return [(DomainType.GENERAL, 0.5)]

        # Sort by score and normalize to confidence
        sorted_domains = sorted(domain_scores.items(), key=lambda x: x[1], reverse=True)
        max_score = sorted_domains[0][1] if sorted_domains else 1

        results = []
        for domain, score in sorted_domains[:top_n]:
            # Normalize score to 0-1 range with minimum confidence
            confidence = max(0.5, min(score / (max_score * 0.5), 0.95))
            results.append((domain, confidence))

        return results


# Global instance for easy access
domain_classifier = DomainClassifier()
