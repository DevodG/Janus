"""
Scam detector for finance domain pack.

Detects potential financial scams and fraudulent schemes.
"""

import re
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)


# Scam indicator patterns
SCAM_PATTERNS = [
    # Get-rich-quick schemes
    r'\b(get rich quick|make money fast|guaranteed returns|no risk)\b',
    r'\b(double your money|triple your investment|10x returns)\b',
    r'\b(passive income|work from home|financial freedom)\b',
    
    # Pressure tactics
    r'\b(act now|limited time|urgent|don\'t miss out|last chance)\b',
    r'\b(exclusive offer|secret|insider tip|hidden opportunity)\b',
    
    # Unrealistic promises
    r'\b(guaranteed profit|risk-free|100% return|never lose)\b',
    r'\b(foolproof|can\'t lose|sure thing|no-brainer)\b',
    
    # Pyramid/MLM indicators
    r'\b(recruit|downline|upline|multi-level|network marketing)\b',
    r'\b(join my team|be your own boss|financial independence)\b',
    
    # Crypto scams
    r'\b(airdrop|free crypto|token giveaway|pump and dump)\b',
    r'\b(send.*receive back|double your bitcoin)\b',
    
    # Phishing/fraud
    r'\b(verify your account|suspended account|unusual activity)\b',
    r'\b(click here immediately|update payment|confirm identity)\b',
]

# Known scam keywords
HIGH_RISK_KEYWORDS = [
    "ponzi", "pyramid scheme", "advance fee", "419 scam",
    "pump and dump", "rug pull", "exit scam", "phishing",
]


def detect_scam_indicators(text: str) -> Dict[str, Any]:
    """
    Detect scam indicators in text.
    
    Args:
        text: Text to analyze
        
    Returns:
        Dictionary with scam detection results
    """
    text_lower = text.lower()
    
    # Find pattern matches
    matches = []
    for pattern in SCAM_PATTERNS:
        found = re.finditer(pattern, text_lower, re.IGNORECASE)
        for match in found:
            matches.append({
                "text": match.group(0),
                "position": match.start(),
                "type": "scam_pattern",
            })
    
    # Check for high-risk keywords
    high_risk_found = []
    for keyword in HIGH_RISK_KEYWORDS:
        if keyword in text_lower:
            high_risk_found.append(keyword)
    
    # Calculate scam score (0-1, higher = more likely scam)
    pattern_score = min(len(matches) * 0.15, 0.8)
    keyword_score = min(len(high_risk_found) * 0.3, 0.9)
    
    scam_score = max(pattern_score, keyword_score)
    
    # Adjust for multiple indicators
    if len(matches) >= 5:
        scam_score = min(scam_score + 0.2, 1.0)
    
    risk_level = "high_risk" if scam_score >= 0.7 else \
                 "medium_risk" if scam_score >= 0.4 else \
                 "low_risk"
    
    logger.info(f"Scam detection: score={scam_score:.2f}, risk={risk_level}")
    
    return {
        "scam_score": scam_score,
        "risk_level": risk_level,
        "pattern_matches": matches,
        "high_risk_keywords": high_risk_found,
        "match_count": len(matches),
        "keyword_count": len(high_risk_found),
    }


def check_investment_legitimacy(
    description: str,
    promised_return: float = None,
    timeframe: str = None
) -> Dict[str, Any]:
    """
    Check if an investment opportunity appears legitimate.
    
    Args:
        description: Investment description
        promised_return: Promised return percentage (if specified)
        timeframe: Timeframe for returns (if specified)
        
    Returns:
        Legitimacy assessment
    """
    # Detect scam indicators
    scam_detection = detect_scam_indicators(description)
    
    # Check for unrealistic returns
    unrealistic_return = False
    if promised_return is not None:
        # Returns over 20% annually are suspicious
        # Returns over 50% are highly suspicious
        if promised_return > 50:
            unrealistic_return = True
            scam_detection["scam_score"] = min(scam_detection["scam_score"] + 0.3, 1.0)
        elif promised_return > 20:
            unrealistic_return = True
            scam_detection["scam_score"] = min(scam_detection["scam_score"] + 0.15, 1.0)
    
    # Check for short timeframes with high returns
    suspicious_timeframe = False
    if timeframe and promised_return:
        timeframe_lower = timeframe.lower()
        if any(word in timeframe_lower for word in ["day", "days", "week", "weeks"]):
            if promised_return > 10:
                suspicious_timeframe = True
                scam_detection["scam_score"] = min(scam_detection["scam_score"] + 0.2, 1.0)
    
    is_legitimate = scam_detection["scam_score"] < 0.4
    
    return {
        "is_legitimate": is_legitimate,
        "scam_detection": scam_detection,
        "unrealistic_return": unrealistic_return,
        "suspicious_timeframe": suspicious_timeframe,
        "recommendation": "avoid" if scam_detection["scam_score"] >= 0.7 else
                         "investigate_thoroughly" if scam_detection["scam_score"] >= 0.4 else
                         "proceed_with_caution",
        "warnings": [
            "Unrealistic return promises" if unrealistic_return else None,
            "Suspicious timeframe" if suspicious_timeframe else None,
            f"{scam_detection['match_count']} scam indicators found" if scam_detection['match_count'] > 0 else None,
        ],
    }
