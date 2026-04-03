"""
Ticker resolver for finance domain pack.

Resolves company names to stock ticker symbols and vice versa.
"""

import re
from typing import Optional, List, Dict, Any
import logging

from app.domain_packs.finance.market_data import search_symbol

logger = logging.getLogger(__name__)


# Ticker pattern: $SYMBOL or standalone uppercase 1-5 letters
TICKER_PATTERN = re.compile(r'\$([A-Z]{1,5})\b')
STANDALONE_TICKER_PATTERN = re.compile(r'\b([A-Z]{2,5})\b')

# Known ticker mappings (expandable)
KNOWN_TICKERS = {
    "AAPL": "Apple Inc.",
    "MSFT": "Microsoft Corporation",
    "GOOGL": "Alphabet Inc.",
    "GOOG": "Alphabet Inc.",
    "AMZN": "Amazon.com Inc.",
    "META": "Meta Platforms Inc.",
    "TSLA": "Tesla Inc.",
    "NVDA": "NVIDIA Corporation",
    "BRK.A": "Berkshire Hathaway Inc.",
    "BRK.B": "Berkshire Hathaway Inc.",
    "JPM": "JPMorgan Chase & Co.",
    "V": "Visa Inc.",
    "WMT": "Walmart Inc.",
    "XOM": "Exxon Mobil Corporation",
    "JNJ": "Johnson & Johnson",
}

# Reverse mapping
COMPANY_TO_TICKER = {v: k for k, v in KNOWN_TICKERS.items()}


def extract_tickers(text: str) -> List[str]:
    """
    Extract stock ticker symbols from text.
    
    Args:
        text: Input text
        
    Returns:
        List of ticker symbols found
    """
    tickers = []
    
    # Find $SYMBOL patterns
    dollar_tickers = TICKER_PATTERN.findall(text)
    tickers.extend(dollar_tickers)
    
    # Find standalone uppercase symbols (more conservative)
    # Only if they're known tickers to avoid false positives
    standalone = STANDALONE_TICKER_PATTERN.findall(text)
    for symbol in standalone:
        if symbol in KNOWN_TICKERS:
            tickers.append(symbol)
    
    # Remove duplicates while preserving order
    seen = set()
    unique_tickers = []
    for ticker in tickers:
        if ticker not in seen:
            unique_tickers.append(ticker)
            seen.add(ticker)
    
    logger.info(f"Extracted {len(unique_tickers)} tickers from text: {unique_tickers}")
    return unique_tickers


def resolve_ticker(ticker: str) -> Optional[Dict[str, Any]]:
    """
    Resolve ticker symbol to company information.
    
    Args:
        ticker: Stock ticker symbol
        
    Returns:
        Dictionary with company information or None
    """
    ticker = ticker.upper()
    
    # Check known tickers first
    if ticker in KNOWN_TICKERS:
        return {
            "ticker": ticker,
            "company_name": KNOWN_TICKERS[ticker],
            "source": "known_mapping",
            "confidence": 1.0,
        }
    
    # Try Alpha Vantage search
    try:
        results = search_symbol(ticker)
        if results:
            best_match = results[0]
            return {
                "ticker": best_match.get("1. symbol", ticker),
                "company_name": best_match.get("2. name", "Unknown"),
                "region": best_match.get("4. region", "Unknown"),
                "currency": best_match.get("8. currency", "Unknown"),
                "source": "alpha_vantage",
                "confidence": 0.8,
            }
    except Exception as e:
        logger.error(f"Error resolving ticker {ticker}: {e}")
    
    return None


def resolve_company_to_ticker(company_name: str) -> Optional[str]:
    """
    Resolve company name to ticker symbol.
    
    Args:
        company_name: Company name
        
    Returns:
        Ticker symbol or None
    """
    # Check known mappings first
    if company_name in COMPANY_TO_TICKER:
        ticker = COMPANY_TO_TICKER[company_name]
        logger.info(f"Resolved '{company_name}' to ticker {ticker}")
        return ticker
    
    # Try Alpha Vantage search
    try:
        results = search_symbol(company_name)
        if results:
            best_match = results[0]
            ticker = best_match.get("1. symbol")
            logger.info(f"Resolved '{company_name}' to ticker {ticker} via Alpha Vantage")
            return ticker
    except Exception as e:
        logger.error(f"Error resolving company '{company_name}' to ticker: {e}")
    
    return None


def enrich_with_tickers(entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Enrich entity list with ticker symbols.
    
    Args:
        entities: List of entities from entity_resolver
        
    Returns:
        Enriched entities with ticker information
    """
    enriched = []
    
    for entity in entities:
        enriched_entity = entity.copy()
        
        if entity.get("type") == "company":
            company_name = entity.get("text", "")
            ticker = resolve_company_to_ticker(company_name)
            if ticker:
                enriched_entity["ticker"] = ticker
        
        enriched.append(enriched_entity)
    
    return enriched
