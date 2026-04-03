"""
API scorer for prioritizing APIs for integration.
"""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


def score_api_usefulness(api_entry: Dict[str, Any]) -> float:
    """
    Score API for integration priority (0.0 - 1.0).
    
    Factors:
    - Auth simplicity (no auth > apiKey > OAuth)
    - HTTPS support (required)
    - CORS support (preferred)
    - Category relevance to domain packs
    - Description quality
    
    Args:
        api_entry: API entry from catalog
        
    Returns:
        Usefulness score (0.0 - 1.0)
    """
    score = 0.0
    
    # Auth simplicity (30% weight)
    auth = api_entry.get("Auth", "").lower()
    if auth == "" or auth == "no":
        score += 0.30  # No auth is easiest
    elif "apikey" in auth or "api key" in auth:
        score += 0.20  # API key is simple
    elif "oauth" in auth:
        score += 0.10  # OAuth is complex
    else:
        score += 0.05  # Unknown auth
    
    # HTTPS support (25% weight) - required for security
    https = api_entry.get("HTTPS", False)
    if https:
        score += 0.25
    
    # CORS support (15% weight) - preferred for frontend
    cors = api_entry.get("Cors", "").lower()
    if cors == "yes":
        score += 0.15
    elif cors == "unknown":
        score += 0.05
    
    # Category relevance (20% weight)
    category = api_entry.get("Category", "").lower()
    relevance_categories = {
        "finance": 1.0,
        "news": 0.9,
        "government": 0.8,
        "social": 0.7,
        "business": 0.8,
        "cryptocurrency": 0.9,
        "weather": 0.6,
    }
    category_score = 0.0
    for cat, weight in relevance_categories.items():
        if cat in category:
            category_score = max(category_score, weight)
    score += 0.20 * category_score
    
    # Description quality (10% weight)
    description = api_entry.get("Description", "")
    if len(description) > 50:
        score += 0.10
    elif len(description) > 20:
        score += 0.05
    
    return min(score, 1.0)  # Cap at 1.0


def rank_apis(api_entries: list[Dict[str, Any]], top_n: int = 10) -> list[Dict[str, Any]]:
    """
    Rank APIs by usefulness score and return top N.
    
    Args:
        api_entries: List of API entries
        top_n: Number of top APIs to return
        
    Returns:
        Top N APIs sorted by score (descending)
    """
    scored_apis = []
    for api in api_entries:
        score = score_api_usefulness(api)
        scored_apis.append({**api, "usefulness_score": score})
    
    # Sort by score descending
    scored_apis.sort(key=lambda x: x.get("usefulness_score", 0.0), reverse=True)
    
    return scored_apis[:top_n]
