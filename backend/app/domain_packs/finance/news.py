"""
News module for finance domain pack.

Provides access to financial news via NewsAPI.
"""

from typing import List, Dict, Any
from datetime import datetime, timedelta
import logging

import httpx

from app.config import NEWSAPI_KEY, ALPHAVANTAGE_API_KEY

logger = logging.getLogger(__name__)


def search_news(
    query: str, page_size: int = 10, language: str = "en", sort_by: str = "publishedAt"
) -> List[Dict[str, Any]]:
    """
    Search for news articles.
    """
    if not NEWSAPI_KEY and not ALPHAVANTAGE_API_KEY:
        logger.warning("Both NewsAPI and Alpha Vantage keys missing")
        return []

    if NEWSAPI_KEY:
        try:
            params = {
                "q": query,
                "pageSize": min(page_size, 100),
                "language": language,
                "sortBy": sort_by,
                "apiKey": NEWSAPI_KEY,
            }
            with httpx.Client(timeout=30) as client:
                response = client.get(
                    "https://newsapi.org/v2/everything", params=params
                )

            if response.status_code == 200:
                data = response.json()
                articles = data.get("articles", [])
                if articles:
                    logger.info(
                        f"Found {len(articles)} news articles for '{query}' via NewsAPI"
                    )
                    return articles
        except Exception as e:
            logger.warning(f"NewsAPI search failed, falling back to Alpha Vantage: {e}")

    return _search_alphavantage(query, page_size)


def get_top_headlines(
    category: str = "business", country: str = "us", page_size: int = 10
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
    # Try NewsAPI first
    if NEWSAPI_KEY:
        try:
            params = {
                "category": category,
                "country": country,
                "pageSize": min(page_size, 100),
                "apiKey": NEWSAPI_KEY,
            }
            with httpx.Client(timeout=15) as client:
                response = client.get(
                    "https://newsapi.org/v2/top-headlines", params=params
                )

            if response.status_code == 200:
                data = response.json()
                articles = data.get("articles", [])
                if articles:
                    logger.info(
                        f"Retrieved {len(articles)} top headlines from NewsAPI for {category}/{country}"
                    )
                    return articles
        except Exception as e:
            logger.warning(
                f"NewsAPI headlines failed, falling back to Alpha Vantage: {e}"
            )

    # Fallback to Alpha Vantage news sentiment
    return _get_headlines_from_alphavantage(category, page_size)


def _search_alphavantage(query: str, page_size: int = 10) -> List[Dict[str, Any]]:
    """Search Alpha Vantage news by query/ticker/company name."""
    if not ALPHAVANTAGE_API_KEY:
        logger.warning("Alpha Vantage API key missing for search")
        return []

    try:
        params = {
            "function": "NEWS_SENTIMENT",
            "topics": "FINANCIAL_MARKETS",
            "limit": page_size,
            "apikey": ALPHAVANTAGE_API_KEY,
        }
        with httpx.Client(timeout=15) as client:
            response = client.get("https://www.alphavantage.co/query", params=params)

        if response.status_code != 200:
            logger.error(f"Alpha Vantage search error {response.status_code}")
            return []

        data = response.json()
        if "Error Message" in data or "Information" in data:
            logger.warning(
                f"Alpha Vantage search error: {data.get('Error Message', data.get('Information', ''))}"
            )
            return []

        feed = data.get("feed", [])
        query_lower = query.lower()
        filtered = []
        for item in feed:
            title = (item.get("title", "") or "").lower()
            summary = (item.get("summary", "") or "").lower()
            if not query_lower or query_lower in title or query_lower in summary:
                filtered.append(item)
            if len(filtered) >= page_size:
                break

        if not filtered:
            filtered = feed[:page_size]

        articles = []
        for item in filtered:
            articles.append(
                {
                    "title": item.get("title", ""),
                    "source": {
                        "name": ", ".join(item.get("source", []))
                        if isinstance(item.get("source"), list)
                        else item.get("source", "")
                    },
                    "url": item.get("url", ""),
                    "publishedAt": item.get("time_published", ""),
                    "description": (item.get("summary") or "")[:200],
                }
            )

        logger.info(
            f"Retrieved {len(articles)} articles from Alpha Vantage for '{query}'"
        )
        return articles
    except Exception as e:
        logger.error(f"Error fetching Alpha Vantage search for '{query}': {e}")
        return []


def _get_headlines_from_alphavantage(
    category: str = "business", page_size: int = 10
) -> List[Dict[str, Any]]:
    """Get headlines from Alpha Vantage News & Sentiment endpoint."""
    if not ALPHAVANTAGE_API_KEY:
        logger.warning("Alpha Vantage API key missing for news fallback")
        return []

    # Map NewsAPI categories to Alpha Vantage topics
    topic_map = {
        "business": "FINANCIAL_MARKETS",
        "technology": "TECHNOLOGY",
        "general": "FINANCIAL_MARKETS",
        "entertainment": "TECHNOLOGY",
        "sports": "FINANCIAL_MARKETS",
        "science": "TECHNOLOGY",
        "health": "TECHNOLOGY",
    }
    topic = topic_map.get(category, "FINANCIAL_MARKETS")

    try:
        params = {
            "function": "NEWS_SENTIMENT",
            "topics": topic,
            "limit": page_size,
            "apikey": ALPHAVANTAGE_API_KEY,
        }
        with httpx.Client(timeout=15) as client:
            response = client.get("https://www.alphavantage.co/query", params=params)

        if response.status_code != 200:
            logger.error(f"Alpha Vantage news error {response.status_code}")
            return []

        data = response.json()
        if "Error Message" in data or "Information" in data:
            logger.warning(
                f"Alpha Vantage news error: {data.get('Error Message', data.get('Information', ''))}"
            )
            return []

        feed = data.get("feed", [])
        articles = []
        for item in feed[:page_size]:
            articles.append(
                {
                    "title": item.get("title", ""),
                    "source": {
                        "name": ", ".join(item.get("source", []))
                        if isinstance(item.get("source"), list)
                        else item.get("source", "")
                    },
                    "url": item.get("url", ""),
                    "publishedAt": item.get("time_published", ""),
                    "description": (item.get("summary") or "")[:200],
                }
            )

        logger.info(
            f"Retrieved {len(articles)} headlines from Alpha Vantage for {category}"
        )
        return articles
    except Exception as e:
        logger.error(f"Error fetching Alpha Vantage headlines: {e}")
        return []


def get_company_news(company_name: str, days_back: int = 7) -> List[Dict[str, Any]]:
    """
    Get recent news about a specific company.
    """
    if NEWSAPI_KEY:
        try:
            from_date = (datetime.now() - timedelta(days=days_back)).strftime(
                "%Y-%m-%d"
            )

            params = {
                "q": company_name,
                "from": from_date,
                "sortBy": "publishedAt",
                "language": "en",
                "pageSize": 20,
                "apiKey": NEWSAPI_KEY,
            }
            with httpx.Client(timeout=30) as client:
                response = client.get(
                    "https://newsapi.org/v2/everything", params=params
                )

            if response.status_code == 200:
                data = response.json()
                articles = data.get("articles", [])
                if articles:
                    logger.info(
                        f"Found {len(articles)} articles about '{company_name}' in last {days_back} days via NewsAPI"
                    )
                    return articles
        except Exception as e:
            logger.warning(f"NewsAPI company news failed for '{company_name}': {e}")

    return _search_alphavantage(company_name, 20)
