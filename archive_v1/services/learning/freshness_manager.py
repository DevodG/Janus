"""
Freshness management for knowledge items.

This is a convenience wrapper around TrustManager's freshness functionality.
"""

from .trust_manager import TrustManager

# Re-export for convenience
__all__ = ["TrustManager"]
