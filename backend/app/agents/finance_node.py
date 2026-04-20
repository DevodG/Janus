"""
Finance data node — Alpha Vantage integration.
Fetches market data, fundamentals, sentiment, and economic indicators.
No chart rendering — raw structured data only.
"""

import asyncio
from typing import List, Dict, Any, Optional
import json
import os, re, logging
from app.agents._model import call_model, safe_parse
from app.config import load_prompt
from app.domain_packs.finance.entity_resolver import extract_entities
from app.domain_packs.finance.market_data import get_company_overview, get_quote
from app.domain_packs.finance.news import get_company_news, get_top_headlines
from app.domain_packs.finance.ticker_resolver import extract_tickers, resolve_company_to_ticker

logger = logging.getLogger(__name__)

AV_BASE = "https://www.alphavantage.co/query"
AV_KEY = os.getenv("ALPHA_VANTAGE_API_KEY", os.getenv("ALPHAVANTAGE_API_KEY", "demo"))


async def av_get(function: str, **params) -> dict:
    """Single Alpha Vantage GET call (Async)."""
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.get(
                AV_BASE,
                params={"function": function, "apikey": AV_KEY, **params}
            )
        r.raise_for_status()
        data = r.json()
        if "Information" in data or "Note" in data:
            return {"error": data.get("Information") or data.get("Note")}
        return data
    except Exception as e:
        return {"error": str(e)}


def extract_tickers_list(intent: str) -> List[str]:
    """Extract list of ticker symbols from intent."""
    return extract_tickers(intent)


async def resolve_all_tickers(intent: str) -> List[str]:
    """Resolve multiple company names to tickers (Async)."""
    tickers = set()
    
    # Try direct resolution of the whole intent
    res = await resolve_company_to_ticker(intent)
    if res:
        tickers.add(res)

    try:
        entities = extract_entities(intent)
        for entity in entities:
            if entity.get("type") != "company":
                continue
            res = await resolve_company_to_ticker(entity.get("text", ""))
            if res:
                tickers.add(res)
    except Exception as e:
        logger.debug("Multi-entity ticker resolution failed: %s", e)

    # If still empty and short, try Alpha Vantage search fallback
    if not tickers:
        cleaned = re.sub(r"[^A-Za-z0-9 .&-]", " ", intent).strip()
        if len(cleaned.split()) <= 6:
            result = await av_get("SYMBOL_SEARCH", keywords=cleaned)
            matches = result.get("bestMatches", [])
            for m in matches[:2]:
                tickers.add(m.get("1. symbol"))
    
    return list(tickers)


async def _gather_single_ticker(ticker: str) -> Dict[str, Any]:
    """Gather all data for one ticker in parallel."""
    try:
        # Fetching quote, overview, and news concurrently for this ticker
        quote_task = get_quote(ticker)
        overview_task = get_company_overview(ticker)
        
        quote, overview = await asyncio.gather(quote_task, overview_task)
        
        company_name = overview.get("Name") or ticker
        news = await get_company_news(company_name, days_back=7, symbol=ticker)
        
        # Strip chart-ish fields
        for drop_key in ["52WeekHigh", "52WeekLow", "50DayMovingAverage", "200DayMovingAverage", "AnalystTargetPrice"]:
            overview.pop(drop_key, None)
            
        return {
            "quote": quote,
            "fundamentals": overview,
            "news_sentiment": news[:3]
        }
    except Exception as e:
        logger.warning(f"Failed to gather data for {ticker}: {e}")
        return {"error": str(e)}


async def run(state: dict) -> dict:
    """Async finance node — parallel data gathering with strict timeouts."""
    route = state.get("route", {})
    intent = route.get("intent", "")

    # Step 1: resolve tickers (multiple supported for comparisons)
    found_tickers = extract_tickers_list(intent)
    resolved_tickers = await resolve_all_tickers(intent)
    
    all_tickers = list(dict.fromkeys(found_tickers + resolved_tickers))[:3]
    logger.info(f"[finance_node] Parallel processing tickers: {all_tickers}")

    gathered = {"tickers": {}}

    if all_tickers:
        try:
            # Step 2: Parallelize data fetching across all tickers
            # Total timeout of 35s for the entire gathering phase
            tasks = [_gather_single_ticker(ticker) for ticker in all_tickers]
            results = await asyncio.wait_for(asyncio.gather(*tasks), timeout=35.0)
            
            for ticker, result in zip(all_tickers, results):
                if result and "error" not in result:
                    gathered["tickers"][ticker] = result
        except asyncio.TimeoutError:
            logger.warning("[finance_node] Data gathering timed out — proceeding with partial data")
    else:
        # No specific tickers — fetch macro / market-wide data
        macro_tasks = [
            av_get("TOP_GAINERS_LOSERS"),
            get_top_headlines(category="business", page_size=5)
        ]
        results = await asyncio.gather(*macro_tasks)
        gathered["top_movers"] = results[0]
        gathered["news_general"] = results[1][:5]

    # Step 3: if macro / economic query, add indicators
    macro_keywords = ["gdp", "inflation", "cpi", "interest rate", "federal", "economy", "recession", "growth", "unemployment"]
    if any(kw in intent.lower() for kw in macro_keywords):
        macro_keys = ["REAL_GDP", "CPI", "INFLATION"]
        macro_results = await asyncio.gather(*[av_get(k) for k in macro_keys])
        gathered["macro"] = {
            "gdp": macro_results[0],
            "cpi": macro_results[1],
            "inflation": macro_results[2]
        }

    # Step 4: LLM interprets the gathered data
    prompt = load_prompt("finance")
    messages = [
        {"role": "system", "content": prompt},
        {
            "role": "user",
            "content": (
                f"User intent: {intent}\n\n"
                f"Market Data:\n{json.dumps(gathered, indent=2, default=str)}\n\n"
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
            ),
        },
    ]
    
    try:
        raw_response = await asyncio.to_thread(call_model, messages)
        result = safe_parse(raw_response)
    except Exception as e:
        logger.error(f"[AGENT ERROR] finance_node: {e}")

        # Deterministic fallback
        fallback_summary = []
        for t, data in gathered.get("tickers", {}).items():
            price = data.get("quote", {}).get("05. price")
            fallback_summary.append(f"{t}: Price {price}.")

        result = {
            "ticker": all_tickers[0] if all_tickers else None,
            "signals": ["Data retrieved"],
            "risks": ["LLM synthesis failed"],
            "sentiment": "neutral",
            "key_metrics": {},
            "data_quality": "partial",
            "summary": " ".join(fallback_summary) or "No market data retrieved.",
            "mode": "deterministic_fallback",
        }

    return {**state, "finance": result}

