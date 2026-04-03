from app.config import SIMULATION_TRIGGER_KEYWORDS
from app.domain_packs.registry import get_registry


def decide_route(user_input: str) -> dict:
    """
    Classify task and determine execution path.
    
    Classification dimensions:
    1. task_family: "normal" or "simulation"
    2. domain_pack: "finance", "general", "policy", "custom"
    3. complexity: "simple" (≤5 words), "medium" (≤25 words), "complex" (>25 words)
    4. execution_mode: "solo", "standard", "deep"
    
    Args:
        user_input: The user's query
        
    Returns:
        Dictionary with routing decision including all four dimensions
    """
    text = user_input.strip()
    lower = text.lower()
    words = len(text.split())

    # Dimension 1: Task family (simulation detection)
    # Check configured keywords
    task_family = "simulation" if any(k in lower for k in SIMULATION_TRIGGER_KEYWORDS) else "normal"

    # Additional scenario patterns that should also trigger deep analysis
    scenario_patterns = [
        "what would", "what if", "how would", "what happens if",
        "what could", "imagine if", "suppose", "hypothetical",
        "could affect", "might impact", "would react",
    ]
    is_speculative = any(p in lower for p in scenario_patterns)

    # Dimension 2: Domain pack detection
    registry = get_registry()
    detected_domain = registry.detect_domain(user_input)
    domain_pack = detected_domain if detected_domain else "general"

    # Dimension 3: Complexity based on word count and nature
    if task_family == "simulation":
        complexity = "complex"
    elif is_speculative:
        # Speculative questions always get at least medium complexity
        complexity = "complex" if words > 15 else "medium"
    elif words <= 5:
        complexity = "simple"
    elif words <= 25:
        complexity = "medium"
    else:
        complexity = "complex"

    # Dimension 4: Execution mode based on complexity and nature
    if task_family == "simulation":
        execution_mode = "deep"
    elif is_speculative:
        # Speculative questions always get deep mode (verifier should check uncertainty)
        execution_mode = "deep"
    elif complexity == "simple":
        execution_mode = "solo"
    elif complexity == "medium":
        execution_mode = "standard"
    else:
        execution_mode = "deep"

    # Risk level
    if execution_mode == "deep":
        risk_level = "medium"
    elif is_speculative:
        risk_level = "medium"
    else:
        risk_level = "low"

    return {
        "task_family": task_family,
        "domain_pack": domain_pack,
        "complexity": complexity,
        "execution_mode": execution_mode,
        "risk_level": risk_level,
    }
