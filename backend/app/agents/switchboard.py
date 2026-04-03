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
    task_family = "simulation" if any(k in lower for k in SIMULATION_TRIGGER_KEYWORDS) else "normal"

    # Dimension 2: Domain pack detection
    registry = get_registry()
    detected_domain = registry.detect_domain(user_input)
    domain_pack = detected_domain if detected_domain else "general"

    # Dimension 3: Complexity based on word count
    if task_family == "simulation":
        complexity = "complex"
    elif words <= 5:
        complexity = "simple"
    elif words <= 25:
        complexity = "medium"
    else:
        complexity = "complex"

    # Dimension 4: Execution mode based on complexity
    if task_family == "simulation":
        execution_mode = "deep"
    elif complexity == "simple":
        execution_mode = "solo"
    elif complexity == "medium":
        execution_mode = "standard"
    else:
        execution_mode = "deep"

    return {
        "task_family": task_family,
        "domain_pack": domain_pack,
        "complexity": complexity,
        "execution_mode": execution_mode,
        "risk_level": "medium" if execution_mode == "deep" else "low",
    }
