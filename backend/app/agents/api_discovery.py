"""
API Discovery Layer client.
Allows agents to query a registry of available APIs and invoke them dynamically.
This enables MiroOrg to expand its tool set without code changes.
"""
import httpx, os
import logging

logger = logging.getLogger(__name__)

DISCOVERY_BASE = os.getenv("API_DISCOVERY_ENDPOINT", "http://localhost:8002")


def discover_apis(query: str, domain: str = "general") -> list[dict]:
    """
    Returns a list of available API descriptors relevant to the query.
    Each descriptor: {name, endpoint, description, params_schema, auth_type}
    """
    try:
        r = httpx.get(f"{DISCOVERY_BASE}/search", params={
            "q": query, "domain": domain,
        }, timeout=10)
        r.raise_for_status()
        return r.json().get("apis", [])
    except Exception as e:
        logger.debug(f"API Discovery unavailable: {e}")
        return []


def call_discovered_api(descriptor: dict, params: dict) -> dict:
    """
    Calls an API found via discovery. Handles auth injection from env.
    Returns raw response dict or {"error": ...} on failure.
    """
    auth_type = descriptor.get("auth_type", "none")
    headers = {}
    if auth_type == "bearer":
        env_key = descriptor.get("env_key", "")
        token = os.getenv(env_key, "")
        if token:
            headers["Authorization"] = f"Bearer {token}"

    try:
        r = httpx.get(descriptor["endpoint"], params=params,
                      headers=headers, timeout=30)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"error": str(e)}
