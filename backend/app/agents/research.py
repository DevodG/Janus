from __future__ import annotations
"""
Research agent — Janus.
Uses lightweight HTTP crawler (no Playwright needed), Knowledge Store, and API Discovery
to gather context before calling the LLM for structured analysis.
"""

import os
import json
import re
import logging
from urllib.parse import quote_plus
from typing import Optional, List, Dict, Any
import httpx
from app.agents._model import call_model
from app.agents.api_discovery import discover_apis, call_discovered_api
from app.config import load_prompt, CRAWLER_ENABLED, NEWS_API_KEY, TAVILY_API_KEY
from app.memory import knowledge_store
from app.services.external_sources import deep_web_research_bundle
from app.services.distillation_engine import KnowledgeDistiller
from app.services.metrics_collector import MetricsCollector

distiller = KnowledgeDistiller()
metrics = MetricsCollector()

logger = logging.getLogger(__name__)

JINA_READER_BASE = os.getenv("JINA_READER_BASE", "https://r.jina.ai/")


def _extract_json(text: str) -> Optional[dict]:
    """Robustly extract JSON from model response."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    cleaned = re.sub(r"```(?:json)?\s*\n?", "", text).strip()
    cleaned = re.sub(r"\n?```\s*$", "", cleaned).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidate = text[start : end + 1]
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    return None


def _deterministic_research_result(
    intent: str,
    route: dict,
    deep_bundle: dict,
    news: list[dict],
    knowledge: list[dict],
    simulation: Optional[dict],
    finance: Optional[dict],
) -> dict:
    synthesis = deep_bundle.get("synthesis", {}) if isinstance(deep_bundle, dict) else {}
    top_sources = synthesis.get("top_sources", []) if isinstance(synthesis.get("top_sources"), list) else []
    key_points = synthesis.get("key_points", []) if isinstance(synthesis.get("key_points"), list) else []
    avg_credibility = float(synthesis.get("avg_credibility", 0.0) or 0.0)

    summary_parts = []
    if synthesis.get("summary"):
        summary_parts.append(synthesis.get("summary", ""))

    if route.get("domain") == "finance":
        summary_parts.append(
            "For this finance request, Janus is weighting official company sources and high-credibility financial reporting above generic commentary."
        )

    if simulation and isinstance(simulation, dict):
        simulation_synthesis = simulation.get("synthesis", {})
        if simulation_synthesis.get("most_likely"):
            summary_parts.append(
                f"The scenario layer currently points to: {simulation_synthesis.get('most_likely', '')}."
            )

    if finance and isinstance(finance, dict):
        quote = finance.get("quote", {}) if isinstance(finance.get("quote"), dict) else {}
        metrics = finance.get("key_metrics", {}) if isinstance(finance.get("key_metrics"), dict) else {}
        price = quote.get("05. price") if isinstance(quote, dict) else None
        if price is None:
            price = metrics.get("price")
        market_cap = metrics.get("market_cap")
        if price is not None:
            summary_parts.append(
                f"Structured market data was available with a latest quoted price of {price}."
            )
        if market_cap:
            summary_parts.append(f"Reported market capitalization was {market_cap}.")

    if not summary_parts:
        summary_parts.append(
            f"Janus assembled a deterministic research view for: {intent}. External model synthesis was unavailable, so this result is grounded directly in retrieved evidence."
        )

    sources = [
        f"{item.get('title', item.get('url', 'source'))} [{item.get('credibility_score', 0.0):.2f}]"
        for item in top_sources[:6]
    ]
    if news:
        sources.extend(
            f"{item.get('title', 'news item')} ({item.get('source', 'news')})"
            for item in news[:3]
        )

    key_facts = [
        f"{item.get('point', '')} (source={item.get('source', '')}, credibility={item.get('credibility_score', 0.0):.2f})"
        for item in key_points[:4]
        if item.get("point")
    ]
    if knowledge:
        key_facts.extend(
            f"Knowledge base context: {str(item.get('text', item.get('content', '')))[:220]}"
            for item in knowledge[:2]
        )

    gaps = []
    if not top_sources:
        gaps.append("no high-confidence deep-web sources were retained")
    if route.get("requires_finance_data") and not finance and route.get("domain") == "finance":
        gaps.append("live market API data was unavailable, so the view relies on web evidence")
    if route.get("domain") == "finance" and not news:
        gaps.append("fresh finance/news API coverage was limited in this run")

    confidence = max(avg_credibility, 0.35 if top_sources else 0.25)
    return {
        "summary": " ".join(part.strip() for part in summary_parts if part).strip(),
        "key_facts": key_facts,
        "sources": list(dict.fromkeys(sources)),
        "gaps": gaps,
        "confidence": round(min(confidence, 0.85), 3),
        "deep_web": {
            "summary": synthesis.get("summary", ""),
            "avg_credibility": avg_credibility,
            "query_variants": deep_bundle.get("query_variants", []),
            "top_sources": top_sources,
            "key_points": key_points,
        },
        "mode": "deterministic_fallback",
    }


def _duckduckgo_urls(query: str, max_results: int = 5) -> list[str]:
    """Get URLs from DuckDuckGo HTML search (no API key)."""
    urls = []
    try:
        search_url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
        with httpx.Client(timeout=15) as client:
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            }
            resp = client.get(search_url, headers=headers, follow_redirects=True)
            if resp.status_code == 200:
                pattern = re.compile(r'class="result__a"[^>]*href="([^"]+)"')
                for match in pattern.finditer(resp.text):
                    url = match.group(1)
                    if url and url.startswith("http") and url not in urls:
                        urls.append(url)
                        if len(urls) >= max_results:
                            break
    except Exception as e:
        logger.warning(f"DuckDuckGo search failed: {e}")
    return urls


def _extract_content(url: str) -> Optional[str]:
    """Extract clean content from a URL using Jina Reader (free, no key needed)."""
    try:
        jina_url = f"{JINA_READER_BASE}{url}"
        with httpx.Client(timeout=12) as client:
            r = client.get(jina_url, follow_redirects=True)
            if r.status_code == 200 and len(r.text) > 100:
                return r.text[:5000]
    except Exception:
        pass

    try:
        with httpx.Client(timeout=10) as client:
            headers = {"User-Agent": "Mozilla/5.0 (compatible; Janus/1.0)"}
            r = client.get(url, headers=headers, follow_redirects=True, timeout=10)
            if r.status_code == 200:
                text = re.sub(r"<script[^>]*>.*?</script>", "", r.text, flags=re.DOTALL)
                text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL)
                text = re.sub(r"<[^>]+>", " ", text)
                text = re.sub(r"\s+", " ", text).strip()
                return text[:5000] if len(text) > 100 else None
    except Exception:
        pass

    return None


def crawl_web_search(query: str, max_results: int = 3) -> list[dict]:
    """
    Self-hosted web research: DuckDuckGo for URLs → Jina Reader for content.
    Optimized for speed: 3 results, parallel fetch, short timeouts.
    """
    if not CRAWLER_ENABLED:
        return []

    urls = _duckduckgo_urls(query, max_results)
    if not urls:
        return []

    results = []
    # Fetch in parallel with ThreadPoolExecutor
    import concurrent.futures

    def _fetch_one(url):
        content = _extract_content(url)
        if content:
            title = content.split("\n")[0][:200] if "\n" in content else url
            return {"title": title, "url": url, "content": content[:2000]}
        return None

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        futures = {executor.submit(_fetch_one, url): url for url in urls[:max_results]}
        for future in concurrent.futures.as_completed(futures, timeout=25):
            try:
                result = future.result()
                if result:
                    results.append(result)
            except Exception:
                pass

    return results


def tavily_search(query: str, max_results: int = 5) -> list[dict]:
    """Returns list of {title, url, content} dicts."""
    if not TAVILY_API_KEY:
        return []
    try:
        r = httpx.post(
            "https://api.tavily.com/search",
            json={
                "api_key": TAVILY_API_KEY,
                "query": query,
                "search_depth": "advanced",
                "max_results": max_results,
                "include_raw_content": False,
            },
            timeout=30,
        )
        r.raise_for_status()
        return r.json().get("results", [])
    except Exception as e:
        logger.warning(f"Tavily search failed: {e}")
        return []


def news_search(query: str, max_articles: int = 5) -> list[dict]:
    """Returns list of {title, source, publishedAt, description} dicts."""
    if not NEWS_API_KEY:
        return []
    try:
        r = httpx.get(
            "https://newsapi.org/v2/everything",
            params={
                "apiKey": NEWS_API_KEY,
                "q": query,
                "sortBy": "publishedAt",
                "language": "en",
                "pageSize": max_articles,
            },
            timeout=30,
        )
        r.raise_for_status()
        return [
            {
                "title": a["title"],
                "source": a["source"]["name"],
                "publishedAt": a["publishedAt"],
                "description": a["description"],
            }
            for a in r.json().get("articles", [])
        ]
    except Exception as e:
        logger.warning(f"News search failed: {e}")
        return []


def run(state: dict) -> dict:
    start_time_research = time.perf_counter()
    route = state.get("route", {})
    intent = route.get("intent", state.get("user_input", ""))
    domain = route.get("domain", "general")
    runtime_context = state.get("context", {})
    complexity = route.get("complexity", "medium")

    # Knowledge-gap driven research: identify if this query touches a known weakness
    reflection = runtime_context.get("self_reflection", {})
    gaps = reflection.get("gaps", [])
    # Search for gap topics that intersect with our intent/user_input
    relevant_gaps = [
        g.get("topic", "") 
        for g in gaps 
        if g.get("topic", "").lower() in intent.lower() or g.get("topic", "").lower() in state.get("user_input", "").lower()
    ]
    
    if relevant_gaps:
        logger.info(f"[RESEARCH] Targeting known gaps to improve Janus: {relevant_gaps}")
        # Append gap-bridging directives to the research intent
        intent = f"{intent} (priority: investigate specifically for gaps in {', '.join(relevant_gaps)})"

    context_blocks = []

    # Step 1: Deeper public-web research (multi-source search + reader + crawler)
    deep_max_results = 4
    deep_follow_links = 0
    deep_variants = 2

    if domain == "finance" or route.get("requires_finance_data"):
        deep_max_results = 5
        deep_follow_links = 1
        deep_variants = 3

    if route.get("requires_simulation") or complexity in {"high", "very_high"}:
        deep_max_results = 6
        deep_follow_links = 1
        deep_variants = 4

    deep_bundle = deep_web_research_bundle(
        intent,
        max_results=deep_max_results,
        follow_links=deep_follow_links,
        max_variants=deep_variants,
    )
    deep_results = deep_bundle.get("results", [])
    deep_brief = deep_bundle.get("synthesis", {})
    if deep_results:
        context_blocks.append(f"[Deep Web Brief]\n{deep_brief.get('summary', '')}")
        if deep_bundle.get("query_variants"):
            context_blocks.append(
                f"[Deep Web Query Variants]\n{json.dumps(deep_bundle.get('query_variants', []), indent=2)}"
            )
        formatted = "\n".join(
            (
                f"- {r.get('title', 'Untitled')}\n"
                f"  URL: {r.get('url', '')}\n"
                f"  Source: {r.get('source', 'web')}\n"
                f"  Credibility: {r.get('credibility_score', 0.0):.2f} ({r.get('credibility_reason', 'unknown')})\n"
                f"  {r.get('content', '')[:700]}"
                + (
                    f"\n  Related read: {r.get('related_reads', [])[0].get('url', '')} [{r.get('related_reads', [])[0].get('credibility_score', 0.0):.2f}]\n"
                    f"  {str(r.get('related_reads', [])[0].get('content', ''))[:250]}"
                    if r.get('related_reads')
                    else ""
                )
            )
            for r in deep_results
        )
        context_blocks.append(f"[Deep Web Results]\n{formatted}")
    else:
        crawl_results = crawl_web_search(intent)
        if crawl_results:
            formatted = "\n".join(
                f"- {r.get('title', 'Untitled')}\n  URL: {r.get('url', '')}\n  {r.get('content', '')[:500]}"
                for r in crawl_results
            )
            context_blocks.append(f"[Web Crawl Results]\n{formatted}")
    if not deep_results and not context_blocks and TAVILY_API_KEY:
        web_results = tavily_search(intent)
        if web_results:
            formatted = "\n".join(
                f"- {r.get('title', 'Untitled')}\n  URL: {r.get('url', '')}\n  {r.get('content', '')[:300]}"
                for r in web_results
            )
            context_blocks.append(f"[Web Search Results]\n{formatted}")

    # Step 2: News API (if requires_news or finance domain)
    news = []
    if route.get("requires_news") or domain == "finance":
        news = news_search(intent)
        if news:
            formatted = "\n".join(
                f"- {a['title']} ({a['source']}, {a['publishedAt']})\n  {a.get('description', '')[:200]}"
                for a in news
            )
            context_blocks.append(f"[News Articles]\n{formatted}")
            
            # Forensic Step: Perform Multimodal Analysis on News Video if available
            try:
                from app.services.mmsa_engine import mmsa_engine
                for article in news[:2]: # Only analyze top 2 for efficiency
                    url = article.get("url", "")
                    if "youtube.com" in url or "youtu.be" in url:
                        logger.info(f"[RESEARCH-FORENSICS] Triggering multimodal check for {url}")
                        forensic_results = mmsa_engine.analyze_url(url, article.get("title", ""))
                        if "error" not in forensic_results:
                            context_blocks.append(f"[Multimodal Forensic Report - {url}]\n{json.dumps(forensic_results, indent=2)}")
            except Exception as e:
                logger.warning(f"[RESEARCH-FORENSICS] Multimodal check failed: {e}")

    # Step 3: Knowledge store
    knowledge = knowledge_store.search(intent, domain=domain)
    if knowledge:
        formatted = "\n".join(
            f"- {k.get('text', k.get('content', ''))[:300]}" for k in knowledge
        )
        context_blocks.append(f"[Knowledge Base]\n{formatted}")

    # Step 3b: Runtime memory and self-awareness context
    similar_cases = runtime_context.get("memory", {}).get("similar_cases", [])
    if similar_cases:
        formatted = "\n".join(
            f"- {c.get('query', '')[:140]} (domain={c.get('domain', 'general')}, score={c.get('score', 0)})"
            for c in similar_cases[:3]
        )
        context_blocks.append(f"[Similar Past Cases]\n{formatted}")

    reflection = runtime_context.get("self_reflection", {})
    reflection_gaps = reflection.get("gaps", [])
    if reflection_gaps:
        formatted = "\n".join(
            f"- {g.get('topic', '')}: {g.get('reason', '')[:140]}"
            for g in reflection_gaps[:3]
        )
        context_blocks.append(f"[Known Weaknesses]\n{formatted}")

    adaptive_context = runtime_context.get("adaptive_intelligence", {})
    domain_expertise = adaptive_context.get("domain_expertise")
    if domain_expertise:
        context_blocks.append(
            f"[Accumulated Domain Expertise]\n{json.dumps(domain_expertise, indent=2)}"
        )

    # Step 4: API Discovery
    discovered = discover_apis(query=intent, domain=domain)
    for api in discovered[:3]:
        extra_data = call_discovered_api(api, {"q": intent})
        context_blocks.append(f"[{api.get('name', 'Discovered API')}]: {extra_data}")

    # Step 5: Include simulation and finance data if available in state
    if state.get("simulation"):
        context_blocks.append(
            f"[Simulation Results]\n{json.dumps(state['simulation'], indent=2)}"
        )
    if state.get("finance"):
        context_blocks.append(
            f"[Finance Data]\n{json.dumps(state['finance'], indent=2)}"
        )

    # NEW: Distilled Domain Insights
    model_insights = []
    if domain != "general":
        domain_model = distiller.load_model(domain)
        if domain_model:
            model_insights = distiller.query_model(domain_model, intent, top_k=3)
            if model_insights:
                formatted = "\n".join(f"• {insight}" for insight in model_insights)
                context_blocks.append(f"[Distilled Domain Insights ({domain})]\n{formatted}")
                logger.info(f"[RESEARCH-MODEL] Injected {len(model_insights)} insights for {domain}")

    # Build context block
    context_str = (
        "\n\n".join(context_blocks)
        if context_blocks
        else "No external context retrieved."
    )

    # Step 6: Call LLM
    prompt = load_prompt("research")
    
    # Inject User Persona for Adaptive Intelligence
    user_persona = runtime_context.get("user_persona", {}) if 'runtime_context' in locals() else {}
    if user_persona.get("context_injection"):
        prompt = f"{prompt}\n\n{user_persona['context_injection']}"

    messages = [
        {"role": "system", "content": prompt},
        {
            "role": "user",
            "content": (
                f"User request: {state.get('user_input', intent)}\n\n"
                f"[CONTEXT]\n{context_str}\n\n"
                "Produce structured JSON output:\n"
                "{\n"
                '  "summary": "<comprehensive analysis — 3-5 paragraphs of deep thinking>",\n'
                '  "key_facts": ["<fact 1 with source>", "<fact 2 with source>"],\n'
                '  "sources": ["<source 1>", "<source 2>"],\n'
                '  "gaps": ["<what\'s missing and why it matters>"],\n'
                '  "confidence": 0.0-1.0\n'
                "}\n"
                "If context is empty, return gaps: ['no data retrieved']. Do not hallucinate."
            ),
        },
    ]

    result = None
    raw_response = None
    deterministic_summary_parts = [
        deep_brief.get("summary", "")
        or "Janus assembled a grounded research bundle from retrieved public-web evidence."
    ]
    if domain == "finance":
        deterministic_summary_parts.append(
            "For this finance request, Janus is weighting official company disclosures and high-credibility financial reporting above generic commentary."
        )
    if state.get("simulation") and isinstance(state.get("simulation"), dict):
        sim_synthesis = state.get("simulation", {}).get("synthesis", {})
        if sim_synthesis.get("most_likely"):
            deterministic_summary_parts.append(
                f"The scenario layer currently leans toward: {sim_synthesis.get('most_likely', '')}."
            )
    deterministic_research = {
        "summary": " ".join(
            part.strip() for part in deterministic_summary_parts if part
        ).strip(),
        "key_facts": [
            f"{item.get('point', '')} (source={item.get('source', '')}, credibility={item.get('credibility_score', 0.0):.2f})"
            for item in deep_brief.get("key_points", [])[:4]
            if item.get("point")
        ],
        "sources": [
            f"{item.get('title', item.get('url', 'source'))} [{item.get('credibility_score', 0.0):.2f}]"
            for item in deep_brief.get("top_sources", [])[:6]
        ],
        "gaps": [
            "model-based research synthesis unavailable; result assembled from retrieved evidence"
        ],
        "confidence": min(
            max(float(deep_brief.get("avg_credibility", 0.0) or 0.0), 0.35), 0.85
        ),
        "mode": "deterministic_fallback",
    }

    if news:
        deterministic_research["sources"].extend(
            f"{item.get('title', 'news item')} ({item.get('source', 'news')})"
            for item in news[:3]
        )
    if knowledge:
        deterministic_research["key_facts"].extend(
            f"Knowledge base context: {str(item.get('text', item.get('content', '')))[:220]}"
            for item in knowledge[:2]
        )
    deterministic_research["sources"] = list(dict.fromkeys(deterministic_research["sources"]))

    # Extract personality for adaptive scaling
    adaptive = runtime_context.get("adaptive_intelligence", {})
    personality = adaptive.get("system_personality", {})

    try:
        raw_response = call_model(messages, personality=personality)
    except Exception as e:
        logger.error(f"[AGENT ERROR] research: {e}")
        raw_response = None
        result = {**deterministic_research, "reason": str(e)}

    if raw_response:
        result = _extract_json(raw_response)
        if result is None:
            logger.warning(
                f"[AGENT PARSE FALLBACK] research: using raw text as summary"
            )
            result = {
                "summary": raw_response[:2000],
                "key_facts": [],
                "sources": [],
                "gaps": ["response format could not be parsed"],
                "confidence": 0.3,
            }

    if result is None or "error" in result or result.get("status") == "error":
        logger.warning(
            f"[AGENT ERROR] research: {result.get('error') if result else 'result is None'}"
        )
        result = deterministic_research

    deep_sources = [
        f"{item.get('title', item.get('url', 'source'))} [{item.get('credibility_score', 0.0):.2f}]"
        for item in deep_brief.get("top_sources", [])[:4]
    ]
    if deep_sources:
        existing_sources = result.get("sources", []) if isinstance(result.get("sources"), list) else []
        result["sources"] = list(dict.fromkeys([*existing_sources, *deep_sources]))

    deep_facts = [
        f"{item.get('point', '')} (source={item.get('source', '')}, credibility={item.get('credibility_score', 0.0):.2f})"
        for item in deep_brief.get("key_points", [])[:3]
        if item.get("point")
    ]
    if deep_facts:
        existing_facts = result.get("key_facts", []) if isinstance(result.get("key_facts"), list) else []
        result["key_facts"] = list(dict.fromkeys([*existing_facts, *deep_facts]))

    result["deep_web"] = {
        "summary": deep_brief.get("summary", ""),
        "avg_credibility": deep_brief.get("avg_credibility", 0.0),
        "query_variants": deep_bundle.get("query_variants", []),
        "top_sources": deep_brief.get("top_sources", []),
        "key_points": deep_brief.get("key_points", []),
    }

    # Log metrics
    try:
        metrics.log_query(
            domain=domain,
            model_enhanced=len(model_insights) > 0,
            insight_count=len(model_insights),
            latency_ms=(time.perf_counter() - start_time_research) * 1000 if 'start_time_research' in locals() else 0,
            query=intent
        )
    except Exception:
        pass

    return {**state, "research": result}
