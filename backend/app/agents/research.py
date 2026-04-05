"""
Research agent — MiroOrg v2.
Uses Tavily web search, News API, Knowledge Store, and API Discovery
to gather context before calling the LLM for structured analysis.
"""

import os, json, re, logging
import httpx
from app.agents._model import call_model
from app.agents.api_discovery import discover_apis, call_discovered_api
from app.config import load_prompt
from app.memory import knowledge_store

logger = logging.getLogger(__name__)

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")
NEWS_API_KEY = os.getenv("NEWS_API_KEY", os.getenv("NEWSAPI_KEY", ""))


def _extract_json(text: str) -> dict | None:
    """Robustly extract JSON from model response."""
    # Try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Strip markdown code fences
    cleaned = re.sub(r"```(?:json)?\s*\n?", "", text).strip()
    cleaned = re.sub(r"\n?```\s*$", "", cleaned).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Find JSON object in text
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidate = text[start : end + 1]
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    return None


# ─── Tool: Tavily Web Search ─────────────────────────────────────────────────


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


# ─── Tool: News API ──────────────────────────────────────────────────────────


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


# ─── Research Node ────────────────────────────────────────────────────────────


def run(state: dict) -> dict:
    route = state.get("route", {})
    intent = route.get("intent", state.get("user_input", ""))
    domain = route.get("domain", "general")

    context_blocks = []

    # Step 1: Tavily web search
    web_results = tavily_search(intent)
    if web_results:
        formatted = "\n".join(
            f"- {r.get('title', 'Untitled')}\n  URL: {r.get('url', '')}\n  {r.get('content', '')[:300]}"
            for r in web_results
        )
        context_blocks.append(f"[Web Search Results]\n{formatted}")

    # Step 2: News API (if requires_news or finance domain)
    if route.get("requires_news") or domain == "finance":
        news = news_search(intent)
        if news:
            formatted = "\n".join(
                f"- {a['title']} ({a['source']}, {a['publishedAt']})\n  {a.get('description', '')[:200]}"
                for a in news
            )
            context_blocks.append(f"[News Articles]\n{formatted}")

    # Step 3: Knowledge store
    knowledge = knowledge_store.search(intent, domain=domain)
    if knowledge:
        formatted = "\n".join(
            f"- {k.get('text', k.get('content', ''))[:300]}" for k in knowledge
        )
        context_blocks.append(f"[Knowledge Base]\n{formatted}")

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

    # Build context block
    context_str = (
        "\n\n".join(context_blocks)
        if context_blocks
        else "No external context retrieved."
    )

    # Step 6: Call LLM
    prompt = load_prompt("research")
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

    try:
        raw_response = call_model(messages)
    except Exception as e:
        logger.error(f"[AGENT ERROR] research: {e}")
        raw_response = None
        result = {"status": "error", "reason": str(e)}

    if raw_response:
        result = _extract_json(raw_response)
        if result is None:
            # Last resort: use raw text as summary
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

    if result is None or "error" in result:
        logger.warning(
            f"[AGENT ERROR] research: {result.get('error') if result else 'result is None'}"
        )
        result = {
            "summary": "Research encountered an error during analysis.",
            "key_facts": [],
            "sources": [],
            "gaps": ["analysis failed"],
            "confidence": 0.0,
        }

    return {**state, "research": result}
