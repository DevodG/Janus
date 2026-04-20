"""
Finance Intelligence Router

Exposes domain pack capabilities directly as API endpoints:
- Ticker/company intelligence (quote + overview + news)
- Stance detection (bullish/bearish)
- Scam detection
- Rumor detection
- Source credibility
- Event impact analysis
- AI signal synthesis
"""

import logging
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.domain_packs.finance.ticker_resolver import extract_tickers, resolve_ticker
from app.domain_packs.finance.entity_resolver import extract_entities
from app.domain_packs.finance.stance_detector import (
    detect_stance,
    analyze_price_action_language,
)
from app.domain_packs.finance.scam_detector import detect_scam_indicators
from app.domain_packs.finance.rumor_detector import detect_rumor_indicators
from app.domain_packs.finance.source_checker import (
    check_source_credibility,
    aggregate_source_scores,
)
from app.domain_packs.finance.event_analyzer import (
    analyze_event_impact,
    detect_event_type,
)
from app.domain_packs.finance.market_data import (
    get_quote,
    get_company_overview,
    search_symbol,
    get_historical_data,
)
from app.domain_packs.finance.news import get_company_news, get_top_headlines
from app.domain_packs.finance.prediction import (
    structure_prediction_context,
    suggest_simulation_scenarios,
)
from app.agents._model import call_model

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/finance", tags=["finance"])


class AnalyzeTextRequest(BaseModel):
    text: str
    sources: list[str] = []


class TickerRequest(BaseModel):
    symbol: str


class NewsAnalysisRequest(BaseModel):
    query: str
    limit: int = 8


# ── Text Intelligence ─────────────────────────────────────────────────────────


@router.post("/analyze/text")
def analyze_text(req: AnalyzeTextRequest):
    """
    Run all domain pack analyzers on a piece of text.
    Returns stance, scam score, rumor score, entities, tickers, events.
    """
    try:
        text = req.text
        sources = req.sources

        tickers = extract_tickers(text)
        entities = extract_entities(text)
        stance = detect_stance(text)
        price_action = analyze_price_action_language(text)
        scam = detect_scam_indicators(text)
        rumor = detect_rumor_indicators(text)
        events = detect_event_type(text)
        event_impact = analyze_event_impact(text, events)
        source_assessment = aggregate_source_scores(sources) if sources else None

        return {
            "tickers": tickers,
            "entities": [e for e in entities if e.get("confidence", 0) >= 0.7],
            "stance": stance,
            "price_action": price_action,
            "scam_detection": scam,
            "rumor_detection": rumor,
            "event_impact": event_impact,
            "source_assessment": source_assessment,
        }
    except Exception as e:
        logger.error(f"Text analysis failed: {e}")
        raise HTTPException(status_code=500, detail="Analysis failed")


# ── Ticker Intelligence ───────────────────────────────────────────────────────


@router.get("/ticker/{symbol}")
def ticker_intelligence(symbol: str):
    """
    Full intelligence package for a ticker:
    quote + company overview + recent news + AI signal
    """
    symbol = symbol.upper().strip()
    try:
        quote = get_quote(symbol)
        overview = get_company_overview(symbol)

        company_name = overview.get("Name") or symbol
        news = get_company_news(company_name, days_back=7, symbol=symbol)

        # Run stance detection on news headlines
        headlines_text = " ".join(
            a.get("title", "") + " " + (a.get("description") or "") for a in news[:10]
        )
        stance = (
            detect_stance(headlines_text)
            if headlines_text.strip()
            else {"stance": "neutral", "confidence": 0.3, "sentiment_score": 0.5}
        )
        events = detect_event_type(headlines_text) if headlines_text.strip() else []
        event_impact = (
            analyze_event_impact(headlines_text, events)
            if headlines_text.strip()
            else {}
        )

        # Build AI signal using LLM
        ai_signal = _generate_ai_signal(
            symbol, company_name, quote, overview, news[:5], stance, events
        )

        return {
            "symbol": symbol,
            "company_name": company_name,
            "quote": quote,
            "overview": {
                "sector": overview.get("Sector"),
                "industry": overview.get("Industry"),
                "market_cap": overview.get("MarketCapitalization"),
                "pe_ratio": overview.get("PERatio"),
                "52_week_high": overview.get("52WeekHigh"),
                "52_week_low": overview.get("52WeekLow"),
                "analyst_target": overview.get("AnalystTargetPrice"),
                "description": (overview.get("Description") or "")[:400],
            },
            "news": [
                {
                    "title": a.get("title"),
                    "source": a.get("source", {}).get("name"),
                    "url": a.get("url"),
                    "published_at": a.get("publishedAt"),
                    "description": (a.get("description") or "")[:200],
                }
                for a in news[:8]
            ],
            "stance": stance,
            "event_impact": event_impact,
            "ai_signal": ai_signal,
        }
    except Exception as e:
        logger.error(f"Ticker intelligence failed for {symbol}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch intelligence for {symbol}"
        )


@router.get("/search/{query}")
def search_ticker(query: str):
    """Search for ticker symbols by company name or keyword."""
    try:
        results = search_symbol(query)
        return [
            {
                "symbol": r.get("1. symbol"),
                "name": r.get("2. name"),
                "type": r.get("3. type"),
                "region": r.get("4. region"),
                "currency": r.get("8. currency"),
            }
            for r in results[:8]
        ]
    except Exception as e:
        logger.error(f"Symbol search failed: {e}")
        return []


@router.get("/historical/{symbol}")
def get_historical(symbol: str, period: str = "3mo"):
    """Get historical stock data for charts."""
    return get_historical_data(symbol.upper().strip(), period)


# ── News Intelligence ─────────────────────────────────────────────────────────


@router.post("/news/analyze")
def analyze_news(req: NewsAnalysisRequest):
    """
    Fetch news for a query and run full intelligence analysis on each article.
    """
    try:
        articles = get_company_news(req.query, days_back=7)
        if not articles:
            from app.domain_packs.finance.news import search_news

            articles = search_news(req.query, page_size=req.limit)

        analyzed = []
        for article in articles[: req.limit]:
            text = (
                (article.get("title") or "") + " " + (article.get("description") or "")
            )
            url = article.get("url", "")

            stance = detect_stance(text)
            scam = detect_scam_indicators(text)
            rumor = detect_rumor_indicators(text)
            source = check_source_credibility(url) if url else None

            analyzed.append(
                {
                    "title": article.get("title"),
                    "source": article.get("source", {}).get("name"),
                    "url": url,
                    "published_at": article.get("publishedAt"),
                    "description": (article.get("description") or "")[:200],
                    "stance": stance.get("stance"),
                    "sentiment_score": stance.get("sentiment_score"),
                    "scam_score": scam.get("scam_score"),
                    "rumor_score": rumor.get("rumor_score"),
                    "source_credibility": source.get("credibility_score")
                    if source
                    else 0.5,
                }
            )

        return {"query": req.query, "articles": analyzed, "total": len(analyzed)}
    except Exception as e:
        logger.error(f"News analysis failed: {e}")
        raise HTTPException(status_code=500, detail="News analysis failed")


@router.get("/headlines")
def get_headlines():
    """Get top business headlines with full intelligence analysis."""
    try:
        articles = get_top_headlines(category="business", page_size=10)
        analyzed = []
        for article in articles[:10]:
            text = (
                (article.get("title") or "") + " " + (article.get("description") or "")
            )
            url = article.get("url", "")

            stance = detect_stance(text)
            scam = detect_scam_indicators(text)
            rumor = detect_rumor_indicators(text)
            source = check_source_credibility(url) if url else None

            analyzed.append(
                {
                    "title": article.get("title"),
                    "source": article.get("source", {}).get("name"),
                    "url": url,
                    "published_at": article.get("publishedAt"),
                    "description": (article.get("description") or "")[:200],
                    "stance": stance.get("stance"),
                    "sentiment_score": stance.get("sentiment_score"),
                    "scam_score": scam.get("scam_score"),
                    "rumor_score": rumor.get("rumor_score"),
                    "source_credibility": source.get("credibility_score")
                    if source
                    else 0.5,
                }
            )
        return analyzed
    except Exception as e:
        logger.error(f"Headlines fetch failed: {e}")
        return []


# ── AI Signal Generator ───────────────────────────────────────────────────────


def _generate_ai_signal(
    symbol: str,
    company_name: str,
    quote: dict,
    overview: dict,
    news: list,
    stance: dict,
    events: list,
) -> dict:
    """Generate an AI trading signal using the LLM."""
    try:
        price = quote.get("05. price", "N/A")
        change_pct = quote.get("10. change percent", "N/A")
        headlines = "\n".join(f"- {a.get('title', '')}" for a in news[:5])
        event_names = (
            ", ".join(e.get("event_type", "") for e in events[:3]) or "none detected"
        )

        prompt = f"""You are a financial intelligence analyst. Analyze this data and give a concise signal.

Company: {company_name} ({symbol})
Current Price: {price}
Change Today: {change_pct}
Market Stance from News: {stance.get("stance")} (confidence: {stance.get("confidence", 0):.0%})
Key Events Detected: {event_names}

Recent Headlines:
{headlines}

Respond in this exact JSON format (no markdown, no extra text):
{{
  "signal": "BUY" | "SELL" | "HOLD" | "WATCH",
  "conviction": 0.0-1.0,
  "reasoning": "one sentence max",
  "risk": "LOW" | "MEDIUM" | "HIGH",
  "timeframe": "short-term" | "medium-term" | "long-term"
}}"""

        raw = call_model(prompt, mode="chat")

        # Parse JSON from response
        import json
        import re

        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"```[a-z]*\n?", "", cleaned).strip()
        data = json.loads(cleaned)
        return data
    except Exception as e:
        logger.warning(f"AI signal generation failed: {e}")
        return {
            "signal": "WATCH",
            "conviction": 0.3,
            "reasoning": "Insufficient data for confident signal",
            "risk": "MEDIUM",
            "timeframe": "short-term",
        }
