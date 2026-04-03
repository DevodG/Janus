"""
Base class for domain packs.

Domain packs provide specialized capabilities for specific domains
without requiring changes to core agents.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional


class DomainPack(ABC):
    """Abstract base class for domain packs."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the domain pack name (e.g., 'finance', 'healthcare')."""
        pass

    @property
    @abstractmethod
    def keywords(self) -> List[str]:
        """Return keywords that trigger this domain pack."""
        pass

    @abstractmethod
    def enhance_research(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enhance research phase with domain-specific capabilities.
        
        Args:
            query: The user's query
            context: Current research context
            
        Returns:
            Enhanced context with domain-specific data
        """
        pass

    @abstractmethod
    def enhance_verification(self, claims: List[str], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enhance verification phase with domain-specific capabilities.
        
        Args:
            claims: Claims to verify
            context: Current verification context
            
        Returns:
            Enhanced context with domain-specific verification
        """
        pass

    @abstractmethod
    def get_capabilities(self) -> Dict[str, Any]:
        """
        Return domain pack capabilities and metadata.
        
        Returns:
            Dictionary describing pack capabilities
        """
        pass
