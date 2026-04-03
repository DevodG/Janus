import re
from app.agents._model import call_model, LLMProviderError
from app.domain_packs.registry import get_registry
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


def run_verifier(user_input: str, research_output: str, planner_output: str, prompt_template: str) -> dict:
    # Detect domain and enhance verification with domain pack capabilities
    registry = get_registry()
    detected_domain = registry.detect_domain(user_input)
    
    domain_verification = {}
    if detected_domain:
        logger.info(f"Enhancing verification with domain pack: {detected_domain}")
        pack = registry.get_pack(detected_domain)
        if pack:
            try:
                # Extract claims from research and planner outputs for verification
                claims = []
                for line in (research_output + "\n" + planner_output).split("\n"):
                    stripped = line.strip()
                    if stripped and len(stripped) > 20 and not stripped.startswith(("Facts:", "Assumptions:", "Open Questions:", "Key Facts:", "Plan:", "Objective:")):
                        claims.append(stripped)
                
                context = {
                    "user_input": user_input,
                    "research_output": research_output,
                    "planner_output": planner_output,
                    "claims": claims[:30]  # Limit claims to avoid token overflow
                }
                domain_verification = pack.enhance_verification(claims[:30], context)
                logger.info(f"Domain verification successful: {detected_domain}")
            except Exception as e:
                logger.warning(f"Domain verification failed for {detected_domain}: {e}")
                domain_verification = {}
    
    # Build enhanced prompt with domain verification
    domain_verification_str = ""
    if domain_verification:
        domain_verification_str = "\n\nDomain-Specific Verification:\n"
        for key, value in domain_verification.items():
            if value:
                domain_verification_str += f"{key}: {value}\n"
    
    prompt = (
        f"{prompt_template}\n\n"
        f"User Request:\n{user_input}\n\n"
        f"Research Packet:\n{research_output}\n\n"
        f"Planner Output:\n{planner_output}"
        f"{domain_verification_str}"
    )

    try:
        text = call_model(prompt, mode="reasoner")
        
        # Extract confidence from LLM output
        confidence = _extract_confidence(text, default=0.70)
        
        # Extract structured verification results
        credibility_score = domain_verification.get("credibility_score", 0.5) if domain_verification else 0.5
        rumors_detected = domain_verification.get("rumors_detected", []) if domain_verification else []
        scams_detected = domain_verification.get("scams_detected", []) if domain_verification else []
        
        return {
            "agent": "verifier",
            "summary": text,
            "details": {
                "model_mode": "reasoner",
                "domain_pack": detected_domain or "general",
                "credibility_score": credibility_score,
                "rumors_detected": rumors_detected,
                "scams_detected": scams_detected,
                "domain_verified": bool(domain_verification)
            },
            "confidence": confidence,
        }
    except LLMProviderError as e:
        return {
            "agent": "verifier",
            "summary": f"Error: {str(e)}",
            "details": {"error_type": "provider_error"},
            "confidence": 0.0,
        }
