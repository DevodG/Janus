"""
Event analyzer for finance domain pack.

Analyzes financial events and their potential market impact.
"""

from typing import Dict, Any, List
import re
import logging

logger = logging.getLogger(__name__)


# Event categories and their typical impact
EVENT_CATEGORIES = {
    "earnings": {
        "keywords": ["earnings", "quarterly results", "q1", "q2", "q3", "q4", "eps", "revenue"],
        "typical_impact": "high",
        "volatility": "high",
    },
    "merger_acquisition": {
        "keywords": ["merger", "acquisition", "takeover", "buyout", "deal"],
        "typical_impact": "very_high",
        "volatility": "very_high",
    },
    "regulatory": {
        "keywords": ["sec", "investigation", "lawsuit", "fine", "penalty", "regulation"],
        "typical_impact": "high",
        "volatility": "high",
    },
    "product_launch": {
        "keywords": ["launch", "release", "unveil", "announce", "new product"],
        "typical_impact": "medium",
        "volatility": "medium",
    },
    "executive_change": {
        "keywords": ["ceo", "cfo", "resign", "appoint", "hire", "fire", "step down"],
        "typical_impact": "medium",
        "volatility": "medium",
    },
    "guidance": {
        "keywords": ["guidance", "forecast", "outlook", "projection", "estimate"],
        "typical_impact": "high",
        "volatility": "high",
    },
    "dividend": {
        "keywords": ["dividend", "payout", "distribution", "yield"],
        "typical_impact": "low",
        "volatility": "low",
    },
    "fed_policy": {
        "keywords": ["federal reserve", "fed", "interest rate", "monetary policy", "fomc"],
        "typical_impact": "very_high",
        "volatility": "very_high",
    },
}


def detect_event_type(text: str) -> List[Dict[str, Any]]:
    """
    Detect financial event types in text.
    
    Args:
        text: Text to analyze
        
    Returns:
        List of detected event types with metadata
    """
    text_lower = text.lower()
    detected_events = []
    
    for event_type, info in EVENT_CATEGORIES.items():
        matches = []
        for keyword in info["keywords"]:
            if keyword in text_lower:
                matches.append(keyword)
        
        if matches:
            detected_events.append({
                "event_type": event_type,
                "matched_keywords": matches,
                "typical_impact": info["typical_impact"],
                "volatility": info["volatility"],
                "confidence": min(len(matches) * 0.3, 1.0),
            })
    
    logger.info(f"Detected {len(detected_events)} event types")
    return detected_events


def analyze_event_impact(text: str, event_types: List[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Analyze potential market impact of events.
    
    Args:
        text: Text describing the event
        event_types: Pre-detected event types (optional)
        
    Returns:
        Impact analysis
    """
    if event_types is None:
        event_types = detect_event_type(text)
    
    if not event_types:
        return {
            "impact_level": "unknown",
            "volatility_level": "unknown",
            "confidence": 0.0,
        }
    
    # Aggregate impact levels
    impact_scores = {
        "very_high": 1.0,
        "high": 0.75,
        "medium": 0.5,
        "low": 0.25,
        "unknown": 0.0,
    }
    
    impacts = [impact_scores.get(e["typical_impact"], 0.0) for e in event_types]
    avg_impact = sum(impacts) / len(impacts) if impacts else 0.0
    
    # Determine impact level
    if avg_impact >= 0.85:
        impact_level = "very_high"
    elif avg_impact >= 0.65:
        impact_level = "high"
    elif avg_impact >= 0.4:
        impact_level = "medium"
    else:
        impact_level = "low"
    
    # Aggregate volatility
    volatility_scores = {
        "very_high": 1.0,
        "high": 0.75,
        "medium": 0.5,
        "low": 0.25,
        "unknown": 0.0,
    }
    
    volatilities = [volatility_scores.get(e["volatility"], 0.0) for e in event_types]
    avg_volatility = sum(volatilities) / len(volatilities) if volatilities else 0.0
    
    if avg_volatility >= 0.85:
        volatility_level = "very_high"
    elif avg_volatility >= 0.65:
        volatility_level = "high"
    elif avg_volatility >= 0.4:
        volatility_level = "medium"
    else:
        volatility_level = "low"
    
    # Calculate confidence
    confidences = [e["confidence"] for e in event_types]
    avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
    
    return {
        "impact_level": impact_level,
        "volatility_level": volatility_level,
        "confidence": avg_confidence,
        "detected_events": event_types,
        "event_count": len(event_types),
    }


def extract_event_timeline(text: str) -> List[Dict[str, Any]]:
    """
    Extract timeline information from event description.
    
    Args:
        text: Text to analyze
        
    Returns:
        List of timeline markers
    """
    timeline = []
    
    # Date patterns
    date_patterns = [
        r'\b(\d{1,2}/\d{1,2}/\d{2,4})\b',  # MM/DD/YYYY
        r'\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b',
        r'\b(Q[1-4]\s+\d{4})\b',  # Q1 2024
    ]
    
    for pattern in date_patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            timeline.append({
                "date_text": match.group(0),
                "position": match.start(),
                "type": "date",
            })
    
    # Time indicators
    time_indicators = [
        "today", "tomorrow", "yesterday", "next week", "next month",
        "this quarter", "next quarter", "this year", "next year",
        "upcoming", "soon", "recently", "last week", "last month",
    ]
    
    text_lower = text.lower()
    for indicator in time_indicators:
        if indicator in text_lower:
            timeline.append({
                "date_text": indicator,
                "type": "relative_time",
            })
    
    logger.info(f"Extracted {len(timeline)} timeline markers")
    return timeline
