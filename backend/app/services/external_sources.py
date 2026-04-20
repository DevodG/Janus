import re
import time
import logging
import os
from typing import List, Dict, Any, Optional
import html
from urllib.parse import quote_plus, urlparse
from urllib.parse import parse_qs, unquote

import httpx

from app.config import (
    TAVILY_API_KEY,
    NEWSAPI_KEY,
    ALPHAVANTAGE_API_KEY,
    JINA_READER_BASE,
)

logger = logging.getLogger(__name__)

# Module-level connection pool
_http_pool = httpx.Client(
    timeout=30,
    limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
)

# Simple TTL cache for market quotes (5 min)
_quote_cache: Dict[str, Dict[str, Any]] = {}  # {symbol: {"data": ..., "ts": ...}}
_QUOTE_TTL = 300  # seconds
_deep_read_cache: Dict[str, Dict[str, Any]] = {}
_DEEP_READ_TTL = 900
_deep_search_cache: Dict[str, Dict[str, Any]] = {}
_DEEP_SEARCH_TTL = 600

URL_PATTERN = re.compile(r"https?://\S+")
TICKER_PATTERN = re.compile(r"\$([A-Z]{1,5})\b")

_GENERIC_TRUSTED_DOMAINS = {
    "reuters.com": 0.95,
    "apnews.com": 0.92,
    "bloomberg.com": 0.95,
    "ft.com": 0.92,
    "wsj.com": 0.92,
    "cnbc.com": 0.86,
    "marketwatch.com": 0.84,
    "investopedia.com": 0.8,
    "wikipedia.org": 0.72,
    "sec.gov": 1.0,
    "federalreserve.gov": 1.0,
    "treasury.gov": 1.0,
    "ecb.europa.eu": 1.0,
    "imf.org": 0.98,
    "worldbank.org": 0.98,
    "nvidia.com": 0.9,
    "investor.nvidia.com": 0.97,
}

_LOWER_CONFIDENCE_DOMAINS = {
    "substack.com": 0.58,
    "blogspot.com": 0.45,
    "medium.com": 0.55,
    "dev.to": 0.5,
}

_BROWSER_FAVOR_DOMAINS = {
    "cnbc.com",
    "finance.yahoo.com",
    "seekingalpha.com",
    "futurumgroup.com",
    "marketwatch.com",
}


def extract_urls(text: str) -> List[str]:
    return URL_PATTERN.findall(text or "")


def extract_ticker(text: str) -> Optional[str]:
    match = TICKER_PATTERN.search(text or "")
    if match:
        return match.group(1)
    return None


def jina_read(url: str) -> str:
    try:
        target = url.replace("https://", "").replace("http://", "")
        full_url = f"{JINA_READER_BASE}{target}"
        with httpx.Client(timeout=30) as client:
            response = client.get(full_url)
        if response.status_code >= 400:
            return ""
        return response.text[:4000]
    except Exception:
        return ""


def duckduckgo_search(query: str, max_results: int = 5) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    try:
        search_url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; Janus/1.0; +https://janus.local)"
        }
        response = _http_pool.get(search_url, headers=headers, follow_redirects=True)
        if response.status_code >= 400:
            return []

        pattern = re.compile(
            r'class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', re.IGNORECASE
        )
        seen = set()
        for match in pattern.finditer(response.text):
            raw_url = html.unescape(match.group(1) or "")
            url = raw_url
            if raw_url.startswith("//duckduckgo.com/l/?"):
                parsed = urlparse(f"https:{raw_url}")
                uddg = parse_qs(parsed.query).get("uddg", [""])[0]
                url = unquote(uddg) if uddg else ""
            title = re.sub(r"<[^>]+>", "", match.group(2)).strip()
            if not url or not url.startswith("http") or url in seen:
                continue
            seen.add(url)
            results.append({"title": title or url, "url": url, "source": "duckduckgo"})
            if len(results) >= max_results:
                break
    except Exception as e:
        logger.warning(f"DuckDuckGo search error: {e}")
    return results


def _direct_page_extract(url: str) -> str:
    try:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; Janus/1.0)"}
        response = _http_pool.get(url, headers=headers, follow_redirects=True)
        if response.status_code >= 400:
            return ""
        text = re.sub(r"<script[^>]*>.*?</script>", "", response.text, flags=re.DOTALL)
        text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text[:8000]
    except Exception:
        return ""


def _sanitize_extracted_text(text: str, limit: int = 8000) -> str:
    cleaned = str(text or "")
    noise_patterns = [
        r"Title:\s*",
        r"URL Source:\s*[^\n]+",
        r"Published Time:\s*[^\n]+",
        r"Markdown Content:\s*",
        r"\bSkip Navigation\b",
        r"\bLivestream\b",
        r"\bMenu\b",
        r"\bSearch\b",
        r"\bSign In\b",
        r"\bSubscribe\b",
        r"\[Image [^\]]+\]",
    ]
    for pattern in noise_patterns:
        cleaned = re.sub(pattern, " ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"!\[[^\]]*\]\([^)]+\)", " ", cleaned)
    cleaned = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", cleaned)
    cleaned = re.sub(r"[#*_`>-]+", " ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned[:limit]


def _best_excerpt(text: str, limit: int = 280) -> str:
    cleaned = _sanitize_extracted_text(text, limit=3000)
    if not cleaned:
        return ""

    sentences = re.split(r"(?<=[.!?])\s+", cleaned)
    for sentence in sentences:
        candidate = sentence.strip().lstrip("|:- ")
        if len(candidate) < 60:
            continue
        lowered = candidate.lower()
        if any(
            token in lowered
            for token in [
                "cookie",
                "subscribe",
                "sign in",
                "javascript",
                "skip to main content",
                "accessibility",
                "stock advisor",
                "join the motley fool",
            ]
        ):
            continue
        return candidate[:limit]

    return cleaned[:limit]


def crawler_read(url: str) -> Dict[str, Any]:
    try:
        from app.services.crawler import JanusCrawler

        crawler = JanusCrawler()
        result = crawler.crawl_sync(url)
        if result.success:
            return {
                "title": result.title or url,
                "content": _sanitize_extracted_text(result.markdown, limit=12000),
                "links": result.links[:20],
                "metadata": result.metadata,
                "source": "janus_crawler",
            }
    except Exception as e:
        logger.debug(f"Janus crawler unavailable for {url}: {e}")
    return {}


def _base_domain(domain: str) -> str:
    parts = [part for part in (domain or "").lower().split(".") if part]
    if len(parts) >= 2:
        return ".".join(parts[-2:])
    return domain.lower()


def score_source_credibility(url: str, metadata: Dict[str, Any] | None = None) -> Dict[str, Any]:
    metadata = metadata or {}
    parsed = urlparse(url)
    domain = parsed.netloc.lower().replace("www.", "")
    root = _base_domain(domain)

    try:
        from app.domain_packs.finance.source_checker import check_source_credibility

        finance_assessment = check_source_credibility(url)
        if finance_assessment.get("reason") == "known_trusted_source":
            return {
                "score": finance_assessment.get("credibility_score", 0.5),
                "reason": finance_assessment.get("reason", "known_trusted_source"),
                "domain": finance_assessment.get("domain", domain),
            }
    except Exception:
        pass

    if domain in _GENERIC_TRUSTED_DOMAINS or root in _GENERIC_TRUSTED_DOMAINS:
        return {
            "score": _GENERIC_TRUSTED_DOMAINS.get(domain, _GENERIC_TRUSTED_DOMAINS.get(root, 0.9)),
            "reason": "trusted_domain",
            "domain": domain,
        }

    if domain.endswith(".gov") or domain.endswith(".edu"):
        return {"score": 0.96, "reason": "government_or_education", "domain": domain}

    if domain in _LOWER_CONFIDENCE_DOMAINS or root in _LOWER_CONFIDENCE_DOMAINS:
        return {
            "score": _LOWER_CONFIDENCE_DOMAINS.get(domain, _LOWER_CONFIDENCE_DOMAINS.get(root, 0.5)),
            "reason": "opinion_or_blog_domain",
            "domain": domain,
        }

    score = 0.58
    reason = "unknown_domain"
    path = parsed.path.lower()
    if any(token in path for token in ["/news", "/press", "/press-release", "/investor", "/earnings"]):
        score += 0.08
        reason = "official_or_news_path"
    if metadata.get("published_at"):
        score += 0.04
    if metadata.get("author"):
        score += 0.02
    return {"score": min(score, 0.9), "reason": reason, "domain": domain}


def plan_deep_research(query: str, max_results: int = 5, follow_links: int = 1) -> Dict[str, int]:
    query_lower = (query or "").lower()
    deep_terms = [
        "across the web",
        "deep web",
        "research",
        "investigate",
        "compare",
        "earnings",
        "guidance",
        "supply chain",
        "data center",
        "competition",
        "regulation",
        "policy",
    ]
    score = sum(1 for term in deep_terms if term in query_lower)
    word_count = len(re.findall(r"[a-z0-9_]+", query_lower))
    if word_count > 10:
        score += 1

    planned_results = max_results
    planned_hops = follow_links
    if score >= 3:
        planned_results = max(max_results, 6)
        planned_hops = max(follow_links, 2)
    elif score >= 1:
        planned_results = max(max_results, 4)
        planned_hops = max(follow_links, 1)

    if os.getenv("JANUS_PREFER_BROWSER_CRAWL", "false").lower() == "true":
        planned_results = min(planned_results, 4)
        planned_hops = min(planned_hops, 1)

    return {
        "max_results": min(planned_results, 8),
        "follow_links": min(planned_hops, 2),
    }


def expand_research_queries(query: str, max_variants: int = 4) -> List[str]:
    query = (query or "").strip()
    if not query:
        return []

    if os.getenv("JANUS_PREFER_BROWSER_CRAWL", "false").lower() == "true":
        max_variants = min(max_variants, 2)

    variants = [query]
    lower = query.lower()

    if any(term in lower for term in ["earnings", "guidance", "revenue", "margin"]):
        variants.extend(
            [
                f"{query} investor relations",
                f"{query} official results",
                f"{query} analyst reaction",
            ]
        )
    elif any(term in lower for term in ["stock", "company", "market", "demand", "supply", "ai"]):
        variants.extend(
            [
                f"{query} official source",
                f"{query} latest analysis",
                f"{query} news and filings",
            ]
        )
    else:
        variants.extend(
            [
                f"{query} official source",
                f"{query} latest developments",
            ]
        )

    deduped = []
    seen = set()
    for item in variants:
        normalized = item.strip().lower()
        if normalized and normalized not in seen:
            seen.add(normalized)
            deduped.append(item.strip())
        if len(deduped) >= max_variants:
            break
    return deduped


def _should_prefer_browser(url: str, query: str = "") -> bool:
    if os.getenv("JANUS_PREFER_BROWSER_CRAWL", "false").lower() == "true":
        return True
    parsed = urlparse(url)
    domain = parsed.netloc.lower().replace("www.", "")
    root = _base_domain(domain)
    if domain in _BROWSER_FAVOR_DOMAINS or root in _BROWSER_FAVOR_DOMAINS:
        return True
    query_lower = (query or "").lower()
    return any(term in query_lower for term in ["headline", "latest", "live", "filing", "press release"])


def _choose_follow_links(
    links: List[str], base_url: str, query: str, limit: int = 1
) -> List[str]:
    query_words = {
        token for token in re.findall(r"[a-z0-9_]+", query.lower()) if len(token) >= 4
    }
    base_netloc = urlparse(base_url).netloc
    candidates = []
    seen = set()
    for link in links:
        parsed = urlparse(link)
        if parsed.scheme not in {"http", "https"}:
            continue
        if not parsed.netloc or parsed.netloc != base_netloc:
            continue
        if link in seen:
            continue
        seen.add(link)
        score = sum(1 for word in query_words if word in link.lower())
        if any(token in link.lower() for token in ["earnings", "results", "revenue", "guidance", "ai", "data-center", "investor", "quarter"]):
            score += 2
        candidates.append((score, link))
    candidates.sort(key=lambda item: item[0], reverse=True)
    return [link for _, link in candidates[:limit]]


def _follow_relevant_links(
    seed_url: str,
    links: List[str],
    query: str,
    remaining_hops: int,
) -> List[Dict[str, Any]]:
    if remaining_hops <= 0 or not links:
        return []

    reads = []
    for link in _choose_follow_links(links, seed_url, query, limit=1):
        nested = deep_read_url(link, follow_links=0, query=query)
        if not nested:
            continue
        credibility = score_source_credibility(link, nested.get("metadata", {}))
        nested["credibility"] = credibility
        nested["domain"] = credibility.get("domain")
        reads.append(
            {
                "url": link,
                "title": nested.get("title") or link,
                "content": nested.get("content", "")[:2500],
                "credibility_score": credibility.get("score", 0.5),
                "credibility_reason": credibility.get("reason", "unknown_domain"),
            }
        )
        if remaining_hops > 1 and nested.get("related_reads"):
            reads.extend(nested.get("related_reads", [])[:1])
    return reads


def deep_read_url(url: str, follow_links: int = 0, query: str = "") -> Dict[str, Any]:
    cache_key = f"{url}|{follow_links}|{query[:120]}|{os.getenv('JANUS_PREFER_BROWSER_CRAWL', 'false')}"
    cached = _deep_read_cache.get(cache_key)
    if cached and (time.time() - cached["ts"]) < _DEEP_READ_TTL:
        return cached["data"]

    prefer_browser = _should_prefer_browser(url, query)
    content = ""
    source = ""
    links: List[str] = []
    metadata: Dict[str, Any] = {}
    title = url

    if prefer_browser:
        crawled = crawler_read(url)
        if crawled:
            content = crawled.get("content", "")
            links = crawled.get("links", [])
            metadata = crawled.get("metadata", {})
            title = crawled.get("title") or title
            source = crawled.get("source", "crawler")

    if not content:
        content = jina_read(url)
        source = "jina_reader" if content else source

    if not content:
        crawled = crawler_read(url)
        if crawled:
            content = crawled.get("content", "")
            links = crawled.get("links", [])
            metadata = crawled.get("metadata", {})
            title = crawled.get("title") or title
            source = crawled.get("source", "crawler")

    if not content:
        content = _direct_page_extract(url)
        source = "direct_fetch" if content else source

    if not content:
        return {}

    related_reads = []
    if follow_links > 0 and links:
        related_reads = _follow_relevant_links(url, links, query, remaining_hops=follow_links)

    credibility = score_source_credibility(url, metadata)

    result = {
        "title": metadata.get("title") or title,
        "url": url,
        "content": _sanitize_extracted_text(content, limit=8000),
        "source": source,
        "metadata": metadata,
        "domain": credibility.get("domain"),
        "credibility": credibility,
        "related_reads": related_reads,
    }
    _deep_read_cache[cache_key] = {"data": result, "ts": time.time()}
    return result


def deep_web_search(
    query: str, max_results: int = 5, follow_links: int = 1
) -> List[Dict[str, Any]]:
    cache_key = f"{query}|{max_results}|{follow_links}|{os.getenv('JANUS_PREFER_BROWSER_CRAWL', 'false')}"
    cached = _deep_search_cache.get(cache_key)
    if cached and (time.time() - cached["ts"]) < _DEEP_SEARCH_TTL:
        return cached["data"]

    plan = plan_deep_research(query, max_results=max_results, follow_links=follow_links)
    max_results = plan["max_results"]
    follow_links = plan["follow_links"]
    started_at = time.time()
    candidates: List[Dict[str, Any]] = []

    tavily_results = tavily_search(query, max_results=max_results)
    for item in tavily_results:
        candidates.append(
            {
                "title": item.get("title", item.get("url", "")),
                "url": item.get("url", ""),
                "snippet": item.get("content", ""),
                "source": "tavily",
            }
        )

    ddg_results = duckduckgo_search(query, max_results=max_results)
    candidates.extend(ddg_results)

    seen_urls = set()
    merged = []
    for item in candidates:
        url = item.get("url", "")
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)
        merged.append(item)
        if len(merged) >= max_results:
            break

    enriched = []
    for item in merged:
        if time.time() - started_at > 20:
            break
        deep = deep_read_url(item.get("url", ""), follow_links=follow_links, query=query)
        if not deep:
            continue
        enriched.append(
            {
                "title": deep.get("title") or item.get("title", "Untitled"),
                "url": item.get("url", ""),
                "content": deep.get("content", "") or item.get("snippet", ""),
                "source": item.get("source", deep.get("source", "web")),
                "domain": deep.get("domain"),
                "credibility_score": (deep.get("credibility") or {}).get("score", 0.5),
                "credibility_reason": (deep.get("credibility") or {}).get("reason", "unknown_domain"),
                "metadata": deep.get("metadata", {}),
                "related_reads": deep.get("related_reads", []),
            }
        )
    enriched.sort(
        key=lambda item: (
            item.get("credibility_score", 0.0),
            len(item.get("content", "")),
        ),
        reverse=True,
    )
    result = enriched[:max_results]
    _deep_search_cache[cache_key] = {"data": result, "ts": time.time()}
    return result


def deep_web_research_bundle(
    query: str,
    max_results: int = 6,
    follow_links: int = 1,
    max_variants: int = 4,
) -> Dict[str, Any]:
    plan = plan_deep_research(query, max_results=max_results, follow_links=follow_links)
    variants = expand_research_queries(query, max_variants=max_variants)

    merged: Dict[str, Dict[str, Any]] = {}
    started_at = time.time()
    for variant in variants:
        if time.time() - started_at > 30:
            break
        results = deep_web_search(
            variant,
            max_results=max(3, min(plan["max_results"], max_results)),
            follow_links=plan["follow_links"],
        )
        for item in results:
            url = item.get("url", "")
            if not url:
                continue
            current = merged.get(url)
            candidate = {**item, "query_variant": variant}
            if current is None or candidate.get("credibility_score", 0.0) > current.get(
                "credibility_score", 0.0
            ):
                merged[url] = candidate

        ranked = sorted(
            merged.values(),
            key=lambda item: (
                item.get("credibility_score", 0.0),
                len(item.get("content", "")),
            ),
            reverse=True,
        )
        if ranked and ranked[0].get("credibility_score", 0.0) >= 0.85 and len(ranked) >= 1:
            if os.getenv("JANUS_PREFER_BROWSER_CRAWL", "false").lower() == "true":
                break

    results = sorted(
        merged.values(),
        key=lambda item: (
            item.get("credibility_score", 0.0),
            len(item.get("content", "")),
        ),
        reverse=True,
    )[:max_results]
    synthesis = synthesize_deep_web_results(query, results)
    return {
        "query": query,
        "query_variants": variants,
        "results": results,
        "synthesis": synthesis,
    }


def synthesize_deep_web_results(query: str, results: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not results:
        return {
            "summary": "No credible deep-web results retrieved.",
            "top_sources": [],
            "key_points": [],
            "avg_credibility": 0.0,
        }

    top_sources = [
        {
            "title": item.get("title"),
            "url": item.get("url"),
            "domain": item.get("domain"),
            "credibility_score": item.get("credibility_score", 0.0),
            "credibility_reason": item.get("credibility_reason", "unknown"),
        }
        for item in results[:4]
    ]
    avg_credibility = sum(item.get("credibility_score", 0.0) for item in results[: min(len(results), 5)]) / max(min(len(results), 5), 1)

    key_points = []
    for item in results[:3]:
        point = _best_excerpt(item.get("content", ""), limit=280)
        if point:
            key_points.append(
                {
                    "point": point,
                    "source": item.get("title") or item.get("domain"),
                    "credibility_score": item.get("credibility_score", 0.0),
                }
            )

    source_lines = "; ".join(
        f"{item.get('title', item.get('domain', 'source'))} [{item.get('credibility_score', 0.0):.2f}]"
        for item in top_sources[:3]
    )
    summary = (
        f"Janus reviewed {len(results)} deep public-web results for '{query}'. "
        f"Highest-ranked sources: {source_lines}. "
        f"Average credibility of the top results: {avg_credibility:.2f}."
    )

    return {
        "summary": summary,
        "top_sources": top_sources,
        "key_points": key_points,
        "avg_credibility": round(avg_credibility, 3),
    }


def tavily_search(query: str, max_results: int = 5) -> List[Dict[str, Any]]:
    if not TAVILY_API_KEY:
        return []

    try:
        payload = {
            "api_key": TAVILY_API_KEY,
            "query": query,
            "search_depth": "basic",
            "max_results": max_results,
        }
        response = _http_pool.post("https://api.tavily.com/search", json=payload)
        if response.status_code >= 400:
            logger.warning(f"Tavily search returned {response.status_code}")
            return []
        data = response.json()
        return data.get("results", [])
    except Exception as e:
        logger.error(f"Tavily search error: {e}")
        return []


def news_search(query: str, page_size: int = 5) -> List[Dict[str, Any]]:
    if not NEWSAPI_KEY:
        return []

    try:
        params = {
            "q": query,
            "pageSize": page_size,
            "language": "en",
            "sortBy": "publishedAt",
            "apiKey": NEWSAPI_KEY,
        }
        response = _http_pool.get("https://newsapi.org/v2/everything", params=params)
        if response.status_code >= 400:
            logger.warning(f"NewsAPI returned {response.status_code}")
            return []
        data = response.json()
        return data.get("articles", [])
    except Exception as e:
        logger.error(f"NewsAPI error: {e}")
        return []


def market_quote(symbol: str) -> Dict[str, Any]:
    if not ALPHAVANTAGE_API_KEY or not symbol:
        return {}

    # Check cache first
    cached = _quote_cache.get(symbol)
    if cached and (time.time() - cached["ts"]) < _QUOTE_TTL:
        logger.debug(f"Market quote cache hit: {symbol}")
        return cached["data"]

    try:
        params = {
            "function": "GLOBAL_QUOTE",
            "symbol": symbol,
            "apikey": ALPHAVANTAGE_API_KEY,
        }
        response = _http_pool.get("https://www.alphavantage.co/query", params=params)
        if response.status_code >= 400:
            logger.warning(f"Alpha Vantage returned {response.status_code}")
            return {}
        data = response.json()
        quote = data.get("Global Quote", {})

        # Cache the result
        _quote_cache[symbol] = {"data": quote, "ts": time.time()}

        return quote
    except Exception as e:
        logger.error(f"Alpha Vantage error: {e}")
        return {}


def build_external_context(user_input: str) -> str:
    chunks: List[str] = []

    urls = extract_urls(user_input)
    for url in urls[:2]:
        content = jina_read(url)
        if content:
            chunks.append(f"[Jina Reader for {url}]\n{content}")

    search_results = tavily_search(user_input, max_results=4)
    if search_results:
        formatted = []
        for item in search_results[:4]:
            formatted.append(
                f"- {item.get('title', 'Untitled')}\n  {item.get('url', '')}\n  {item.get('content', '')[:300]}"
            )
        chunks.append("[Tavily Search]\n" + "\n".join(formatted))

    deep_results = deep_web_search(user_input, max_results=3, follow_links=1)
    if deep_results:
        synthesized = synthesize_deep_web_results(user_input, deep_results)
        chunks.append(f"[Deep Web Brief]\n{synthesized.get('summary', '')}")
        formatted = []
        for item in deep_results[:3]:
            related = item.get("related_reads", [])
            related_text = ""
            if related:
                related_text = "\n  Related: " + " | ".join(
                    f"{r.get('url', '')} [{r.get('credibility_score', 0.0):.2f}]: {str(r.get('content', ''))[:140]}" for r in related[:1]
                )
            formatted.append(
                f"- {item.get('title', 'Untitled')}\n  {item.get('url', '')}\n  Credibility: {item.get('credibility_score', 0.0):.2f} ({item.get('credibility_reason', 'unknown')})\n  {str(item.get('content', ''))[:500]}{related_text}"
            )
        chunks.append("[Deep Web Search]\n" + "\n".join(formatted))

    articles = news_search(user_input, page_size=4)
    if articles:
        formatted = []
        for item in articles[:4]:
            formatted.append(
                f"- {item.get('title', 'Untitled')}\n  {item.get('url', '')}\n  {str(item.get('description', ''))[:300]}"
            )
        chunks.append("[NewsAPI]\n" + "\n".join(formatted))

    ticker = extract_ticker(user_input)
    if ticker:
        quote = market_quote(ticker)
        if quote:
            chunks.append(f"[Alpha Vantage Quote for {ticker}]\n{quote}")

    if not chunks:
        return "No external API context available."

    return "\n\n".join(chunks)
