"""
Domain pack registry for managing and discovering domain packs.
"""

from typing import Dict, List, Optional
import logging

from app.domain_packs.base import DomainPack

logger = logging.getLogger(__name__)


class DomainPackRegistry:
    """Registry for managing domain packs."""

    def __init__(self):
        self._packs: Dict[str, DomainPack] = {}

    def register(self, pack: DomainPack) -> None:
        """Register a domain pack."""
        name = pack.name
        if name in self._packs:
            logger.warning(f"Domain pack '{name}' is already registered, overwriting")
        self._packs[name] = pack
        logger.info(f"Registered domain pack: {name}")

    def get_pack(self, name: str) -> Optional[DomainPack]:
        """Get a domain pack by name."""
        return self._packs.get(name)

    def detect_domain(self, query: str) -> Optional[str]:
        """
        Detect which domain pack matches the query based on keywords.
        
        Args:
            query: The user's query
            
        Returns:
            Domain pack name if detected, None otherwise
        """
        query_lower = query.lower()
        
        for name, pack in self._packs.items():
            for keyword in pack.keywords:
                if keyword.lower() in query_lower:
                    logger.info(f"Detected domain '{name}' from keyword '{keyword}'")
                    return name
        
        return None

    def list_packs(self) -> List[str]:
        """List all registered domain pack names."""
        return list(self._packs.keys())

    def get_capabilities(self) -> Dict[str, Any]:
        """Get capabilities of all registered domain packs."""
        return {
            name: pack.get_capabilities()
            for name, pack in self._packs.items()
        }


# Global registry instance
_registry = DomainPackRegistry()


def get_registry() -> DomainPackRegistry:
    """Get the global domain pack registry."""
    return _registry
