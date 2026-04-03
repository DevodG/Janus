import re
import time
import logging
from typing import List, Dict, Any, Optional

import httpx

from app.config import (
    TAVILY_API_KEY,
    NEWSAPI_KEY,
    ALPHAVANTAGE_API_KEY,
    JINA_READER_BASE,
)

logger = logging.getLogger(__name__)

# Module-level connection pool
_http_pool = httpx.Client(
    timeout=30,
    limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
)

# Simple TTL cache for market quotes (5 min)
_quote_cache: Dict[str, Dict[str, Any]] = {}  # {symbol: {"data": ..., "ts": ...}}
_QUOTE_TTL = 300  # seconds

URL_PATTERN = re.compile(r"https?://\S+")
TICKER_PATTERN = re.compile(r"\$([A-Z]{1,5})\b")


def extract_urls(text: str) -> List[str]:
    return URL_PATTERN.findall(text or "")


def extract_ticker(text: str) -> Optional[str]:
    match = TICKER_PATTERN.search(text or "")
    if match:
        return match.group(1)
    return None


def jina_read(url: str) -> str:
    try:
        target = url.replace("https://", "").replace("http://", "")
        full_url = f"{JINA_READER_BASE}{target}"
        with httpx.Client(timeout=30) as client:
            response = client.get(full_url)
        if response.status_code >= 400:
            return ""
        return response.text[:4000]
    except Exception:
        return ""


def tavily_search(query: str, max_results: int = 5) -> List[Dict[str, Any]]:
    if not TAVILY_API_KEY:
        return []

    try:
        payload = {
            "api_key": TAVILY_API_KEY,
            "query": query,
            "search_depth": "basic",
            "max_results": max_results,
        }
        response = _http_pool.post("https://api.tavily.com/search", json=payload)
        if response.status_code >= 400:
            logger.warning(f"Tavily search returned {response.status_code}")
            return []
        data = response.json()
        return data.get("results", [])
    except Exception as e:
        logger.error(f"Tavily search error: {e}")
        return []


def news_search(query: str, page_size: int = 5) -> List[Dict[str, Any]]:
    if not NEWSAPI_KEY:
        return []

    try:
        params = {
            "q": query,
            "pageSize": page_size,
            "language": "en",
            "sortBy": "publishedAt",
            "apiKey": NEWSAPI_KEY,
        }
        response = _http_pool.get("https://newsapi.org/v2/everything", params=params)
        if response.status_code >= 400:
            logger.warning(f"NewsAPI returned {response.status_code}")
            return []
        data = response.json()
        return data.get("articles", [])
    except Exception as e:
        logger.error(f"NewsAPI error: {e}")
        return []


def market_quote(symbol: str) -> Dict[str, Any]:
    if not ALPHAVANTAGE_API_KEY or not symbol:
        return {}

    # Check cache first
    cached = _quote_cache.get(symbol)
    if cached and (time.time() - cached["ts"]) < _QUOTE_TTL:
        logger.debug(f"Market quote cache hit: {symbol}")
        return cached["data"]

    try:
        params = {
            "function": "GLOBAL_QUOTE",
            "symbol": symbol,
            "apikey": ALPHAVANTAGE_API_KEY,
        }
        response = _http_pool.get("https://www.alphavantage.co/query", params=params)
        if response.status_code >= 400:
            logger.warning(f"Alpha Vantage returned {response.status_code}")
            return {}
        data = response.json()
        quote = data.get("Global Quote", {})

        # Cache the result
        _quote_cache[symbol] = {"data": quote, "ts": time.time()}

        return quote
    except Exception as e:
        logger.error(f"Alpha Vantage error: {e}")
        return {}


def build_external_context(user_input: str) -> str:
    chunks: List[str] = []

    urls = extract_urls(user_input)
    for url in urls[:2]:
        content = jina_read(url)
        if content:
            chunks.append(f"[Jina Reader for {url}]\n{content}")

    search_results = tavily_search(user_input, max_results=4)
    if search_results:
        formatted = []
        for item in search_results[:4]:
            formatted.append(
                f"- {item.get('title', 'Untitled')}\n  {item.get('url', '')}\n  {item.get('content', '')[:300]}"
            )
        chunks.append("[Tavily Search]\n" + "\n".join(formatted))

    articles = news_search(user_input, page_size=4)
    if articles:
        formatted = []
        for item in articles[:4]:
            formatted.append(
                f"- {item.get('title', 'Untitled')}\n  {item.get('url', '')}\n  {str(item.get('description', ''))[:300]}"
            )
        chunks.append("[NewsAPI]\n" + "\n".join(formatted))

    ticker = extract_ticker(user_input)
    if ticker:
        quote = market_quote(ticker)
        if quote:
            chunks.append(f"[Alpha Vantage Quote for {ticker}]\n{quote}")

    if not chunks:
        return "No external API context available."

    return "\n\n".join(chunks)