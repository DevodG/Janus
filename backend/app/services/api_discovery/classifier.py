"""
API classifier for categorizing APIs by domain and use case.
"""

import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

# Domain classification keywords
DOMAIN_KEYWORDS = {
    "market_data": ["stock", "crypto", "currency", "finance", "trading", "market", "exchange", "commodity"],
    "news": ["news", "article", "media", "press", "journalism", "headline"],
    "social": ["social", "twitter", "facebook", "reddit", "instagram", "community"],
    "government": ["government", "policy", "regulation", "law", "public", "civic", "open data"],
    "weather": ["weather", "climate", "forecast", "meteorology", "temperature"],
    "general": [],  # Catch-all
}


def classify_api(api_entry: Dict[str, Any]) -> Dict[str, Any]:
    """
    Classify API by category and potential use cases.
    
    Args:
        api_entry: API entry from catalog with API, Description, Category, etc.
        
    Returns:
        Classification with:
        - domain: Detected domain (market_data, news, social, government, weather, general)
        - use_cases: List of potential use cases
        - relevance_score: Relevance to MiroOrg domains (0.0 - 1.0)
    """
    name = api_entry.get("API", "").lower()
    description = api_entry.get("Description", "").lower()
    category = api_entry.get("Category", "").lower()
    
    combined_text = f"{name} {description} {category}"
    
    # Detect domain
    detected_domain = "general"
    max_matches = 0
    
    for domain, keywords in DOMAIN_KEYWORDS.items():
        if domain == "general":
            continue
        matches = sum(1 for keyword in keywords if keyword in combined_text)
        if matches > max_matches:
            max_matches = matches
            detected_domain = domain
    
    # Determine use cases
    use_cases = []
    if detected_domain == "market_data":
        use_cases = ["financial_research", "market_analysis", "portfolio_tracking"]
    elif detected_domain == "news":
        use_cases = ["news_research", "sentiment_analysis", "event_detection"]
    elif detected_domain == "social":
        use_cases = ["social_listening", "sentiment_analysis", "trend_detection"]
    elif detected_domain == "government":
        use_cases = ["policy_research", "regulatory_tracking", "open_data_analysis"]
    elif detected_domain == "weather":
        use_cases = ["weather_forecasting", "climate_analysis"]
    else:
        use_cases = ["general_research"]
    
    # Calculate relevance score (higher for domains we care about)
    relevance_scores = {
        "market_data": 1.0,
        "news": 0.9,
        "government": 0.8,
        "social": 0.7,
        "weather": 0.5,
        "general": 0.3,
    }
    relevance_score = relevance_scores.get(detected_domain, 0.3)
    
    return {
        "domain": detected_domain,
        "use_cases": use_cases,
        "relevance_score": relevance_score,
    }


def classify_multiple_apis(api_entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Classify multiple APIs and return enriched entries."""
    results = []
    for api in api_entries:
        classification = classify_api(api)
        enriched = {**api, **classification}
        results.append(enriched)
    return results
