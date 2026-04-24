"""
Learning Filter for MiroOrg v2.

Decides whether to learn from a query based on its type.
Never learns from GENERIC queries (definitions, simple facts).
Always learns from SPECIFIC queries (reasoning, analysis).
Conditionally learns from HYBRID queries.
"""

from typing import Tuple
from app.services.query_classifier import QueryType


class LearningFilter:
    """Filters which queries should contribute to learning."""

    def should_learn(
        self,
        query_type: QueryType,
        query: str,
        answer: str,
        domain: str,
        metadata: dict = None,
    ) -> Tuple[bool, str]:
        """
        Determine if this query should be learned from.

        Returns:
            Tuple of (should_learn, reason)
        """
        metadata = metadata or {}

        # Never learn from generic queries
        if query_type == QueryType.GENERIC:
            return False, "Generic/trivial query — definition lookup only"

        # Always learn from specific domain queries
        if query_type == QueryType.SPECIFIC:
            if domain != "general":
                return True, f"Specific domain ({domain}) query with reasoning"
            # Even general-specific queries are worth learning if they required reasoning
            if metadata.get("reasoning_required", False):
                return True, "Specific query requiring reasoning"
            return False, "Specific but trivial — no reasoning required"

        # Hybrid: learn if domain-specific or reasoning-heavy
        if query_type == QueryType.HYBRID:
            if domain != "general":
                return True, f"Hybrid query with domain ({domain}) context"
            if metadata.get("specific_score", 0) >= 2:
                return True, "Hybrid query with strong reasoning component"
            return False, "Hybrid query leans generic — skip learning"

        return False, "Unknown query type"
