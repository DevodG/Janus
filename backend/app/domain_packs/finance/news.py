"""
News module for finance domain pack.

Provides access to financial news via NewsAPI.
"""

from typing import List, Dict, Any
from datetime import datetime, timedelta
import logging

import httpx

from app.config import NEWSAPI_KEY

logger = logging.getLogger(__name__)


def search_news(
    query: str,
    page_size: int = 10,
    language: str = "en",
    sort_by: str = "publishedAt"
) -> List[Dict[str, Any]]:
    """
    Search for news articles.
    
    Args:
        query: Search query
        page_size: Number of results (max 100)
        language: Language code (default: 'en')
        sort_by: Sort order ('publishedAt', 'relevancy', 'popularity')
        
    Returns:
        List of news articles
    """
    if not NEWSAPI_KEY:
        logger.warning("NewsAPI key missing")
        return []

    try:
        params = {
            "q": query,
            "pageSize": min(page_size, 100),
            "language": language,
            "sortBy": sort_by,
            "apiKey": NEWSAPI_KEY,
        }
        with httpx.Client(timeout=30) as client:
            response = client.get("https://newsapi.org/v2/everything", params=params)
        
        if response.status_code >= 400:
            logger.error(f"NewsAPI error {response.status_code}: {response.text}")
            return []
        
        data = response.json()
        articles = data.get("articles", [])
        logger.info(f"Found {len(articles)} news articles for '{query}'")
        return articles
    except Exception as e:
        logger.error(f"Error searching news for '{query}': {e}")
        return []


def get_top_headlines(
    category: str = "business",
    country: str = "us",
    page_size: int = 10
) -> List[Dict[str, Any]]:
    """
    Get top headlines by category.
    
    Args:
        category: News category ('business', 'technology', etc.)
        country: Country code (default: 'us')
        page_size: Number of results (max 100)
        
    Returns:
        List of top headline articles
    """
    if not NEWSAPI_KEY:
        logger.warning("NewsAPI key missing")
        return []

    try:
        params = {
            "category": category,
            "country": country,
            "pageSize": min(page_size, 100),
            "apiKey": NEWSAPI_KEY,
        }
        with httpx.Client(timeout=30) as client:
            response = client.get("https://newsapi.org/v2/top-headlines", params=params)
        
        if response.status_code >= 400:
            logger.error(f"NewsAPI error {response.status_code}")
            return []
        
        data = response.json()
        articles = data.get("articles", [])
        logger.info(f"Retrieved {len(articles)} top headlines for {category}/{country}")
        return articles
    except Exception as e:
        logger.error(f"Error fetching top headlines: {e}")
        return []


def get_company_news(company_name: str, days_back: int = 7) -> List[Dict[str, Any]]:
    """
    Get recent news about a specific company.
    
    Args:
        company_name: Company name to search for
        days_back: Number of days to look back (default: 7)
        
    Returns:
        List of news articles about the company
    """
    if not NEWSAPI_KEY:
        return []

    try:
        from_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
        
        params = {
            "q": company_name,
            "from": from_date,
            "sortBy": "publishedAt",
            "language": "en",
            "pageSize": 20,
            "apiKey": NEWSAPI_KEY,
        }
        with httpx.Client(timeout=30) as client:
            response = client.get("https://newsapi.org/v2/everything", params=params)
        
        if response.status_code >= 400:
            return []
        
        data = response.json()
        articles = data.get("articles", [])
        logger.info(f"Found {len(articles)} articles about '{company_name}' in last {days_back} days")
        return articles
    except Exception as e:
        logger.error(f"Error fetching company news for '{company_name}': {e}")
        return []
