"""
Market data module for finance domain pack.

Provides access to market quotes, historical data, and financial metrics
via Yahoo Finance (primary) with Alpha Vantage fallback.
"""

import os
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import logging

import httpx
import yfinance

from app.config import ALPHAVANTAGE_API_KEY, FINNHUB_API_KEY, FMP_API_KEY, EODHD_API_KEY

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


def get_historical_data(symbol: str, outputsize: str = "compact") -> list:
    """Waterfall: yfinance → AlphaVantage → Finnhub → FMP → EODHD"""
    days = 100 if outputsize == "compact" else 730
    return (
        _hist_yfinance(symbol, days)
        or _hist_alphavantage(symbol, outputsize)
        or _hist_finnhub(symbol, days)
        or _hist_fmp(symbol, days)
        or _hist_eodhd(symbol, days)
        or []
    )


def _hist_yfinance(symbol: str, days: int) -> list:
    try:
        import yfinance as yf
        from datetime import datetime, timedelta

        # Translate exchange suffixes: RELIANCE.BSE → RELIANCE.BO
        s = symbol.upper()
        if s.endswith(".BSE"):
            s = s[:-4] + ".BO"
        if s.endswith(".NSE"):
            s = s[:-4] + ".NS"
        end = datetime.utcnow()
        start = end - timedelta(days=days)
        df = yf.Ticker(s).history(
            start=start.strftime("%Y-%m-%d"),
            end=end.strftime("%Y-%m-%d"),
            interval="1d",
            auto_adjust=True,
        )
        if df.empty:
            return []
        out = []
        for idx, row in df.iterrows():
            out.append(
                {
                    "date": idx.strftime("%Y-%m-%d"),
                    "open": round(float(row["Open"]), 4),
                    "high": round(float(row["High"]), 4),
                    "low": round(float(row["Low"]), 4),
                    "close": round(float(row["Close"]), 4),
                    "volume": int(row.get("Volume", 0)),
                }
            )
        out.sort(key=lambda x: x["date"])
        logger.info("yfinance: %d points for %s", len(out), symbol)
        return out
    except Exception as e:
        logger.warning("yfinance failed for %s: %s", symbol, e)
        return []


def _hist_alphavantage(symbol: str, outputsize: str) -> list:
    if not ALPHAVANTAGE_API_KEY:
        return []
    try:
        with httpx.Client(timeout=20) as c:
            r = c.get(
                "https://www.alphavantage.co/query",
                params={
                    "function": "TIME_SERIES_DAILY",
                    "symbol": symbol.upper(),
                    "outputsize": outputsize,
                    "apikey": ALPHAVANTAGE_API_KEY,
                },
            )
        data = r.json()
        if "Information" in data or "Note" in data:
            return []
        series = data.get("Time Series (Daily)", {})
        if not series:
            return []
        out = [
            {
                "date": d,
                "open": float(v["1. open"]),
                "high": float(v["2. high"]),
                "low": float(v["3. low"]),
                "close": float(v["4. close"]),
                "volume": int(v["5. volume"]),
            }
            for d, v in series.items()
        ]
        out.sort(key=lambda x: x["date"])
        return out
    except Exception as e:
        logger.warning("AlphaVantage failed: %s", e)
        return []


def _hist_finnhub(symbol: str, days: int) -> list:
    key = os.getenv("FINNHUB_API_KEY", "")
    if not key:
        return []
    try:
        import time as t
        from datetime import datetime as dt

        end = int(t.time())
        start = end - days * 86400
        with httpx.Client(timeout=15) as c:
            r = c.get(
                "https://finnhub.io/api/v1/stock/candle",
                params={
                    "symbol": symbol.upper(),
                    "resolution": "D",
                    "from": start,
                    "to": end,
                    "token": key,
                },
            )
        data = r.json()
        if data.get("s") != "ok":
            return []
        out = [
            {
                "date": dt.utcfromtimestamp(ts).strftime("%Y-%m-%d"),
                "open": data["o"][i],
                "high": data["h"][i],
                "low": data["l"][i],
                "close": data["c"][i],
                "volume": int(data["v"][i]),
            }
            for i, ts in enumerate(data.get("t", []))
        ]
        return out
    except Exception as e:
        logger.warning("Finnhub failed: %s", e)
        return []


def _hist_fmp(symbol: str, days: int) -> list:
    key = os.getenv("FMP_API_KEY", "")
    if not key:
        return []
    try:
        from datetime import datetime as dt, timedelta

        end = dt.utcnow().strftime("%Y-%m-%d")
        start = (dt.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d")
        with httpx.Client(timeout=15) as c:
            r = c.get(
                f"https://financialmodelingprep.com/api/v3/historical-price-full/{symbol.upper()}",
                params={"from": start, "to": end, "apikey": key},
            )
        history = r.json().get("historical", [])
        out = [
            {
                "date": row["date"],
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"]),
                "volume": int(row.get("volume", 0)),
            }
            for row in history
        ]
        out.sort(key=lambda x: x["date"])
        return out
    except Exception as e:
        logger.warning("FMP failed: %s", e)
        return []


def _hist_eodhd(symbol: str, days: int) -> list:
    key = os.getenv("EODHD_API_KEY", "")
    if not key:
        return []
    try:
        from datetime import datetime as dt, timedelta

        end = dt.utcnow().strftime("%Y-%m-%d")
        start = (dt.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d")
        with httpx.Client(timeout=15) as c:
            r = c.get(
                f"https://eodhd.com/api/eod/{symbol.upper()}",
                params={"from": start, "to": end, "api_token": key, "fmt": "json"},
            )
        data = r.json()
        if not isinstance(data, list):
            return []
        out = [
            {
                "date": row["date"],
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["adjusted_close"]),
                "volume": int(row.get("volume", 0)),
            }
            for row in data
        ]
        out.sort(key=lambda x: x["date"])
        return out
    except Exception as e:
        logger.warning("EODHD failed: %s", e)
        return []


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
