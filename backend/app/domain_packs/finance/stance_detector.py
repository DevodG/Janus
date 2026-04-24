"""
Stance detector for finance domain pack.

Detects sentiment and stance (bullish/bearish) in financial content.
"""

import re
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


# Bullish indicators
BULLISH_KEYWORDS = [
    "bullish", "buy", "long", "upgrade", "outperform", "strong buy",
    "positive", "growth", "rally", "surge", "soar", "climb", "gain",
    "beat expectations", "exceed", "record high", "all-time high",
    "momentum", "breakout", "uptrend", "optimistic", "confident",
]

# Bearish indicators
BEARISH_KEYWORDS = [
    "bearish", "sell", "short", "downgrade", "underperform", "strong sell",
    "negative", "decline", "fall", "drop", "plunge", "crash", "loss",
    "miss expectations", "disappoint", "record low", "downturn",
    "weakness", "breakdown", "downtrend", "pessimistic", "concerned",
]

# Neutral indicators
NEUTRAL_KEYWORDS = [
    "hold", "neutral", "maintain", "unchanged", "stable", "flat",
    "sideways", "range-bound", "wait and see", "cautious",
]


def detect_stance(text: str) -> Dict[str, Any]:
    """
    Detect financial stance (bullish/bearish/neutral) in text.
    
    Args:
        text: Text to analyze
        
    Returns:
        Dictionary with stance detection results
    """
    text_lower = text.lower()
    
    # Count keyword occurrences
    bullish_count = sum(1 for keyword in BULLISH_KEYWORDS if keyword in text_lower)
    bearish_count = sum(1 for keyword in BEARISH_KEYWORDS if keyword in text_lower)
    neutral_count = sum(1 for keyword in NEUTRAL_KEYWORDS if keyword in text_lower)
    
    total_count = bullish_count + bearish_count + neutral_count
    
    if total_count == 0:
        # No clear indicators
        stance = "neutral"
        confidence = 0.3
        sentiment_score = 0.5
    else:
        # Calculate sentiment score (-1 to 1)
        # Positive = bullish, negative = bearish
        sentiment_score = (bullish_count - bearish_count) / total_count
        
        # Normalize to 0-1 range
        sentiment_score = (sentiment_score + 1) / 2
        
        # Determine stance
        if bullish_count > bearish_count and bullish_count > neutral_count:
            stance = "bullish"
            confidence = bullish_count / total_count
        elif bearish_count > bullish_count and bearish_count > neutral_count:
            stance = "bearish"
            confidence = bearish_count / total_count
        else:
            stance = "neutral"
            confidence = max(neutral_count / total_count, 0.5)
    
    logger.info(f"Stance detection: {stance} (confidence={confidence:.2f}, sentiment={sentiment_score:.2f})")
    
    return {
        "stance": stance,
        "confidence": confidence,
        "sentiment_score": sentiment_score,
        "bullish_count": bullish_count,
        "bearish_count": bearish_count,
        "neutral_count": neutral_count,
        "total_indicators": total_count,
    }


def analyze_price_action_language(text: str) -> Dict[str, Any]:
    """
    Analyze language describing price action.
    
    Args:
        text: Text to analyze
        
    Returns:
        Price action analysis
    """
    text_lower = text.lower()
    
    # Detect magnitude words
    strong_movement = any(word in text_lower for word in [
        "surge", "soar", "plunge", "crash", "skyrocket", "plummet"
    ])
    
    moderate_movement = any(word in text_lower for word in [
        "rise", "fall", "climb", "drop", "gain", "loss"
    ])
    
    weak_movement = any(word in text_lower for word in [
        "inch", "edge", "slip", "dip", "tick"
    ])
    
    # Detect direction
    upward = any(word in text_lower for word in [
        "up", "higher", "gain", "rise", "climb", "rally", "surge"
    ])
    
    downward = any(word in text_lower for word in [
        "down", "lower", "loss", "fall", "drop", "decline", "plunge"
    ])
    
    magnitude = "strong" if strong_movement else \
                "moderate" if moderate_movement else \
                "weak" if weak_movement else \
                "unclear"
    
    direction = "upward" if upward and not downward else \
                "downward" if downward and not upward else \
                "mixed" if upward and downward else \
                "unclear"
    
    return {
        "magnitude": magnitude,
        "direction": direction,
        "strong_movement": strong_movement,
        "moderate_movement": moderate_movement,
        "weak_movement": weak_movement,
    }
