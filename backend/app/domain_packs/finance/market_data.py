"""
Market data module for finance domain pack.

Provides access to market quotes, historical data, and financial metrics
via Alpha Vantage API.
"""

from typing import Dict, Any, Optional
import logging

import httpx

from app.config import ALPHAVANTAGE_API_KEY

logger = logging.getLogger(__name__)


def get_quote(symbol: str) -> Dict[str, Any]:
    """
    Get real-time quote for a stock symbol.
    
    Args:
        symbol: Stock ticker symbol (e.g., 'AAPL', 'TSLA')
        
    Returns:
        Dictionary with quote data or empty dict if unavailable
    """
    if not ALPHAVANTAGE_API_KEY or not symbol:
        logger.warning("Alpha Vantage API key missing or symbol empty")
        return {}

    try:
        params = {
            "function": "GLOBAL_QUOTE",
            "symbol": symbol.upper(),
            "apikey": ALPHAVANTAGE_API_KEY,
        }
        with httpx.Client(timeout=30) as client:
            response = client.get("https://www.alphavantage.co/query", params=params)
        
        if response.status_code >= 400:
            logger.error(f"Alpha Vantage API error {response.status_code}")
            return {}
        
        data = response.json()
        quote = data.get("Global Quote", {})
        
        if quote:
            logger.info(f"Retrieved quote for {symbol}")
        else:
            logger.warning(f"No quote data for {symbol}")
        
        return quote
    except Exception as e:
        logger.error(f"Error fetching quote for {symbol}: {e}")
        return {}


def get_company_overview(symbol: str) -> Dict[str, Any]:
    """
    Get company overview and fundamental data.
    
    Args:
        symbol: Stock ticker symbol
        
    Returns:
        Dictionary with company data or empty dict if unavailable
    """
    if not ALPHAVANTAGE_API_KEY or not symbol:
        return {}

    try:
        params = {
            "function": "OVERVIEW",
            "symbol": symbol.upper(),
            "apikey": ALPHAVANTAGE_API_KEY,
        }
        with httpx.Client(timeout=30) as client:
            response = client.get("https://www.alphavantage.co/query", params=params)
        
        if response.status_code >= 400:
            return {}
        
        data = response.json()
        logger.info(f"Retrieved company overview for {symbol}")
        return data
    except Exception as e:
        logger.error(f"Error fetching company overview for {symbol}: {e}")
        return {}


def search_symbol(keywords: str) -> list[Dict[str, Any]]:
    """
    Search for stock symbols by company name or keywords.
    
    Args:
        keywords: Search keywords
        
    Returns:
        List of matching symbols with metadata
    """
    if not ALPHAVANTAGE_API_KEY or not keywords:
        return []

    try:
        params = {
            "function": "SYMBOL_SEARCH",
            "keywords": keywords,
            "apikey": ALPHAVANTAGE_API_KEY,
        }
        with httpx.Client(timeout=30) as client:
            response = client.get("https://www.alphavantage.co/query", params=params)
        
        if response.status_code >= 400:
            return []
        
        data = response.json()
        matches = data.get("bestMatches", [])
        logger.info(f"Found {len(matches)} symbol matches for '{keywords}'")
        return matches
    except Exception as e:
        logger.error(f"Error searching symbols for '{keywords}': {e}")
        return []
