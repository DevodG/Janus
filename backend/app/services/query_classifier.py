"""
Query Classifier for MiroOrg v2.

Classifies user queries into three types:
- GENERIC: Definition lookups, simple facts ("What is X?", "Define Y")
- SPECIFIC: Complex reasoning, domain-specific analysis ("Should I invest in Tesla?")
- HYBRID: Mix of both ("What is machine learning and should I use it?")
"""

import re
from enum import Enum
from typing import Dict, Tuple


class QueryType(Enum):
    GENERIC = "generic"
    SPECIFIC = "specific"
    HYBRID = "hybrid"


# Generic patterns - definition/fact lookups
GENERIC_PATTERNS = [
    r"^what\s+is\s+",
    r"^define\s+",
    r"^who\s+is\s+",
    r"^where\s+is\s+",
    r"^when\s+did\s+",
    r"^how\s+many\s+",
    r"^what\s+are\s+",
    r"^list\s+(the\s+)?(types|kinds|examples)",
    r"^explain\s+(the\s+)?(concept|term|word|definition)",
    r"^what\s+does\s+\w+\s+(mean|stand\s+for)",
    r"^how\s+to\s+(spell|pronounce|say)",
    r"^what\s+color",
    r"^what\s+time",
    r"^what\s+date",
    r"^\d+\s*\+\s*\d+",
    r"^\d+\s*-\s*\d+",
    r"^\d+\s*\*\s*\d+",
    r"^\d+\s*/\s*\d+",
]

# Specific patterns - reasoning, analysis, recommendations
SPECIFIC_PATTERNS = [
    r"\bshould\s+i\b",
    r"\bshould\s+we\b",
    r"\brecommend\b",
    r"\brisk\b",
    r"\binvest\b",
    r"\bstrategy\b",
    r"\bcompare\b",
    r"\banalyze\b",
    r"\bevaluate\b",
    r"\bpredict\b",
    r"\bforecast\b",
    r"\bimpact\b",
    r"\bimplications?\b",
    r"\bconsequences?\b",
    r"\bpros\s+and\s+cons\b",
    r"\badvantages?\s+and\s+disadvantages?\b",
    r"\bbest\s+(way|approach|method|practice)\b",
    r"\bhow\s+to\s+(improve|optimize|build|create|design)\b",
    r"\bwhat\s+would\s+happen\s+if\b",
    r"\bwhat\s+if\b",
    r"\bsimulate\b",
    r"\bwhat\s+are\s+the\s+(implications|effects|consequences|risks)\b",
    r"\bhow\s+does\s+\w+\s+affect\b",
    r"\bimpact\s+of\b",
    r"\binfluence\s+of\b",
    r"\bcorrelation\s+between\b",
    r"\bcausation\b",
    r"\bmarket\s+trends?\b",
    r"\bstock\s+price\b",
    r"\bportfolio\b",
    r"\btrading\s+strategy\b",
    r"\bvaluation\b",
    r"\bcompetitive\s+(analysis|landscape|advantage)\b",
    r"\bswot\s+analysis\b",
    r"\bfeasibility\b",
    r"\bcost-benefit\b",
    r"\breturn\s+on\s+investment\b",
    r"\broi\b",
]

# Domain keywords
DOMAIN_KEYWORDS = {
    "finance": [
        "stock",
        "market",
        "trading",
        "investment",
        "portfolio",
        "earnings",
        "dividend",
        "ipo",
        "merger",
        "acquisition",
        "revenue",
        "profit",
        "loss",
        "valuation",
        "pe ratio",
        "market cap",
        "bull",
        "bear",
        "hedge",
        "options",
        "futures",
        "etf",
        "mutual fund",
        "bond",
        "yield",
        "interest rate",
        "inflation",
        "gdp",
        "recession",
        "crypto",
        "bitcoin",
        "ethereum",
        "blockchain",
        "defi",
        "tesla",
        "apple",
        "microsoft",
        "amazon",
        "google",
        "nvidia",
        "sp500",
        "nasdaq",
        "dow jones",
        "s&p",
    ],
    "technology": [
        "software",
        "hardware",
        "ai",
        "machine learning",
        "deep learning",
        "neural network",
        "algorithm",
        "api",
        "cloud",
        "devops",
        "cybersecurity",
        "blockchain",
        "iot",
        "quantum computing",
        "programming",
        "python",
        "javascript",
        "react",
        "docker",
        "kubernetes",
        "microservices",
        "database",
        "sql",
        "nosql",
    ],
    "healthcare": [
        "drug",
        "treatment",
        "disease",
        "clinical trial",
        "fda",
        "pharma",
        "biotech",
        "healthcare",
        "medical",
        "diagnosis",
        "therapy",
        "vaccine",
        "pandemic",
        "epidemic",
    ],
    "policy": [
        "regulation",
        "policy",
        "law",
        "legislation",
        "government",
        "tax",
        "tariff",
        "sanction",
        "compliance",
        "gdpr",
    ],
}


class QueryClassifier:
    """Classifies queries into GENERIC, SPECIFIC, or HYBRID types."""

    def __init__(self):
        self.generic_patterns = [re.compile(p, re.IGNORECASE) for p in GENERIC_PATTERNS]
        self.specific_patterns = [
            re.compile(p, re.IGNORECASE) for p in SPECIFIC_PATTERNS
        ]

    def classify(self, query: str) -> Tuple[QueryType, float, Dict]:
        """
        Classify a query.

        Returns:
            Tuple of (query_type, confidence, metadata)
        """
        query_lower = query.lower().strip()

        # Score generic patterns
        generic_score = 0
        for pattern in self.generic_patterns:
            if pattern.search(query_lower):
                generic_score += 1

        # Score specific patterns
        specific_score = 0
        for pattern in self.specific_patterns:
            if pattern.search(query_lower):
                specific_score += 1

        # Detect domain
        detected_domain = "general"
        domain_scores = {}
        for domain, keywords in DOMAIN_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in query_lower)
            domain_scores[domain] = score
            if score > domain_scores.get(detected_domain, 0):
                detected_domain = domain

        # Determine type
        total = generic_score + specific_score
        if total == 0:
            # Default: if short query, likely generic; if long, likely specific
            word_count = len(query_lower.split())
            if word_count <= 5:
                return (
                    QueryType.GENERIC,
                    0.5,
                    {
                        "detected_domain": detected_domain,
                        "reasoning_required": False,
                        "word_count": word_count,
                    },
                )
            else:
                return (
                    QueryType.SPECIFIC,
                    0.4,
                    {
                        "detected_domain": detected_domain,
                        "reasoning_required": True,
                        "word_count": word_count,
                    },
                )

        generic_conf = generic_score / total if total > 0 else 0
        specific_conf = specific_score / total if total > 0 else 0

        if generic_score > 0 and specific_score > 0:
            # Both patterns found - HYBRID
            confidence = max(generic_conf, specific_conf)
            return (
                QueryType.HYBRID,
                confidence,
                {
                    "detected_domain": detected_domain,
                    "reasoning_required": True,
                    "generic_score": generic_score,
                    "specific_score": specific_score,
                    "word_count": len(query_lower.split()),
                },
            )
        elif specific_score > 0:
            return (
                QueryType.SPECIFIC,
                specific_conf,
                {
                    "detected_domain": detected_domain,
                    "reasoning_required": True,
                    "word_count": len(query_lower.split()),
                },
            )
        else:
            return (
                QueryType.GENERIC,
                generic_conf,
                {
                    "detected_domain": detected_domain,
                    "reasoning_required": False,
                    "word_count": len(query_lower.split()),
                },
            )
