"""
Prediction support module for finance domain pack.

Provides structured support for financial predictions and forecasts.
Note: This module does NOT make actual predictions, but helps structure
prediction-related analysis and uncertainty quantification.
"""

from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)


def structure_prediction_context(
    query: str,
    entities: List[Dict[str, Any]],
    events: List[Dict[str, Any]],
    stance: Dict[str, Any],
    sources: List[str]
) -> Dict[str, Any]:
    """
    Structure context for prediction-related queries.
    
    Args:
        query: User's prediction query
        entities: Extracted entities
        events: Detected events
        stance: Market stance analysis
        sources: Information sources
        
    Returns:
        Structured prediction context
    """
    from app.domain_packs.finance.source_checker import aggregate_source_scores
    
    # Assess source credibility
    source_assessment = aggregate_source_scores(sources)
    
    # Determine prediction type
    query_lower = query.lower()
    prediction_type = "unknown"
    
    if any(word in query_lower for word in ["price", "stock", "value", "worth"]):
        prediction_type = "price_movement"
    elif any(word in query_lower for word in ["earnings", "revenue", "profit"]):
        prediction_type = "financial_performance"
    elif any(word in query_lower for word in ["market", "sector", "industry"]):
        prediction_type = "market_trend"
    elif any(word in query_lower for word in ["merger", "acquisition", "deal"]):
        prediction_type = "corporate_action"
    
    # Calculate uncertainty factors
    uncertainty_factors = []
    
    if source_assessment["average_score"] < 0.7:
        uncertainty_factors.append("low_source_credibility")
    
    if stance.get("confidence", 0) < 0.6:
        uncertainty_factors.append("mixed_market_sentiment")
    
    if len(events) == 0:
        uncertainty_factors.append("no_clear_catalysts")
    
    if len(entities) == 0:
        uncertainty_factors.append("unclear_target_entities")
    
    uncertainty_level = "high" if len(uncertainty_factors) >= 3 else \
                       "medium" if len(uncertainty_factors) >= 1 else \
                       "low"
    
    return {
        "prediction_type": prediction_type,
        "target_entities": entities,
        "relevant_events": events,
        "market_stance": stance,
        "source_credibility": source_assessment,
        "uncertainty_level": uncertainty_level,
        "uncertainty_factors": uncertainty_factors,
        "recommendation": "high_confidence_analysis" if uncertainty_level == "low" else
                         "moderate_confidence_analysis" if uncertainty_level == "medium" else
                         "low_confidence_analysis",
    }


def quantify_prediction_uncertainty(
    prediction_context: Dict[str, Any],
    additional_factors: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Quantify uncertainty in prediction context.
    
    Args:
        prediction_context: Structured prediction context
        additional_factors: Additional uncertainty factors
        
    Returns:
        Uncertainty quantification
    """
    base_uncertainty = 0.5  # Start with 50% uncertainty
    
    # Adjust based on source credibility
    source_score = prediction_context.get("source_credibility", {}).get("average_score", 0.5)
    base_uncertainty -= (source_score - 0.5) * 0.3
    
    # Adjust based on market stance confidence
    stance_confidence = prediction_context.get("market_stance", {}).get("confidence", 0.5)
    base_uncertainty -= (stance_confidence - 0.5) * 0.2
    
    # Adjust based on event clarity
    event_count = len(prediction_context.get("relevant_events", []))
    if event_count > 0:
        base_uncertainty -= 0.1
    
    # Adjust based on entity clarity
    entity_count = len(prediction_context.get("target_entities", []))
    if entity_count > 0:
        base_uncertainty -= 0.1
    
    # Apply additional factors
    if additional_factors:
        if additional_factors.get("high_volatility"):
            base_uncertainty += 0.15
        if additional_factors.get("conflicting_signals"):
            base_uncertainty += 0.2
        if additional_factors.get("limited_data"):
            base_uncertainty += 0.15
    
    # Clamp to 0-1 range
    uncertainty_score = max(0.0, min(1.0, base_uncertainty))
    
    confidence_score = 1.0 - uncertainty_score
    
    return {
        "uncertainty_score": uncertainty_score,
        "confidence_score": confidence_score,
        "uncertainty_level": prediction_context.get("uncertainty_level", "unknown"),
        "factors": prediction_context.get("uncertainty_factors", []),
        "recommendation": "proceed_with_caution" if uncertainty_score >= 0.7 else
                         "moderate_confidence" if uncertainty_score >= 0.4 else
                         "reasonable_confidence",
    }


def suggest_simulation_scenarios(prediction_context: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Suggest simulation scenarios based on prediction context.
    
    Args:
        prediction_context: Structured prediction context
        
    Returns:
        List of suggested simulation scenarios
    """
    scenarios = []
    
    prediction_type = prediction_context.get("prediction_type", "unknown")
    events = prediction_context.get("relevant_events", [])
    
    if prediction_type == "price_movement":
        scenarios.append({
            "scenario": "bull_case",
            "description": "Optimistic price movement scenario",
            "parameters": {"sentiment": "positive", "volatility": "moderate"},
        })
        scenarios.append({
            "scenario": "bear_case",
            "description": "Pessimistic price movement scenario",
            "parameters": {"sentiment": "negative", "volatility": "moderate"},
        })
        scenarios.append({
            "scenario": "base_case",
            "description": "Neutral price movement scenario",
            "parameters": {"sentiment": "neutral", "volatility": "low"},
        })
    
    if prediction_type == "market_trend":
        scenarios.append({
            "scenario": "sector_rotation",
            "description": "Capital flows between sectors",
            "parameters": {"market_phase": "rotation"},
        })
    
    # Add event-specific scenarios
    for event in events:
        event_type = event.get("event_type")
        if event_type == "earnings":
            scenarios.append({
                "scenario": "earnings_beat",
                "description": "Company beats earnings expectations",
                "parameters": {"event": "earnings", "outcome": "positive"},
            })
            scenarios.append({
                "scenario": "earnings_miss",
                "description": "Company misses earnings expectations",
                "parameters": {"event": "earnings", "outcome": "negative"},
            })
    
    logger.info(f"Suggested {len(scenarios)} simulation scenarios")
    return scenarios
