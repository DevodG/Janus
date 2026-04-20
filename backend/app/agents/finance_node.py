"""
Finance data node — Alpha Vantage integration.
Fetches market data, fundamentals, sentiment, and economic indicators.
No chart rendering — raw structured data only.
"""

from typing import List, Dict, Any, Optional
import json
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


def extract_tickers_list(intent: str) -> List[str]:
    """Extract list of ticker symbols from intent."""
    return extract_tickers(intent)


def resolve_all_tickers(intent: str) -> List[str]:
    """Resolve multiple company names to tickers."""
    tickers = set()
    
    # Try direct resolution of the whole intent
    res = resolve_company_to_ticker(intent)
    if res:
        tickers.add(res)

    try:
        entities = extract_entities(intent)
        for entity in entities:
            if entity.get("type") != "company":
                continue
            res = resolve_company_to_ticker(entity.get("text", ""))
            if res:
                tickers.add(res)
    except Exception as e:
        logger.debug("Multi-entity ticker resolution failed: %s", e)

    # If still empty and short, try Alpha Vantage search fallback
    if not tickers:
        cleaned = re.sub(r"[^A-Za-z0-9 .&-]", " ", intent).strip()
        if len(cleaned.split()) <= 6:
            result = av_get("SYMBOL_SEARCH", keywords=cleaned)
            matches = result.get("bestMatches", [])
            for m in matches[:2]:
                tickers.add(m.get("1. symbol"))
    
    return list(tickers)


def run(state: dict) -> dict:
    route = state.get("route", {})
    intent = route.get("intent", "")
    domain = route.get("domain", "finance")

    # Step 1: resolve tickers (multiple supported for comparisons)
    found_tickers = extract_tickers_list(intent)
    resolved_tickers = resolve_all_tickers(intent)
    
    all_tickers = list(dict.fromkeys(found_tickers + resolved_tickers))[:3]
    logger.info(f"[finance_node] Processing tickers: {all_tickers}")

    gathered = {"tickers": {}}

    if all_tickers:
        for ticker in all_tickers:
            ticker_data = {}
            # Quote and fundamentals
            ticker_data["quote"] = get_quote(ticker)
            overview = get_company_overview(ticker)
            
            # Strip chart-ish fields
            for drop_key in [
                "52WeekHigh", "52WeekLow", "50DayMovingAverage", 
                "200DayMovingAverage", "AnalystTargetPrice"
            ]:
                overview.pop(drop_key, None)
            ticker_data["fundamentals"] = overview

            company_name = overview.get("Name") or ticker
            ticker_data["news_sentiment"] = get_company_news(company_name, days_back=7, symbol=ticker)[:3]
            
            gathered["tickers"][ticker] = ticker_data
    else:
        # No specific tickers — fetch macro / market-wide data
        gathered["top_movers"] = av_get("TOP_GAINERS_LOSERS")
        gathered["news_general"] = get_top_headlines(category="business", page_size=5)[:5]

    # Step 3: if macro / economic query, add indicators
    macro_keywords = ["gdp", "inflation", "cpi", "interest rate", "federal", "economy", "recession", "growth", "unemployment"]
    if any(kw in intent.lower() for kw in macro_keywords):
        gathered["macro"] = {
            "gdp": av_get("REAL_GDP", interval="annual"),
            "cpi": av_get("CPI", interval="monthly"),
            "inflation": av_get("INFLATION")
        }

    # Step 4: LLM interprets the gathered data
    prompt = load_prompt("finance")
    messages = [
        {"role": "system", "content": prompt},
        {
            "role": "user",
            "content": (
                f"User intent: {intent}\n\n"
                f"Market Data:\n{json.dumps(gathered, indent=2)}\n\n"
                "Analyse this financial data and return ONLY valid JSON:\n"
                "{\n"
                '  "ticker": "<main symbol or null>",\n'
                '  "signals": ["<signal 1>", "<signal 2>"],\n'
                '  "risks": ["<risk 1>"],\n'
                '  "sentiment": "bullish | bearish | neutral",\n'
                '  "key_metrics": {"<metric>": "<value>"},\n'
                '  "data_quality": "good | partial | limited",\n'
                '  "summary": "<2-3 sentence plain English summary comparison>"\n'
                "}\n"
                "Do NOT include chart data, OHLCV arrays, or price history."
            ),
        },
    ]
    
    try:
        result = safe_parse(call_model(messages))
    except Exception as e:
        logger.error(f"[AGENT ERROR] finance_node: {e}")

        # Deterministic fallback for multiple tickers
        fallback_summary = []
        signals = []
        risks = []
        
        for t, data in gathered["tickers"].items():
            price = data.get("quote", {}).get("05. price")
            change = data.get("quote", {}).get("10. change percent")
            fallback_summary.append(f"{t}: Price {price} ({change}).")
            if price:
                signals.append(f"{t} active price: {price}")
            if not price:
                risks.append(f"Could not retrieve live quote for {t}")

        result = {
            "ticker": all_tickers[0] if all_tickers else None,
            "signals": signals,
            "risks": risks,
            "sentiment": "neutral",
            "key_metrics": {t: data.get("quote", {}).get("05. price") for t, data in gathered["tickers"].items()},
            "data_quality": "partial" if gathered["tickers"] else "limited",
            "summary": " ".join(fallback_summary) or "No market data retrieved.",
            "raw": gathered,
            "status": "ok",
            "mode": "deterministic_fallback",
        }

    return {**state, "finance": result}

