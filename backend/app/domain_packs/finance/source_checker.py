"""
Source credibility checker for finance domain pack.

Evaluates the credibility of financial news sources and information.
"""

from typing import Dict, Any
from urllib.parse import urlparse
import logging

logger = logging.getLogger(__name__)


# Trusted financial news sources (expandable)
TRUSTED_SOURCES = {
    # Tier 1: Highly trusted
    "bloomberg.com": {"tier": 1, "score": 0.95, "category": "financial_news"},
    "reuters.com": {"tier": 1, "score": 0.95, "category": "news_wire"},
    "wsj.com": {"tier": 1, "score": 0.95, "category": "financial_news"},
    "ft.com": {"tier": 1, "score": 0.95, "category": "financial_news"},
    
    # Tier 2: Trusted
    "cnbc.com": {"tier": 2, "score": 0.85, "category": "financial_news"},
    "marketwatch.com": {"tier": 2, "score": 0.85, "category": "financial_news"},
    "barrons.com": {"tier": 2, "score": 0.85, "category": "financial_news"},
    "economist.com": {"tier": 2, "score": 0.85, "category": "business_news"},
    "forbes.com": {"tier": 2, "score": 0.80, "category": "business_news"},
    
    # Tier 3: Generally reliable
    "yahoo.com": {"tier": 3, "score": 0.70, "category": "aggregator"},
    "seekingalpha.com": {"tier": 3, "score": 0.70, "category": "analysis"},
    "investopedia.com": {"tier": 3, "score": 0.75, "category": "education"},
    
    # Official sources
    "sec.gov": {"tier": 1, "score": 1.0, "category": "regulatory"},
    "federalreserve.gov": {"tier": 1, "score": 1.0, "category": "regulatory"},
    "treasury.gov": {"tier": 1, "score": 1.0, "category": "regulatory"},
}

# Red flag domains (known for misinformation)
UNTRUSTED_SOURCES = {
    "example-scam.com": {"score": 0.1, "reason": "known_scam"},
    # Add more as identified
}


def check_source_credibility(url: str) -> Dict[str, Any]:
    """
    Check the credibility of a source URL.
    
    Args:
        url: Source URL to check
        
    Returns:
        Dictionary with credibility assessment
    """
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        
        # Remove www. prefix
        if domain.startswith("www."):
            domain = domain[4:]
        
        # Check if it's a trusted source
        if domain in TRUSTED_SOURCES:
            info = TRUSTED_SOURCES[domain]
            logger.info(f"Source {domain} is trusted (tier {info['tier']})")
            return {
                "url": url,
                "domain": domain,
                "credibility_score": info["score"],
                "tier": info["tier"],
                "category": info["category"],
                "trusted": True,
                "reason": "known_trusted_source",
            }
        
        # Check if it's an untrusted source
        if domain in UNTRUSTED_SOURCES:
            info = UNTRUSTED_SOURCES[domain]
            logger.warning(f"Source {domain} is untrusted: {info['reason']}")
            return {
                "url": url,
                "domain": domain,
                "credibility_score": info["score"],
                "trusted": False,
                "reason": info["reason"],
            }
        
        # Unknown source - neutral score
        logger.info(f"Source {domain} is unknown, assigning neutral score")
        return {
            "url": url,
            "domain": domain,
            "credibility_score": 0.5,
            "trusted": None,
            "reason": "unknown_source",
        }
    
    except Exception as e:
        logger.error(f"Error checking source credibility for {url}: {e}")
        return {
            "url": url,
            "credibility_score": 0.3,
            "trusted": False,
            "reason": "parse_error",
        }


def aggregate_source_scores(sources: list[str]) -> Dict[str, Any]:
    """
    Aggregate credibility scores from multiple sources.
    
    Args:
        sources: List of source URLs
        
    Returns:
        Aggregated credibility assessment
    """
    if not sources:
        return {
            "average_score": 0.0,
            "trusted_count": 0,
            "untrusted_count": 0,
            "unknown_count": 0,
        }
    
    scores = []
    trusted_count = 0
    untrusted_count = 0
    unknown_count = 0
    
    for url in sources:
        result = check_source_credibility(url)
        scores.append(result["credibility_score"])
        
        if result.get("trusted") is True:
            trusted_count += 1
        elif result.get("trusted") is False:
            untrusted_count += 1
        else:
            unknown_count += 1
    
    average_score = sum(scores) / len(scores) if scores else 0.0
    
    return {
        "average_score": average_score,
        "trusted_count": trusted_count,
        "untrusted_count": untrusted_count,
        "unknown_count": unknown_count,
        "total_sources": len(sources),
        "assessment": "high_credibility" if average_score >= 0.8 else
                     "medium_credibility" if average_score >= 0.6 else
                     "low_credibility",
    }
