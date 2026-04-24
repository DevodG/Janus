"""
Rumor detector for finance domain pack.

Detects potential rumors and unverified claims in financial content.
"""

import re
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)


# Rumor indicator patterns
RUMOR_INDICATORS = [
    # Hedging language
    r'\b(allegedly|reportedly|rumor|rumored|speculation|speculated|unconfirmed|unverified)\b',
    r'\b(sources say|sources claim|insider|insiders|anonymous source)\b',
    r'\b(could be|might be|may be|possibly|potentially)\b',
    
    # Vague attribution
    r'\b(some say|people say|word is|buzz is|chatter|whispers)\b',
    r'\b(according to rumors|according to speculation)\b',
    
    # Sensational language
    r'\b(shocking|bombshell|explosive|leaked|secret)\b',
]

# Verification indicators (opposite of rumors)
VERIFICATION_INDICATORS = [
    r'\b(confirmed|verified|official|announced|disclosed|filed)\b',
    r'\b(sec filing|press release|earnings report|official statement)\b',
    r'\b(ceo said|cfo said|company announced)\b',
]


def detect_rumor_indicators(text: str) -> Dict[str, Any]:
    """
    Detect rumor indicators in text.
    
    Args:
        text: Text to analyze
        
    Returns:
        Dictionary with rumor detection results
    """
    text_lower = text.lower()
    
    # Count rumor indicators
    rumor_matches = []
    for pattern in RUMOR_INDICATORS:
        matches = re.finditer(pattern, text_lower, re.IGNORECASE)
        for match in matches:
            rumor_matches.append({
                "text": match.group(0),
                "position": match.start(),
                "type": "rumor_indicator",
            })
    
    # Count verification indicators
    verification_matches = []
    for pattern in VERIFICATION_INDICATORS:
        matches = re.finditer(pattern, text_lower, re.IGNORECASE)
        for match in matches:
            verification_matches.append({
                "text": match.group(0),
                "position": match.start(),
                "type": "verification_indicator",
            })
    
    # Calculate rumor score (0-1, higher = more likely rumor)
    rumor_count = len(rumor_matches)
    verification_count = len(verification_matches)
    
    if rumor_count == 0 and verification_count == 0:
        rumor_score = 0.5  # Neutral
    else:
        # Score based on ratio
        total = rumor_count + verification_count
        rumor_score = rumor_count / total if total > 0 else 0.5
    
    # Adjust for absolute counts
    if rumor_count >= 3:
        rumor_score = min(rumor_score + 0.2, 1.0)
    if verification_count >= 2:
        rumor_score = max(rumor_score - 0.2, 0.0)
    
    assessment = "likely_rumor" if rumor_score >= 0.7 else \
                 "possible_rumor" if rumor_score >= 0.5 else \
                 "likely_verified"
    
    logger.info(f"Rumor detection: score={rumor_score:.2f}, assessment={assessment}")
    
    return {
        "rumor_score": rumor_score,
        "assessment": assessment,
        "rumor_indicators": rumor_matches,
        "verification_indicators": verification_matches,
        "rumor_count": rumor_count,
        "verification_count": verification_count,
    }


def check_claim_verification(claim: str, sources: List[str]) -> Dict[str, Any]:
    """
    Check if a claim is verified by credible sources.
    
    Args:
        claim: Claim to verify
        sources: List of source URLs
        
    Returns:
        Verification assessment
    """
    from app.domain_packs.finance.source_checker import aggregate_source_scores
    
    # Detect rumor indicators in the claim itself
    rumor_detection = detect_rumor_indicators(claim)
    
    # Check source credibility
    source_assessment = aggregate_source_scores(sources)
    
    # Combine assessments
    is_verified = (
        rumor_detection["rumor_score"] < 0.5 and
        source_assessment["average_score"] >= 0.7
    )
    
    confidence = (1 - rumor_detection["rumor_score"]) * source_assessment["average_score"]
    
    return {
        "claim": claim,
        "is_verified": is_verified,
        "confidence": confidence,
        "rumor_detection": rumor_detection,
        "source_assessment": source_assessment,
        "recommendation": "trust" if is_verified else "verify_further" if confidence >= 0.5 else "skeptical",
    }
