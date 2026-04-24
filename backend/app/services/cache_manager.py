"""
Intelligent Cache Manager for MiroOrg v2.

Caches answers for generic queries to avoid redundant pipeline runs.
Only learns from specific/domain queries to keep memory clean.
"""

import json
import os
import time
import hashlib
from pathlib import Path
from typing import Dict, List, Any, Optional

from app.services.query_classifier import QueryType

CACHE_DIR = Path(__file__).parent.parent / "data" / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# TTL in hours
GENERIC_TTL_HOURS = 720  # 30 days
SPECIFIC_TTL_HOURS = 168  # 7 days
HYBRID_TTL_HOURS = 336  # 14 days


def _query_hash(query: str) -> str:
    """Generate a stable hash for a query string."""
    return hashlib.md5(query.lower().strip().encode()).hexdigest()


class CacheEntry:
    """Single cache entry with TTL."""

    def __init__(
        self,
        query: str,
        answer: str,
        query_type: QueryType,
        domain: str,
        ttl_hours: int,
        model_insights: List[str] = None,
        metadata: Dict = None,
    ):
        self.query = query
        self.answer = answer
        self.query_type = query_type.value
        self.domain = domain
        self.created_at = time.time()
        self.ttl_seconds = ttl_hours * 3600
        self.hit_count = 0
        self.model_insights = model_insights or []
        self.metadata = metadata or {}

    def is_expired(self) -> bool:
        return (time.time() - self.created_at) > self.ttl_seconds

    def to_dict(self) -> Dict:
        return {
            "query": self.query,
            "answer": self.answer,
            "query_type": self.query_type,
            "domain": self.domain,
            "created_at": self.created_at,
            "ttl_seconds": self.ttl_seconds,
            "hit_count": self.hit_count,
            "model_insights": self.model_insights,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "CacheEntry":
        entry = cls(
            query=data["query"],
            answer=data["answer"],
            query_type=QueryType(data["query_type"]),
            domain=data["domain"],
            ttl_hours=data["ttl_seconds"] // 3600,
            model_insights=data.get("model_insights", []),
            metadata=data.get("metadata", {}),
        )
        entry.created_at = data["created_at"]
        entry.hit_count = data.get("hit_count", 0)
        return entry


class IntelligentCacheManager:
    """Manages intelligent caching with TTL and hit tracking."""

    def __init__(self, cache_dir: Path = CACHE_DIR):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_cache_path(self, query_hash: str) -> Path:
        return self.cache_dir / f"{query_hash}.json"

    def get(self, query: str) -> Optional[Dict]:
        """
        Get cached answer for a query.

        Returns:
            Dict with answer, cached=True, cache_age_hours if found
            None if not found or expired
        """
        h = _query_hash(query)
        path = self._get_cache_path(h)

        if not path.exists():
            return None

        try:
            with open(path) as f:
                data = json.load(f)

            entry = CacheEntry.from_dict(data)

            if entry.is_expired():
                path.unlink(missing_ok=True)
                return None

            # Increment hit count
            entry.hit_count += 1
            with open(path, "w") as f:
                json.dump(entry.to_dict(), f, indent=2)

            cache_age_hours = (time.time() - entry.created_at) / 3600

            return {
                "answer": entry.answer,
                "cached": True,
                "cache_age_hours": cache_age_hours,
                "hit_count": entry.hit_count,
                "query_type": entry.query_type,
                "domain": entry.domain,
                "model_insights": entry.model_insights,
            }
        except Exception:
            return None

    def put(
        self,
        query: str,
        answer: str,
        query_type: QueryType,
        domain: str,
        ttl_hours: int = None,
        model_insights: List[str] = None,
        metadata: Dict = None,
    ) -> None:
        """Store an answer in the cache."""
        if ttl_hours is None:
            if query_type == QueryType.GENERIC:
                ttl_hours = GENERIC_TTL_HOURS
            elif query_type == QueryType.SPECIFIC:
                ttl_hours = SPECIFIC_TTL_HOURS
            else:
                ttl_hours = HYBRID_TTL_HOURS

        entry = CacheEntry(
            query=query,
            answer=answer,
            query_type=query_type,
            domain=domain,
            ttl_hours=ttl_hours,
            model_insights=model_insights or [],
            metadata=metadata or {},
        )

        h = _query_hash(query)
        path = self._get_cache_path(h)

        with open(path, "w") as f:
            json.dump(entry.to_dict(), f, indent=2)

    def cleanup_expired(self) -> int:
        """Remove expired cache entries. Returns count removed."""
        count = 0
        for path in self.cache_dir.glob("*.json"):
            try:
                with open(path) as f:
                    data = json.load(f)
                entry = CacheEntry.from_dict(data)
                if entry.is_expired():
                    path.unlink(missing_ok=True)
                    count += 1
            except Exception:
                path.unlink(missing_ok=True)
                count += 1
        return count

    def get_stats(self) -> Dict:
        """Get cache statistics."""
        total = 0
        generic = 0
        specific = 0
        hybrid = 0
        expired = 0
        total_hits = 0

        for path in self.cache_dir.glob("*.json"):
            try:
                with open(path) as f:
                    data = json.load(f)
                entry = CacheEntry.from_dict(data)
                total += 1
                total_hits += entry.hit_count

                if entry.is_expired():
                    expired += 1
                elif entry.query_type == "generic":
                    generic += 1
                elif entry.query_type == "specific":
                    specific += 1
                else:
                    hybrid += 1
            except Exception:
                pass

        # Calculate cache size
        cache_size_bytes = sum(
            p.stat().st_size for p in self.cache_dir.glob("*.json") if p.exists()
        )
        cache_size_mb = cache_size_bytes / (1024 * 1024)

        return {
            "total_entries": total,
            "generic_entries": generic,
            "specific_entries": specific,
            "hybrid_entries": hybrid,
            "expired_entries": expired,
            "total_hits": total_hits,
            "cache_size_mb": round(cache_size_mb, 2),
            "avg_hits_per_entry": round(total_hits / total, 1) if total > 0 else 0,
        }
