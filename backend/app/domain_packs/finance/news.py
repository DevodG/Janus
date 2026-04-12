"""
News module for finance domain pack.

Primary: Yahoo Finance (free, no key, stock-specific)
Fallback: Actually Relevant (free, no key, curated)
Legacy: Alpha Vantage (requires API key)
"""

from typing import List, Dict, Any
from datetime import datetime, timedelta
import logging

import httpx
import yfinance

from app.config import NEWSAPI_KEY, ALPHAVANTAGE_API_KEY

logger = logging.getLogger(__name__)

ACTUALLY_RELEVANT_API = "https://actually-relevant-api.onrender.com/api"


def _news_query(symbol: str, company_name: str = "") -> str:
    """Strip exchange suffix so news APIs can find the company."""
    if company_name and len(company_name) > 3:
        return company_name
    s = symbol.upper()
    for suffix in [".BSE", ".NSE", ".BO", ".NS", ".L", ".TO"]:
        if s.endswith(suffix):
            return s[: -len(suffix)]
    return s


def _normalize_actually_relevant(stories: list) -> List[Dict[str, Any]]:
    """Convert Actually Relevant stories to the standard article format."""
    articles = []
    for s in stories:
        articles.append(
            {
                "title": s.get("title", ""),
                "source": {
                    "name": s.get("feed", {}).get(
                        "displayTitle", s.get("feed", {}).get("title", "")
                    )
                },
                "url": s.get("sourceUrl", ""),
                "publishedAt": s.get("datePublished", ""),
                "description": (s.get("summary") or "")[:200],
                "stance": "neutral",
                "sentiment_score": 0.5,
                "scam_score": 0.0,
                "rumor_score": 0.0,
                "source_credibility": 0.8,
            }
        )
    return articles


def _fetch_actually_relevant(
    issue_slug: str = None, page_size: int = 10, search_query: str = None
) -> List[Dict[str, Any]]:
    """Fetch curated stories from Actually Relevant API."""
    try:
        params = {"pageSize": page_size}
        if issue_slug:
            params["issueSlug"] = issue_slug
        if search_query:
            params["query"] = search_query
        with httpx.Client(timeout=15) as client:
            response = client.get(f"{ACTUALLY_RELEVANT_API}/stories", params=params)
        if response.status_code == 200:
            data = response.json()
            stories = data.get("data", [])
            if stories:
                logger.info(
                    f"Retrieved {len(stories)} curated stories from Actually Relevant"
                )
                return _normalize_actually_relevant(stories[:page_size])
    except Exception as e:
        logger.warning(f"Actually Relevant API failed: {e}")
    return []


def _get_yahoo_finance_news(symbol: str) -> List[Dict[str, Any]]:
    """Get news from Yahoo Finance for a specific symbol."""
    try:
        ticker = yfinance.Ticker(symbol)
        news = ticker.news
        if not news:
            logger.info(f"No news from Yahoo Finance for {symbol}")
            return []

        articles = []
        for item in news:
            try:
                content = item.get("content", item)
                provider = content.get("provider", {}) or {}
                articles.append(
                    {
                        "title": content.get("title", ""),
                        "source": {
                            "name": provider.get("displayName", "Yahoo Finance")
                            if isinstance(provider, dict)
                            else "Yahoo Finance"
                        },
                        "url": (content.get("clickThroughUrl") or {}).get("url", "")
                        if isinstance(content.get("clickThroughUrl"), dict)
                        else "",
                        "publishedAt": content.get("pubDate", ""),
                        "description": content.get("summary", "")[:200]
                        if content.get("summary")
                        else "",
                    }
                )
            except Exception as inner_e:
                logger.warning(f"Failed to parse news item: {inner_e}")
                continue

        logger.info(f"Got {len(articles)} articles from Yahoo Finance for {symbol}")
        return articles
    except Exception as e:
        logger.warning(f"Yahoo Finance news failed for {symbol}: {e}")
    return []


def search_news(
    query: str, page_size: int = 10, language: str = "en", sort_by: str = "publishedAt"
) -> List[Dict[str, Any]]:
    """Search for news articles."""
    articles = _fetch_actually_relevant(page_size=page_size, search_query=query)
    if articles:
        query_lower = query.lower()
        filtered = [
            a
            for a in articles
            if query_lower in (a.get("title", "") or "").lower()
            or query_lower in (a.get("description", "") or "").lower()
        ]
        if filtered:
            return filtered
        return articles

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
                        f"Found {len(articles)} articles for '{query}' via NewsAPI"
                    )
                    return articles
        except Exception as e:
            logger.warning(f"NewsAPI search failed: {e}")

    if ALPHAVANTAGE_API_KEY:
        return _search_alphavantage(query, page_size)

    return []


def get_top_headlines(
    category: str = "business", country: str = "us", page_size: int = 10
) -> List[Dict[str, Any]]:
    """Get top headlines by category."""
    issue_map = {
        "business": None,
        "technology": "science-technology",
        "science": "science-technology",
        "health": "human-development",
        "general": None,
    }
    issue_slug = issue_map.get(category)
    articles = _fetch_actually_relevant(
        issue_slug=issue_slug, page_size=page_size, search_query=category
    )
    if articles:
        return articles

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
                    return articles
        except Exception as e:
            logger.warning(f"NewsAPI headlines failed: {e}")

    if ALPHAVANTAGE_API_KEY:
        return _get_headlines_from_alphavantage(category, page_size)

    return []


def _search_alphavantage(query: str, page_size: int = 10) -> List[Dict[str, Any]]:
    """Search Alpha Vantage news by query/ticker/company name."""
    if not ALPHAVANTAGE_API_KEY:
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
            return []
        data = response.json()
        if "Error Message" in data or "Information" in data:
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
        return articles
    except Exception as e:
        logger.error(f"Alpha Vantage search error: {e}")
        return []


def _get_headlines_from_alphavantage(
    category: str = "business", page_size: int = 10
) -> List[Dict[str, Any]]:
    """Get headlines from Alpha Vantage News & Sentiment endpoint."""
    if not ALPHAVANTAGE_API_KEY:
        return []
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
            return []
        data = response.json()
        if "Error Message" in data or "Information" in data:
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
        return articles
    except Exception as e:
        logger.error(f"Alpha Vantage headlines error: {e}")
        return []


def get_company_news(
    company_name: str, days_back: int = 7, symbol: str = None
) -> List[Dict[str, Any]]:
    """Get recent news about a specific company."""
    if symbol:
        yf_articles = _get_yahoo_finance_news(symbol)
        if yf_articles:
            logger.info(
                f"Found {len(yf_articles)} articles from Yahoo Finance for {symbol}"
            )
            return yf_articles[:10]

    search_queries = []
    if symbol:
        clean_symbol = symbol.split(".")[0]
        search_queries.append(clean_symbol)
        search_queries.append(f"{clean_symbol} stock")

    if company_name and company_name != symbol:
        search_queries.insert(0, company_name)
        if "." in company_name:
            search_queries.insert(1, company_name.split(".")[0])

    for query in search_queries:
        if not query:
            continue
        articles = _fetch_actually_relevant(page_size=20, search_query=query)
        if articles:
            query_lower = query.lower()
            symbol_lower = (symbol or "").lower()
            filtered = [
                a
                for a in articles
                if query_lower in (a.get("title", "") or "").lower()
                or symbol_lower in (a.get("title", "") or "").lower()
            ]
            if filtered:
                return filtered[:10]

    articles = _fetch_actually_relevant(page_size=20, search_query=company_name)
    if articles:
        company_lower = company_name.lower()
        filtered = [
            a
            for a in articles
            if company_lower in (a.get("title", "") or "").lower()
            or company_lower in (a.get("description", "") or "").lower()
        ]
        if filtered:
            return filtered
        return articles[:10]

    if NEWSAPI_KEY:
        try:
            from_date = (datetime.now() - timedelta(days=days_back)).strftime(
                "%Y-%m-%d"
            )
            params = {
                "q": _news_query(symbol or "", company_name),
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
                    return articles
        except Exception as e:
            logger.warning(f"NewsAPI company news failed: {e}")

    return _search_alphavantage(company_name, 20)
