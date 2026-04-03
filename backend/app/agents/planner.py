import re
from app.agents._model import call_model, LLMProviderError
from app.config import SIMULATION_TRIGGER_KEYWORDS
import logging

logger = logging.getLogger(__name__)

_CONFIDENCE_PATTERN = re.compile(r'Confidence:\s*([\d.]+)', re.IGNORECASE)


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


def run_planner(user_input: str, research_output: str, prompt_template: str) -> dict:
    # Detect if simulation mode would be appropriate
    user_lower = user_input.lower()
    simulation_suggested = any(keyword in user_lower for keyword in SIMULATION_TRIGGER_KEYWORDS)
    
    # Check for scenario/prediction patterns in research
    research_lower = research_output.lower()
    scenario_patterns = ["scenario", "what if", "predict", "forecast", "impact", "reaction",
                         "what would", "how would", "could affect", "might happen"]
    has_scenario_context = any(pattern in research_lower for pattern in scenario_patterns)
    
    # Also check user input for scenario patterns
    user_scenario_patterns = ["what would", "what if", "how would", "what happens",
                              "what could", "imagine", "suppose", "hypothetical"]
    has_user_scenario = any(pattern in user_lower for pattern in user_scenario_patterns)
    
    if (has_scenario_context or has_user_scenario) and not simulation_suggested:
        simulation_suggested = True
        logger.info("Planner detected scenario analysis opportunity - suggesting simulation mode")
    
    prompt = (
        f"{prompt_template}\n\n"
        f"User Request:\n{user_input}\n\n"
        f"Research Packet:\n{research_output}"
    )

    try:
        text = call_model(prompt, mode="chat")
        confidence = _extract_confidence(text, default=0.70)
        
        return {
            "agent": "planner",
            "summary": text,
            "details": {
                "model_mode": "chat",
                "simulation_suggested": simulation_suggested
            },
            "confidence": confidence,
        }
    except LLMProviderError as e:
        return {
            "agent": "planner",
            "summary": f"Error: {str(e)}",
            "details": {"error_type": "provider_error"},
            "confidence": 0.0,
        }
