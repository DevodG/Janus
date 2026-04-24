"""
New service: ResponseCache

An in-process TTL cache that prevents the same external API call from being
made more than once per window. Solves the AlphaVantage 25/day rate limit
and the NewsAPI repeated hammering visible in the server logs.

Usage:
    from app.services.response_cache import response_cache

    cached = response_cache.get("finance:quote:AAPL")
    if cached is None:
        data = fetch_from_api()
        response_cache.set("finance:quote:AAPL", data, ttl=300)
    else:
        data = cached
"""
from __future__ import annotations

import threading
import time
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


class _CacheEntry:
    __slots__ = ("value", "expires_at")

    def __init__(self, value: Any, ttl: int):
        self.value      = value
        self.expires_at = time.monotonic() + ttl


class ResponseCache:
    """
    Thread-safe in-memory TTL cache.

    Default TTLs (seconds):
      market quotes   : 300   (5 min)
      historical data : 3600  (1 hour)
      company overview: 86400 (24 hours)
      news headlines  : 900   (15 min)
      news articles   : 1800  (30 min)
    """

    DEFAULT_TTL = 300

    TTL_PRESETS = {
        "quote":     300,
        "historical": 3600,
        "overview":  86400,
        "headlines": 900,
        "news":      1800,
        "search":    3600,
        "sentinel":  60,
    }

    def __init__(self, max_entries: int = 2048):
        self._cache: dict[str, _CacheEntry] = {}
        self._lock  = threading.RLock()
        self._max   = max_entries

    # ── Public API ─────────────────────────────────────────────────────────

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return None
            if time.monotonic() > entry.expires_at:
                del self._cache[key]
                return None
            return entry.value

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        if ttl is None:
            # Infer TTL from key prefix
            for preset, secs in self.TTL_PRESETS.items():
                if preset in key:
                    ttl = secs
                    break
            else:
                ttl = self.DEFAULT_TTL

        with self._lock:
            if len(self._cache) >= self._max:
                self._evict_expired()
                if len(self._cache) >= self._max:
                    self._evict_lru(count=self._max // 4)
            self._cache[key] = _CacheEntry(value, ttl)

    def delete(self, key: str) -> None:
        with self._lock:
            self._cache.pop(key, None)

    def invalidate_prefix(self, prefix: str) -> int:
        with self._lock:
            keys = [k for k in self._cache if k.startswith(prefix)]
            for k in keys:
                del self._cache[k]
            return len(keys)

    def stats(self) -> dict:
        with self._lock:
            now  = time.monotonic()
            live = sum(1 for e in self._cache.values() if e.expires_at > now)
            return {
                "total_entries": len(self._cache),
                "live_entries":  live,
                "expired":       len(self._cache) - live,
                "max_entries":   self._max,
            }

    # ── Helpers ────────────────────────────────────────────────────────────

    def _evict_expired(self):
        now  = time.monotonic()
        dead = [k for k, e in self._cache.items() if e.expires_at <= now]
        for k in dead:
            del self._cache[k]

    def _evict_lru(self, count: int):
        # Cheapest approximation — evict entries expiring soonest
        sorted_keys = sorted(self._cache, key=lambda k: self._cache[k].expires_at)
        for k in sorted_keys[:count]:
            del self._cache[k]

    # ── Decorator helper ───────────────────────────────────────────────────

    def cached(self, key_fn, ttl: Optional[int] = None):
        """
        Decorator: @response_cache.cached(lambda *a, **kw: f"quote:{a[0]}", ttl=300)
        """
        def decorator(fn):
            import functools
            @functools.wraps(fn)
            def wrapper(*args, **kwargs):
                key   = key_fn(*args, **kwargs)
                value = self.get(key)
                if value is not None:
                    return value
                value = fn(*args, **kwargs)
                self.set(key, value, ttl=ttl)
                return value
            return wrapper
        return decorator


# ── Module-level singleton ────────────────────────────────────────────────────
response_cache = ResponseCache()
