import logging
from typing import Dict, Any, List
from app.agents._model import call_model

logger = logging.getLogger(__name__)

def run(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Mental Scratchpad Agent: Deliberates on strategy for complex queries.
    This effectively adds "virtual parameters" to Janus's architecture.
    """
    user_input = state.get("user_input", "")
    route = state.get("route", {})
    context = state.get("context", {})
    adaptive = context.get("adaptive_intelligence", {})
    personality = adaptive.get("system_personality", {})
    
    # Internal Architectural Parameters
    breadth = personality.get("cognitive_breadth", 0.5)
    depth = personality.get("analytical_depth", 0.7)
    
    prompt = f"""You are the Janus Mental Scratchpad. 
Your role is to deliberate on the STRATEGY for a complex query before any research is performed.

USER QUERY: {user_input}
DOMAINS DETECTED: {route.get('domain', 'general')}

COGNITIVE PARAMETERS:
- Breadth: {breadth}
- Depth: {depth}

INSTRUCTIONS:
1. Deconstruct the user query into its core logical components.
2. Identify potential contradictions or hidden assumptions that research should address.
3. Determine the optimal "Reasoning Path" (how Janus should connect the dots later).
4. Do NOT answer the question. Only provide the ARCHITECTURAL STRATEGY.

Structure your response with a <think> block for your own deliberation, then provide:
- STRATEGIC_VECTORS: List of angles research must cover.
- POTENTIAL_BIASES: Any biases or assumptions in the query.
- SYNTHESIS_PLAN: How the final answer should be structured to be most impactful.
"""

    try:
        # We always use the "High IQ" tier for the scratchpad if possible
        response = call_model([{"role": "user", "content": prompt}], personality=personality)
        return {**state, "scratchpad": {"strategy": response}}
    except Exception as e:
        logger.error(f"[AGENT ERROR] mental_scratchpad: {e}")
        return {**state, "scratchpad": {"error": str(e)}}
