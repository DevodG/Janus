import re
from app.agents._model import call_model, LLMProviderError
from app.services.external_sources import build_external_context
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


def run_research(user_input: str, prompt_template: str) -> dict:
    external_context = build_external_context(user_input)
    
    # Detect domain and enhance research with domain pack capabilities
    registry = get_registry()
    detected_domain = registry.detect_domain(user_input)
    
    domain_enhanced_context = {}
    if detected_domain:
        logger.info(f"Enhancing research with domain pack: {detected_domain}")
        pack = registry.get_pack(detected_domain)
        if pack:
            try:
                base_context = {
                    "user_input": user_input,
                    "external_context": external_context
                }
                domain_enhanced_context = pack.enhance_research(user_input, base_context)
                logger.info(f"Domain enhancement successful: {detected_domain}")
            except Exception as e:
                logger.warning(f"Domain enhancement failed for {detected_domain}: {e}")
                domain_enhanced_context = {}
    
    # Build enhanced prompt with domain context
    domain_context_str = ""
    if domain_enhanced_context:
        domain_context_str = "\n\nDomain-Specific Context:\n"
        for key, value in domain_enhanced_context.items():
            if value:
                domain_context_str += f"{key}: {value}\n"

    prompt = (
        f"{prompt_template}\n\n"
        f"User Request:\n{user_input}\n\n"
        f"External Context:\n{external_context}"
        f"{domain_context_str}"
    )

    try:
        text = call_model(prompt, mode="chat")
        
        # Extract structured entities from domain enhancement
        entities = domain_enhanced_context.get("entities", []) if domain_enhanced_context else []
        tickers = domain_enhanced_context.get("tickers", []) if domain_enhanced_context else []
        
        # Extract confidence from LLM output (our prompt asks for it)
        confidence = _extract_confidence(text, default=0.65)
        
        return {
            "agent": "research",
            "summary": text,
            "details": {
                "external_context_used": external_context != "No external API context available.",
                "domain_pack": detected_domain or "general",
                "entities": entities,
                "tickers": tickers,
                "domain_enhanced": bool(domain_enhanced_context)
            },
            "confidence": confidence,
        }
    except LLMProviderError as e:
        return {
            "agent": "research",
            "summary": f"Error: {str(e)}",
            "details": {"error_type": "provider_error"},
            "confidence": 0.0,
        }
