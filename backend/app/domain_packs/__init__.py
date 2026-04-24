"""
Domain Packs - Pluggable domain-specific intelligence modules.

Domain packs extend the base MiroOrg system with specialized capabilities
for specific domains (finance, healthcare, legal, etc.) without requiring
changes to the core agent architecture.
"""

from app.domain_packs.base import DomainPack
from app.domain_packs.registry import DomainPackRegistry, get_registry

__all__ = ["DomainPack", "DomainPackRegistry", "get_registry"]
