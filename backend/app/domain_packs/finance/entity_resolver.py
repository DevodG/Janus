"""
Entity resolver for finance domain pack.

Extracts and normalizes financial entities (companies, people, organizations)
from text.
"""

import re
from typing import List, Dict, Any, Set
import logging

logger = logging.getLogger(__name__)


# Common financial entity patterns
COMPANY_SUFFIXES = [
    "Inc", "Corp", "Corporation", "Ltd", "Limited", "LLC", "LP", "LLP",
    "Co", "Company", "Group", "Holdings", "Partners", "Capital", "Ventures",
    "Technologies", "Systems", "Solutions", "Services", "Enterprises"
]

# Known major companies (expandable)
KNOWN_COMPANIES = {
    "apple": "Apple Inc.",
    "microsoft": "Microsoft Corporation",
    "google": "Alphabet Inc.",
    "alphabet": "Alphabet Inc.",
    "amazon": "Amazon.com Inc.",
    "meta": "Meta Platforms Inc.",
    "facebook": "Meta Platforms Inc.",
    "tesla": "Tesla Inc.",
    "nvidia": "NVIDIA Corporation",
    "berkshire": "Berkshire Hathaway Inc.",
    "jpmorgan": "JPMorgan Chase & Co.",
    "visa": "Visa Inc.",
    "walmart": "Walmart Inc.",
    "exxon": "Exxon Mobil Corporation",
    "johnson": "Johnson & Johnson",
}


def extract_entities(text: str) -> List[Dict[str, Any]]:
    """
    Extract financial entities from text.
    
    Args:
        text: Input text
        
    Returns:
        List of extracted entities with metadata
    """
    entities = []
    seen: Set[str] = set()
    
    # Extract company names with suffixes
    for suffix in COMPANY_SUFFIXES:
        pattern = rf'\b([A-Z][a-zA-Z&\s]+)\s+{suffix}\b'
        matches = re.finditer(pattern, text)
        for match in matches:
            full_name = match.group(0)
            if full_name not in seen:
                entities.append({
                    "text": full_name,
                    "type": "company",
                    "confidence": 0.9,
                    "source": "pattern_match"
                })
                seen.add(full_name)
    
    # Check for known companies
    text_lower = text.lower()
    for key, canonical_name in KNOWN_COMPANIES.items():
        if key in text_lower and canonical_name not in seen:
            entities.append({
                "text": canonical_name,
                "type": "company",
                "confidence": 1.0,
                "source": "known_entity"
            })
            seen.add(canonical_name)
    
    # Extract potential CEO/executive names (capitalized names near titles)
    exec_pattern = r'\b(CEO|CFO|CTO|COO|President|Chairman|Director|Executive)\s+([A-Z][a-z]+\s+[A-Z][a-z]+)'
    matches = re.finditer(exec_pattern, text)
    for match in matches:
        title = match.group(1)
        name = match.group(2)
        if name not in seen:
            entities.append({
                "text": name,
                "type": "person",
                "role": title,
                "confidence": 0.8,
                "source": "title_pattern"
            })
            seen.add(name)
    
    logger.info(f"Extracted {len(entities)} entities from text")
    return entities


def normalize_company_name(name: str) -> str:
    """
    Normalize company name to canonical form.
    
    Args:
        name: Company name
        
    Returns:
        Normalized company name
    """
    # Check known companies first
    name_lower = name.lower()
    for key, canonical in KNOWN_COMPANIES.items():
        if key in name_lower:
            return canonical
    
    # Otherwise return cleaned version
    # Remove extra whitespace
    normalized = " ".join(name.split())
    
    # Capitalize properly
    words = normalized.split()
    normalized = " ".join(
        word.upper() if word.upper() in ["LLC", "LP", "LLP", "USA", "UK"] 
        else word.capitalize() 
        for word in words
    )
    
    return normalized


def resolve_entity(entity_text: str) -> Dict[str, Any]:
    """
    Resolve entity to canonical form with metadata.
    
    Args:
        entity_text: Entity text to resolve
        
    Returns:
        Dictionary with resolved entity information
    """
    normalized = normalize_company_name(entity_text)
    
    return {
        "original": entity_text,
        "normalized": normalized,
        "type": "company" if any(suffix in normalized for suffix in COMPANY_SUFFIXES) else "unknown",
        "confidence": 0.7,
    }
