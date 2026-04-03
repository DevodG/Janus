import re
from app.agents._model import call_model, LLMProviderError
import logging

logger = logging.getLogger(__name__)

_CONFIDENCE_PATTERN = re.compile(r'Confidence:\s*([\d.]+)', re.IGNORECASE)
_UNCERTAINTY_PATTERN = re.compile(r'Uncertainty\s*Level:\s*(HIGH|MEDIUM|LOW)', re.IGNORECASE)


def _extract_confidence(text: str, default: float = 0.5) -> float:
    """Extract confidence score from structured LLM output."""
    match = _CONFIDENCE_PATTERN.search(text)
    if match:
        try:
            score = float(match.group(1))
            return max(0.0, min(1.0, score))
        except ValueError:
            pass
    return default


def _extract_uncertainty(text: str) -> str:
    """Extract uncertainty level from structured LLM output."""
    match = _UNCERTAINTY_PATTERN.search(text)
    if match:
        return match.group(1).upper()
    
    # Fallback heuristic
    text_lower = text.lower()
    uncertainty_indicators = ["uncertain", "unclear", "missing", "unverified",
                              "assumption", "unknown", "speculative", "conflicting",
                              "limited evidence", "cannot confirm"]
    count = sum(1 for indicator in uncertainty_indicators if indicator in text_lower)
    
    if count >= 4:
        return "HIGH"
    elif count >= 2:
        return "MEDIUM"
    return "LOW"


def run_synthesizer(
    user_input: str,
    research_output: str,
    planner_output: str,
    verifier_output: str,
    prompt_template: str
) -> dict:
    # Extract uncertainty level from verifier output (or synthesizer will self-assess)
    uncertainty_level = _extract_uncertainty(verifier_output)
    
    # Check if simulation was recommended by planner or verifier
    planner_lower = planner_output.lower()
    simulation_recommended = (
        ("simulation recommended: yes" in planner_lower) or
        ("simulation" in planner_lower and "recommend" in planner_lower)
    )
    
    logger.info(f"Synthesizer: uncertainty_level={uncertainty_level}, simulation_recommended={simulation_recommended}")
    
    prompt = (
        f"{prompt_template}\n\n"
        f"User Request:\n{user_input}\n\n"
        f"Research Packet:\n{research_output}\n\n"
        f"Planner Output:\n{planner_output}\n\n"
        f"Verifier Output:\n{verifier_output}"
    )

    try:
        text = call_model(prompt, mode="chat")
        confidence = _extract_confidence(text, default=0.60)
        
        # Also try to extract uncertainty from synthesizer's own output
        synth_uncertainty = _extract_uncertainty(text)
        # Use the higher uncertainty between verifier and synthesizer
        if synth_uncertainty == "HIGH" or uncertainty_level == "HIGH":
            final_uncertainty = "HIGH"
        elif synth_uncertainty == "MEDIUM" or uncertainty_level == "MEDIUM":
            final_uncertainty = "MEDIUM"
        else:
            final_uncertainty = "LOW"
        
        return {
            "agent": "synthesizer",
            "summary": text,
            "details": {
                "model_mode": "chat",
                "uncertainty_level": final_uncertainty,
                "simulation_recommended": simulation_recommended
            },
            "confidence": confidence,
        }
    except LLMProviderError as e:
        return {
            "agent": "synthesizer",
            "summary": f"Error: {str(e)}",
            "details": {"error_type": "provider_error"},
            "confidence": 0.0,
        }
