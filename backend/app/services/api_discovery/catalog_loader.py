"""
Catalog loader for public-apis dataset.
"""

import json
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
import httpx

logger = logging.getLogger(__name__)

# GitHub raw URL for public-apis catalog
PUBLIC_APIS_URL = "https://raw.githubusercontent.com/public-apis/public-apis/master/entries.json"
CACHE_FILE = Path(__file__).parent.parent.parent / "data" / "api_catalog_cache.json"


def load_public_apis_catalog(use_cache: bool = True) -> List[Dict[str, Any]]:
    """
    Load public-apis catalog from GitHub or local cache.
    
    Args:
        use_cache: If True, use local cache if available
        
    Returns:
        List of API entries with:
        - API: API name
        - Description: API description
        - Auth: Auth type (apiKey, OAuth, None, etc.)
        - HTTPS: HTTPS support (True/False)
        - Cors: CORS support (yes/no/unknown)
        - Category: API category
        - Link: API documentation URL
    """
    # Try to load from cache first
    if use_cache and CACHE_FILE.exists():
        try:
            logger.info("Loading API catalog from cache")
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            logger.info(f"Loaded {len(data.get('entries', []))} APIs from cache")
            return data.get("entries", [])
        except Exception as e:
            logger.warning(f"Failed to load cache: {e}")
    
    # Fetch from GitHub
    try:
        logger.info("Fetching API catalog from GitHub")
        with httpx.Client(timeout=30) as client:
            response = client.get(PUBLIC_APIS_URL)
            response.raise_for_status()
            data = response.json()
        
        entries = data.get("entries", [])
        logger.info(f"Fetched {len(entries)} APIs from GitHub")
        
        # Save to cache
        try:
            CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            logger.info("Saved API catalog to cache")
        except Exception as e:
            logger.warning(f"Failed to save cache: {e}")
        
        return entries
    
    except Exception as e:
        logger.error(f"Failed to fetch API catalog: {e}")
        return []


def get_api_by_name(name: str) -> Optional[Dict[str, Any]]:
    """Get a specific API by name."""
    catalog = load_public_apis_catalog()
    for api in catalog:
        if api.get("API", "").lower() == name.lower():
            return api
    return None


def get_apis_by_category(category: str) -> List[Dict[str, Any]]:
    """Get all APIs in a specific category."""
    catalog = load_public_apis_catalog()
    return [api for api in catalog if api.get("Category", "").lower() == category.lower()]
