"""tools.py — TOOLS registry + call_tool with ring check and receipt log (§3).

Rings: read-only auto-approves; own-write logs; world-acting requires a preview
token. V1 ships only the 3 read-only tools: web_search, fetch_page, market_quote.
Every call writes a receipt (source, fetch time, trust) the verifier can check.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

RING_READ, RING_WRITE, RING_WORLD = "read", "write", "world"
_RECEIPTS = Path(__file__).parent / "data" / "receipts.jsonl"


def _receipt(tool: str, detail: dict) -> None:
    _RECEIPTS.parent.mkdir(parents=True, exist_ok=True)
    with open(_RECEIPTS, "a") as f:
        f.write(json.dumps({"ts": time.time(), "tool": tool, **detail}) + "\n")


def web_search(query: str) -> dict:
    """API-free search: DuckDuckGo HTML crawl (crawlers.py). No key, no stub."""
    from janus_v2 import crawlers
    out = crawlers.search_web(query)
    _receipt("web_search", {"query": query, "n": len(out["results"]), "tier": out["tier"]})
    return out


def fetch_page(url: str) -> dict:
    """API-free fetch: Crawl4AI/trafilatura/bs4 tiered extraction (crawlers.py)."""
    from janus_v2 import crawlers
    out = crawlers.crawl_page(url)
    _receipt("fetch_page", {"url": url, "tier": out["tier"], "chars": len(out["text"])})
    return {**out, "stub": False}


def market_quote(symbol: str) -> dict:
    """API-free quote: Stooq CSV crawl. Never invents a price."""
    from janus_v2 import crawlers
    out = crawlers.market_quote(symbol)
    _receipt("market_quote", {"symbol": symbol, "stub": out["stub"], "tier": out["tier"]})
    return out


def deep_search(query: str) -> dict:
    """Massive-mode tiered web research (deep.py): search -> crawl -> roam."""
    from janus_v2 import deep
    out = deep.deep_search(query)
    _receipt("deep_search", {"query": query, "pages": len(out["evidence"]),
                             "seconds": out["seconds"]})
    return out


def swarm(question: str) -> dict:
    """Massive-mode parallel workers (swarm.py): decompose, fan out, fuse."""
    from janus_v2 import swarm as _swarm
    out = _swarm.run_swarm(question)
    _receipt("swarm", {"workers": len(out["workers"]), "fused": bool(out["fused"])})
    return out


def live_sensor(sensor: str) -> dict:
    """Live sensor grid reading (sensors.py): weather/quakes/air/ISS/news."""
    from janus_v2 import sensors
    fn = sensors.SENSORS[sensor]
    out = fn()
    _receipt("live_sensor", {"sensor": sensor})
    return {"reading": out}


def social_search(query: str) -> dict:
    """Keyless social reading across Bluesky/Mastodon/HN (social.py)."""
    from janus_v2 import social
    out = social.search_social(query)
    _receipt("social_search", {"query": query, "n": len(out["posts"])})
    return out


def social_post(platform: str, text: str) -> dict:
    """World-ring posting: preview token enforced by call_tool before this runs."""
    from janus_v2 import social
    return social.post(platform, text)


def crawl_feed(feed_url: str) -> dict:
    """API-free intel: RSS/Atom feed crawl (crawlers.py)."""
    from janus_v2 import crawlers
    out = crawlers.crawl_feed(feed_url)
    _receipt("crawl_feed", {"url": feed_url, "n": len(out["items"])})
    return out


def browser_roam(start_url: str, goal: str = "") -> dict:
    """Human-like browser roaming (browser.py): rendered, scrolled, paced."""
    from janus_v2 import browser
    out = browser.roam(start_url, [w for w in goal.split() if len(w) > 3])
    _receipt("browser_roam", {"start": start_url, "pages": out["pages_visited"]})
    return out


def code_exec(code: str) -> dict:
    """Python action (write-ring, receipt-logged, 10s timeout).

    Runs in an isolated interpreter (`python3 -I`) for verifiable computation.
    Honest limit: this is NOT a security sandbox — host access exists, which is
    why it sits behind the write ring with a receipt on every call.
    """
    import subprocess
    proc = subprocess.run(
        ["python3", "-I", "-c", code], capture_output=True, text=True, timeout=10)
    out = {"stdout": proc.stdout[:4000], "stderr": proc.stderr[-500:], "returncode": proc.returncode}
    _receipt("code_exec", {"chars": len(code), "returncode": proc.returncode})
    return out


TOOLS = {
    "web_search": (web_search, RING_READ),
    "fetch_page": (fetch_page, RING_READ),
    "market_quote": (market_quote, RING_READ),
    "browser_roam": (browser_roam, RING_READ),
    "crawl_feed": (crawl_feed, RING_READ),
    "social_search": (social_search, RING_READ),
    "live_sensor": (live_sensor, RING_READ),
    "deep_search": (deep_search, RING_READ),
    "swarm": (swarm, RING_READ),
    "social_post": (social_post, RING_WORLD),
    "code_exec": (code_exec, RING_WRITE),
}


def call_tool(name: str, preview_token: str | None = None, **kwargs) -> dict:
    if name not in TOOLS:
        raise KeyError(f"unknown tool {name}")
    fn, ring = TOOLS[name]
    if ring == RING_WORLD and not preview_token:
        raise PermissionError(f"{name} acts in the world — preview approval required")
    if ring == RING_WRITE:
        _receipt(name, {"ring": "write", "kwargs": list(kwargs)})
    return fn(**kwargs)
