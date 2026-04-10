"""
Market data module for finance domain pack.

Provides access to market quotes, historical data, and financial metrics
via Yahoo Finance (primary) with Alpha Vantage fallback.
"""

from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import logging

import httpx
import yfinance

from app.config import ALPHAVANTAGE_API_KEY

logger = logging.getLogger(__name__)

INDIAN_SUFFIX_MAP = {
    "RELIANCE": "RELIANCE.BSE",
    "TCS": "TCS.BSE",
    "HDFCBANK": "HDFCBANK.NS",
    "ICICIBANK": "ICICIBANK.NS",
    "SBIN": "SBIN.NS",
}


def _get_yahoo_symbol(symbol: str) -> str:
    """Convert symbol to Yahoo Finance format for Indian stocks."""
    clean = symbol.upper().strip()
    if clean in INDIAN_SUFFIX_MAP:
        return INDIAN_SUFFIX_MAP[clean]
    if "." not in clean:
        return clean
    return symbol


def get_quote(symbol: str) -> Dict[str, Any]:
    """
    Get real-time quote for a stock symbol.
    """
    yf_symbol = _get_yahoo_symbol(symbol)
    try:
        ticker = yfinance.Ticker(yf_symbol)
        info = ticker.info
        if info:
            return {
                "05. price": info.get("currentPrice") or info.get("regularMarketPrice"),
                "09. change": info.get("regularMarketChange"),
                "10. change percent": info.get("regularMarketChangePercent"),
                "06. volume": info.get("regularMarketVolume"),
                "08. previous close": info.get("previousClose"),
            }
    except Exception as e:
        logger.warning(f"Yahoo Finance quote failed for {symbol}: {e}")

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
    Get company overview and fundamental data using Yahoo Finance.
    """
    yf_symbol = _get_yahoo_symbol(symbol)
    try:
        ticker = yfinance.Ticker(yf_symbol)
        info = ticker.info
        if info:
            return {
                "Name": info.get("longName") or info.get("shortName") or symbol,
                "Sector": info.get("sector", ""),
                "Industry": info.get("industry", ""),
                "MarketCapitalization": info.get("marketCap"),
                "PERatio": info.get("trailingPE"),
                "52WeekHigh": info.get("fiftyTwoWeekHigh"),
                "52WeekLow": info.get("fiftyTwoWeekLow"),
                "AnalystTargetPrice": info.get("targetMeanPrice"),
                "Description": info.get("longBusinessSummary", "")[:500],
            }
    except Exception as e:
        logger.warning(f"Yahoo Finance overview failed for {symbol}: {e}")

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


def get_historical_data(symbol: str, period: str = "3mo") -> Dict[str, Any]:
    """
    Get historical stock data for charts.
    """
    yf_symbol = _get_yahoo_symbol(symbol)
    try:
        ticker = yfinance.Ticker(yf_symbol)
        hist = ticker.history(period=period)
        if not hist.empty:
            data = []
            for idx, row in hist.iterrows():
                data.append(
                    {
                        "date": idx.strftime("%Y-%m-%d"),
                        "open": float(row["Open"]),
                        "high": float(row["High"]),
                        "low": float(row["Low"]),
                        "close": float(row["Close"]),
                        "volume": int(row["Volume"]),
                    }
                )
            logger.info(f"Retrieved {len(data)} historical points for {symbol}")
            return {"symbol": symbol, "data": data}
    except Exception as e:
        logger.warning(f"Yahoo Finance historical failed for {symbol}: {e}")

    return {"symbol": symbol, "data": []}


def search_symbol(keywords: str) -> list[Dict[str, Any]]:
    """
    Search for stock symbols by company name or keywords.
    """
    if not keywords:
        return []

    if ALPHAVANTAGE_API_KEY:
        try:
            params = {
                "function": "SYMBOL_SEARCH",
                "keywords": keywords,
                "apikey": ALPHAVANTAGE_API_KEY,
            }
            with httpx.Client(timeout=30) as client:
                response = client.get(
                    "https://www.alphavantage.co/query", params=params
                )

            if response.status_code < 400:
                data = response.json()
                matches = data.get("bestMatches", [])
                logger.info(f"Found {len(matches)} symbol matches for '{keywords}'")
                return matches
        except Exception as e:
            logger.error(f"Error searching symbols for '{keywords}': {e}")

    return []
