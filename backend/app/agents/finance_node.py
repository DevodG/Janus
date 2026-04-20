"""
Finance data node — Alpha Vantage integration.
Fetches market data, fundamentals, sentiment, and economic indicators.
No chart rendering — raw structured data only.
"""

import httpx, os, re, logging
from app.agents._model import call_model, safe_parse
from app.config import load_prompt
from app.domain_packs.finance.entity_resolver import extract_entities
from app.domain_packs.finance.market_data import get_company_overview, get_quote
from app.domain_packs.finance.news import get_company_news, get_top_headlines
from app.domain_packs.finance.ticker_resolver import extract_tickers, resolve_company_to_ticker

logger = logging.getLogger(__name__)

AV_BASE = "https://www.alphavantage.co/query"
AV_KEY = os.getenv("ALPHA_VANTAGE_API_KEY", os.getenv("ALPHAVANTAGE_API_KEY", "demo"))


def av_get(function: str, **params) -> dict:
    """Single Alpha Vantage GET call. Returns parsed JSON or {"error": ...}."""
    try:
        r = httpx.get(
            AV_BASE,
            params={"function": function, "apikey": AV_KEY, **params},
            timeout=20,
        )
        r.raise_for_status()
        data = r.json()
        # AV returns {"Information": "..."} when rate-limited or key is invalid
        if "Information" in data or "Note" in data:
            return {"error": data.get("Information") or data.get("Note")}
        return data
    except Exception as e:
        return {"error": str(e)}


def extract_ticker(intent: str) -> str | None:
    """
    Try to pull a ticker symbol from the intent string.
    Use the finance-domain ticker resolver to avoid false positives like
    the word 'AI' being treated as ticker 'AI'.
    """
    tickers = extract_tickers(intent)
    return tickers[0] if tickers else None


def resolve_ticker(intent: str) -> str | None:
    """Resolve a company name to a ticker more conservatively."""
    resolved = resolve_company_to_ticker(intent)
    if resolved:
        return resolved

    try:
        entities = extract_entities(intent)
        for entity in entities:
            if entity.get("type") != "company":
                continue
            resolved = resolve_company_to_ticker(entity.get("text", ""))
            if resolved:
                return resolved
    except Exception as e:
        logger.debug("Entity-based ticker resolution failed: %s", e)

    # Fall back to Alpha Vantage search only on shorter, company-like phrases.
    cleaned = re.sub(r"[^A-Za-z0-9 .&-]", " ", intent).strip()
    if len(cleaned.split()) > 6:
        return None

    result = av_get("SYMBOL_SEARCH", keywords=cleaned)
    matches = result.get("bestMatches", [])
    if matches:
        return matches[0].get("1. symbol")
    return None


def run(state: dict) -> dict:
    route = state.get("route", {})
    intent = route.get("intent", "")
    domain = route.get("domain", "finance")

    gathered = {}

    # Step 1: resolve ticker if query is about a specific stock
    ticker = extract_ticker(intent) or resolve_ticker(intent)

    if ticker:
        # Quote and fundamentals via Yahoo Finance primary, Alpha Vantage fallback inside helpers
        gathered["quote"] = get_quote(ticker)
        overview = get_company_overview(ticker)
        # Strip chart-ish fields to keep payload clean
        for drop_key in [
            "52WeekHigh",
            "52WeekLow",
            "50DayMovingAverage",
            "200DayMovingAverage",
            "AnalystTargetPrice",
        ]:
            overview.pop(drop_key, None)
        gathered["fundamentals"] = overview

        company_name = overview.get("Name") or ticker
        gathered["news_sentiment"] = get_company_news(company_name, days_back=7, symbol=ticker)[:5]

    else:
        # No specific ticker — fetch macro / market-wide data
        gathered["top_movers"] = av_get("TOP_GAINERS_LOSERS")
        gathered["news_general"] = get_top_headlines(category="business", page_size=5)[:5]

    # Step 3: if macro / economic query, add indicators
    macro_keywords = [
        "gdp",
        "inflation",
        "cpi",
        "interest rate",
        "federal",
        "economy",
        "recession",
        "growth",
        "unemployment",
    ]
    if any(kw in intent.lower() for kw in macro_keywords):
        gathered["gdp"] = av_get("REAL_GDP", interval="annual")
        gathered["cpi"] = av_get("CPI", interval="monthly")
        gathered["inflation"] = av_get("INFLATION")

    # Step 4: LLM interprets the gathered data
    prompt = load_prompt("finance")
    messages = [
        {"role": "system", "content": prompt},
        {
            "role": "user",
            "content": (
                f"User intent: {intent}\n\n"
                f"Alpha Vantage data:\n{gathered}\n\n"
                "Analyse this financial data and return ONLY valid JSON:\n"
                "{\n"
                '  "ticker": "<symbol or null>",\n'
                '  "signals": ["<signal 1>", "<signal 2>"],\n'
                '  "risks": ["<risk 1>"],\n'
                '  "sentiment": "bullish | bearish | neutral",\n'
                '  "key_metrics": {"<metric>": "<value>"},\n'
                '  "data_quality": "good | partial | limited",\n'
                '  "summary": "<2-3 sentence plain English summary>"\n'
                "}\n"
                "Do NOT include chart data, OHLCV arrays, image URLs, or price history."
            ),
        },
    ]
    try:
        result = safe_parse(call_model(messages))
    except Exception as e:
        logger.error(f"[AGENT ERROR] finance_node: {e}")

        # Deterministic fallback: return usable structured data even without model access.
        quote = gathered.get("quote") if isinstance(gathered.get("quote"), dict) else {}
        overview = gathered.get("fundamentals") if isinstance(gathered.get("fundamentals"), dict) else {}
        news = gathered.get("news_sentiment") if isinstance(gathered.get("news_sentiment"), list) else []

        price = quote.get("05. price") or quote.get("05. price")
        change_pct = quote.get("10. change percent")
        market_cap = overview.get("MarketCapitalization")
        pe_ratio = overview.get("PERatio")
        sector = overview.get("Sector")

        signals = []
        if ticker:
            signals.append(f"Ticker resolved: {ticker}")
        if price is not None:
            signals.append(f"Price: {price}")
        if change_pct is not None:
            signals.append(f"Change percent: {change_pct}")
        if market_cap is not None:
            signals.append(f"Market cap: {market_cap}")
        if pe_ratio is not None:
            signals.append(f"PE ratio: {pe_ratio}")
        if sector:
            signals.append(f"Sector: {sector}")

        risks = []
        if isinstance(quote, dict) and quote.get("error"):
            risks.append(f"Quote unavailable: {quote.get('error')}")
        if isinstance(overview, dict) and overview.get("error"):
            risks.append(f"Fundamentals unavailable: {overview.get('error')}")

        data_quality = "good" if signals else "limited"
        if any("unavailable" in str(r).lower() for r in risks):
            data_quality = "partial" if signals else "limited"

        summary_parts = ["Deterministic finance summary (no model available)."]
        if ticker:
            summary_parts.append(f"Ticker: {ticker}.")
        if price is not None:
            summary_parts.append(f"Price: {price}.")
        if change_pct is not None:
            summary_parts.append(f"Change: {change_pct}.")
        if market_cap is not None:
            summary_parts.append(f"Market cap: {market_cap}.")
        if pe_ratio is not None:
            summary_parts.append(f"PE: {pe_ratio}.")
        if news:
            summary_parts.append(f"News items fetched: {len(news)}.")

        result = {
            "ticker": ticker,
            "signals": signals,
            "risks": risks,
            "sentiment": "neutral",
            "key_metrics": {
                "price": price,
                "change_percent": change_pct,
                "market_cap": market_cap,
                "pe_ratio": pe_ratio,
                "sector": sector,
            },
            "data_quality": data_quality,
            "summary": " ".join(str(p) for p in summary_parts if p),
            "raw": {
                "quote": quote,
                "fundamentals": overview,
                "news_sentiment": news[:5],
                "macro": {k: v for k, v in gathered.items() if k in {"gdp", "cpi", "inflation"}},
            },
            "status": "ok",
            "mode": "deterministic_fallback",
        }

    return {**state, "finance": result}
