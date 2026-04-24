"""
Initialize and register domain packs.

This module should be imported at application startup to register
all available domain packs.
"""

import logging
from app.config import os

logger = logging.getLogger(__name__)


def init_domain_packs():
    """Initialize and register all domain packs."""
    from app.domain_packs.registry import get_registry
    
    # Check if finance pack is enabled
    finance_enabled = os.getenv("FINANCE_DOMAIN_PACK_ENABLED", "true").lower() == "true"
    
    if finance_enabled:
        try:
            from app.domain_packs.finance import FinanceDomainPack
            
            registry = get_registry()
            finance_pack = FinanceDomainPack()
            registry.register(finance_pack)
            
            logger.info("Finance domain pack registered successfully")
        except Exception as e:
            logger.error(f"Failed to register finance domain pack: {e}")
    else:
        logger.info("Finance domain pack is disabled")
    
    # Future domain packs can be registered here
    # Example:
    # if healthcare_enabled:
    #     from app.domain_packs.healthcare import HealthcareDomainPack
    #     registry.register(HealthcareDomainPack())
