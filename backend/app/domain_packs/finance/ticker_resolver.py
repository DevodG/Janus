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
    "RELIANCE": "Reliance Industries Limited",
    "TCS": "Tata Consultancy Services Limited",
    "HDFCBANK": "HDFC Bank Limited",
    "INFY": "Infosys Limited",
    "ICICIBANK": "ICICI Bank Limited",
}

# Reverse mapping
COMPANY_TO_TICKER = {v: k for k, v in KNOWN_TICKERS.items()}


def extract_tickers(text: str) -> List[str]:
    """
    Extract stock ticker symbols from text.
    """
    tickers = []
    
    # 1. Find $SYMBOL patterns (case-insensitive for the find, but norm to upper)
    dollar_tickers = re.findall(r'\$([A-Za-z]{1,5})\b', text)
    tickers.extend([t.upper() for t in dollar_tickers])
    
    # 2. Split text into words and check if any word (case-insensitive) matches KNOWN_TICKERS
    # This handles "Reliance" -> "RELIANCE"
    words = re.findall(r'\b[A-Za-z]{2,10}\b', text)
    for word in words:
        u_word = word.upper()
        if u_word in KNOWN_TICKERS:
            tickers.append(u_word)
    
    # 3. Check for standalone uppercase symbols
    standalone = STANDALONE_TICKER_PATTERN.findall(text)
    for symbol in standalone:
        if symbol in KNOWN_TICKERS and symbol not in tickers:
            tickers.append(symbol)
    
    # Remove duplicates while preserving order
    seen = set()
    unique_tickers = []
    for ticker in tickers:
        if ticker not in seen:
            unique_tickers.append(ticker)
            seen.add(ticker)
    
    return unique_tickers


def resolve_ticker(ticker: str) -> Optional[Dict[str, Any]]:
    """Resolve ticker symbol to company information."""
    ticker = ticker.upper()
    if ticker in KNOWN_TICKERS:
        return {
            "ticker": ticker,
            "company_name": KNOWN_TICKERS[ticker],
            "source": "known_mapping",
            "confidence": 1.0,
        }
    return None


def resolve_company_to_ticker(company_name: str) -> Optional[str]:
    """Resolve company name to ticker symbol."""
    if not company_name:
        return None
        
    # Check known mappings first
    name_clean = company_name.upper().strip()
    
    # Direct match on ticker key
    if name_clean in KNOWN_TICKERS:
        return name_clean
        
    # Match on company name expansion
    for ticker, name in KNOWN_TICKERS.items():
        if name_clean in name.upper() or name.upper() in name_clean:
            return ticker
    
    # Try Alpha Vantage search only if key exists
    from app.config import ALPHAVANTAGE_API_KEY
    if ALPHAVANTAGE_API_KEY:
        try:
            results = search_symbol(company_name)
            if results:
                return results[0].get("1. symbol")
        except Exception as e:
            logger.debug(f"Search resolution failed: {e}")
    
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
