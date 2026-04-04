"""
Finance data node — Alpha Vantage integration.
Fetches market data, fundamentals, sentiment, and economic indicators.
No chart rendering — raw structured data only.
"""
import httpx, os, re, logging
from app.agents._model import call_model, safe_parse
from app.config import load_prompt

logger = logging.getLogger(__name__)

AV_BASE = "https://www.alphavantage.co/query"
AV_KEY  = os.getenv("ALPHA_VANTAGE_API_KEY", os.getenv("ALPHAVANTAGE_API_KEY", "demo"))


def av_get(function: str, **params) -> dict:
    """Single Alpha Vantage GET call. Returns parsed JSON or {"error": ...}."""
    try:
        r = httpx.get(AV_BASE, params={"function": function, "apikey": AV_KEY, **params},
                      timeout=20)
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
    Looks for uppercase sequences of 1–5 letters (e.g. AAPL, MSFT, TSLA).
    Falls back to SYMBOL_SEARCH if a company name is detected.
    """
    match = re.search(r'\b([A-Z]{1,5})\b', intent)
    if match:
        return match.group(1)
    return None


def resolve_ticker(intent: str) -> str | None:
    """Use SYMBOL_SEARCH to find a ticker from a company name in the intent."""
    result = av_get("SYMBOL_SEARCH", keywords=intent)
    matches = result.get("bestMatches", [])
    if matches:
        return matches[0].get("1. symbol")
    return None


def run(state: dict) -> dict:
    route  = state.get("route", {})
    intent = route.get("intent", "")
    domain = route.get("domain", "finance")

    gathered = {}

    # Step 1: resolve ticker if query is about a specific stock
    ticker = extract_ticker(intent) or resolve_ticker(intent)

    if ticker:
        # Quote (current price, change, volume) — no OHLCV chart data
        quote = av_get("GLOBAL_QUOTE", symbol=ticker)
        gathered["quote"] = quote.get("Global Quote", quote)

        # Fundamentals (P/E, market cap, sector, EPS, etc.)
        overview = av_get("OVERVIEW", symbol=ticker)
        # Strip raw price series fields to keep payload clean
        for drop_key in ["52WeekHigh", "52WeekLow", "50DayMovingAverage",
                          "200DayMovingAverage", "AnalystTargetPrice"]:
            overview.pop(drop_key, None)
        gathered["fundamentals"] = overview

        # News & sentiment for this ticker
        news = av_get("NEWS_SENTIMENT", tickers=ticker, limit=5)
        gathered["news_sentiment"] = news.get("feed", [])[:5]

    else:
        # No specific ticker — fetch macro / market-wide data
        gathered["top_movers"]   = av_get("TOP_GAINERS_LOSERS")
        gathered["news_general"] = av_get("NEWS_SENTIMENT", limit=5).get("feed", [])[:5]

    # Step 3: if macro / economic query, add indicators
    macro_keywords = ["gdp", "inflation", "cpi", "interest rate", "federal", "economy",
                      "recession", "growth", "unemployment"]
    if any(kw in intent.lower() for kw in macro_keywords):
        gathered["gdp"]       = av_get("REAL_GDP", interval="annual")
        gathered["cpi"]       = av_get("CPI", interval="monthly")
        gathered["inflation"] = av_get("INFLATION")

    # Step 4: LLM interprets the gathered data
    prompt = load_prompt("finance")
    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": (
            f"User intent: {intent}\n\n"
            f"Alpha Vantage data:\n{gathered}\n\n"
            "Analyse this financial data and return ONLY valid JSON:\n"
            "{\n"
            "  \"ticker\": \"<symbol or null>\",\n"
            "  \"signals\": [\"<signal 1>\", \"<signal 2>\"],\n"
            "  \"risks\": [\"<risk 1>\"],\n"
            "  \"sentiment\": \"bullish | bearish | neutral\",\n"
            "  \"key_metrics\": {\"<metric>\": \"<value>\"},\n"
            "  \"data_quality\": \"good | partial | limited\",\n"
            "  \"summary\": \"<2-3 sentence plain English summary>\"\n"
            "}\n"
            "Do NOT include chart data, OHLCV arrays, image URLs, or price history."
        )},
    ]
    try:
        result = safe_parse(call_model(messages))
    except RuntimeError as e:
        logger.error(f"[AGENT ERROR] finance_node: {e}")
        result = {"status": "error", "reason": str(e)}

    return {**state, "finance": result}
