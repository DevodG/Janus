"""deep.py — massive-mode deep search: tiered crawling with intent-aware fan-out.

Tier 1 keyless search -> tier 2 page crawl of top sources -> tier 3 browser
roam on the single most relevant page. Pure open web, zero paid APIs.
Findings carry provenance (url, tier, time) into memory as untrusted facts.
"""
from __future__ import annotations

import time

from janus_v2 import crawlers


def deep_search(query: str, pages: int = 4) -> dict:
    t0 = time.time()
    provenance = []
    # tier 1: search fan-out
    found = crawlers.search_web(query, pages)
    provenance.append({"tier": 1, "tool": "search_web", "n": len(found["results"])})
    # tier 2: crawl every top source, keep quoted evidence
    evidence = []
    for r in found["results"]:
        if not r["url"].startswith("http"):
            continue
        page = crawlers.crawl_page(r["url"])
        evidence.append({"url": r["url"], "title": r["title"],
                         "snippet": r["snippet"][:300], "text": page["text"][:1500],
                         "tier": page["tier"]})
    provenance.append({"tier": 2, "tool": "crawl_page", "n": len(evidence)})
    # tier 3: browser-roam the most relevant result only (bounded)
    roam_note = "skipped — no pages crawled"
    if evidence:
        from janus_v2 import browser
        kw = [w for w in query.lower().split() if len(w) > 3]
        br = browser.roam(evidence[0]["url"], kw, max_pages=3, max_depth=1)
        roam_note = f"roamed {br['pages_visited']} pages"
        provenance.append({"tier": 3, "tool": "browser_roam", "n": br["pages_visited"]})
    evidence.sort(key=lambda e: -len(e["text"]))
    return {"query": query, "evidence": evidence, "roam": roam_note,
            "provenance": provenance, "seconds": round(time.time() - t0, 1)}


def store_deep(memory, result: dict) -> int:
    """Findings become gated untrusted facts (verification proposes later)."""
    n = 0
    for e in result["evidence"]:
        if memory.add_fact(e["title"] or "web", "web-evidence",
                           e["snippet"] or e["text"][:400],
                           source=f"deep:{e['tier']}"):
            n += 1
    return n
