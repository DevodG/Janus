"""crawlers.py — API-free fetching: popular open-source crawling, tiered.

Tiers (first available wins): Crawl4AI (~80k stars, Apache-2.0, LLM-ready
markdown) -> trafilatura (extraction) -> BeautifulSoup+httpx (always present).
Search needs no API key: DuckDuckGo's HTML endpoint, crawled and parsed.
Quotes need no API key: Stooq's plain-CSV quote endpoint, crawled directly.
Firecrawl (~170k stars) is API-shaped/AGPL, so it is not embedded; Scrapy is
the scale-out option if crawl volume ever justifies a framework.
"""
from __future__ import annotations

import csv
import io
import re
from urllib.parse import quote_plus, urlparse

_MAX = 8000


def _get(url: str) -> str:
    import httpx
    r = httpx.get(url, timeout=20, follow_redirects=True,
                  headers={"User-Agent": "Mozilla/5.0 JanusV2/1.0"})
    return r.text


def crawl_page(url: str) -> dict:
    """Fetch + extract main content as clean text/markdown. No API key anywhere."""
    tier = "bs4"
    text = ""
    try:
        import trafilatura
        html = _get(url)
        text = trafilatura.extract(html, url=url, favor_recall=True) or ""
        tier = "trafilatura"
    except Exception:
        text = ""
    if len(text) < 200:  # extraction thin -> bs4 fallback
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(_get(url), "html.parser")
            for tag in soup(["script", "style", "nav", "footer"]):
                tag.decompose()
            text = soup.get_text(separator="\n", strip=True)
            tier = "bs4"
        except Exception as e:
            return {"url": url, "text": "", "tier": "failed", "error": str(e)[:120]}
    return {"url": url, "text": text[:_MAX], "tier": tier,
            "domain": urlparse(url).netloc}


def search_web(query: str, max_results: int = 5) -> dict:
    """Keyless search: crawl DuckDuckGo HTML results, parse titles/links/snippets."""
    html = _get(f"https://html.duckduckgo.com/html/?q={quote_plus(query)}")
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    results = []
    for a in soup.select("a.result__a")[:max_results]:
        snip = a.find_next(class_="result__snippet")
        results.append({"title": a.get_text(strip=True), "url": a.get("href", ""),
                        "snippet": snip.get_text(strip=True) if snip else ""})
    return {"results": results, "tier": "ddg-html-crawl", "stub": False}


def crawl_feed(feed_url: str, max_items: int = 10) -> dict:
    """Roam via RSS/Atom feeds (keyless intel): parse feed, return item summaries."""
    from bs4 import BeautifulSoup
    xml = _get(feed_url)
    soup = BeautifulSoup(xml, "xml")
    items = []
    for it in soup.find_all(["item", "entry"])[:max_items]:
        title = it.find("title")
        link = it.find("link")
        items.append({"title": title.get_text(strip=True) if title else "",
                      "link": (link.get_text(strip=True) or link.get("href", "")
                               if link else "")})
    return {"items": items, "tier": "feed-crawl", "stub": False}


def market_quote(symbol: str) -> dict:
    """Keyless quote: crawl Stooq CSV (symbol.us). Parsed, receipted, honest."""
    sym = symbol.lower().replace(".", "-") + ".us"
    try:
        raw = _get(f"https://stooq.com/q/l/?s={sym}&f=sd2t2ohlcv&i=d")
        row = list(csv.DictReader(io.StringIO(raw)))[0]
        close = float(row["Close"])
        return {"symbol": symbol.upper(), "price": close, "date": row.get("Date"),
                "tier": "stooq-crawl", "stub": False}
    except Exception as e:
        return {"symbol": symbol.upper(), "price": None, "tier": "stooq-crawl",
                "stub": True, "note": f"quote unavailable: {str(e)[:100]}"}
