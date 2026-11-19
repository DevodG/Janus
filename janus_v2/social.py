"""social.py — social media access: read freely, post only on explicit approval.

Reading (no keys, no accounts): Bluesky public API, Mastodon public timelines,
Hacker News official API, Reddit RSS. Normalized to {platform, author, text,
url}. X/Twitter has no keyless official read path — stated, not scraped around.

Posting (world ring): draft-first. Requires (a) platform credentials in env
(MASTODON_TOKEN / BLUESKY_HANDLE+BLUESKY_APP_PASSWORD) and (b) a per-action
preview token — enforced in tools.call_tool. No credentials -> draft saved
locally only. Nothing posts silently, ever.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

_DRAFTS = Path(__file__).parent / "data" / "social_drafts.jsonl"


def _get(url: str):
    import httpx
    r = httpx.get(url, timeout=20, follow_redirects=True,
                  headers={"User-Agent": "Mozilla/5.0 JanusV2/1.0"})
    return r


def read_bluesky(query: str, limit: int = 10) -> list[dict]:
    r = _get(f"https://public.api.bsky.app/xrpc/app.bsky.feed.searchPosts"
             f"?q={query}&limit={limit}")
    if r.status_code != 200:
        raise RuntimeError(f"bluesky search HTTP {r.status_code} (endpoint may require auth)")
    data = r.json()
    return [{"platform": "bluesky", "author": p["author"].get("handle", ""),
             "text": p["record"].get("text", "")[:500],
             "url": f"https://bsky.app/profile/{p['author'].get('handle','')}/post/"
                    f"{p['uri'].split('/')[-1]}"} for p in data.get("posts", [])]


def read_mastodon(instance: str = "mastodon.social", limit: int = 10) -> list[dict]:
    r = _get(f"https://{instance}/api/v1/timelines/public?limit={limit}")
    if r.status_code != 200:
        raise RuntimeError(f"mastodon {instance} HTTP {r.status_code} (instance may require auth)")
    data = r.json()
    if not isinstance(data, list):
        raise RuntimeError(f"mastodon {instance} returned non-list (auth likely required)")
    from bs4 import BeautifulSoup
    return [{"platform": "mastodon", "author": p["account"].get("acct", ""),
             "text": BeautifulSoup(p.get("content", ""), "html.parser").get_text(" ")[:500],
             "url": p.get("url", "")} for p in data]


def read_hackernews(limit: int = 10) -> list[dict]:
    ids = _get("https://hacker-news.firebaseio.com/v0/topstories.json").json()[:limit]
    out = []
    for i in ids:
        item = _get(f"https://hacker-news.firebaseio.com/v0/item/{i}.json").json() or {}
        out.append({"platform": "hackernews", "author": item.get("by", ""),
                    "text": item.get("title", ""),
                    "url": item.get("url", f"https://news.ycombinator.com/item?id={i}")})
    return out


def read_reddit(subreddit: str, limit: int = 10) -> list[dict]:
    from janus_v2 import crawlers
    feed = crawlers.crawl_feed(f"https://www.reddit.com/r/{subreddit}/.rss", limit)
    return [{"platform": "reddit", "author": subreddit, "text": it["title"],
             "url": it["link"]} for it in feed["items"]]


def search_social(query: str, limit: int = 8) -> dict:
    """Fan out across keyless platforms; per-platform failures are reported, not hidden."""
    out, errors = [], {}
    for name, fn in (("bluesky", lambda: read_bluesky(query, limit)),
                     ("mastodon", lambda: read_mastodon(limit=limit)),
                     ("hackernews", lambda: read_hackernews(limit))):
        try:
            out += fn()
        except Exception as e:
            errors[name] = str(e)[:100]
    return {"posts": out, "errors": errors, "note": "X/Twitter: no keyless official read path"}


def draft_post(platform: str, text: str) -> dict:
    _DRAFTS.parent.mkdir(parents=True, exist_ok=True)
    row = {"ts": time.time(), "platform": platform, "text": text, "status": "draft"}
    with open(_DRAFTS, "a") as f:
        f.write(json.dumps(row) + "\n")
    return row


def post(platform: str, text: str) -> dict:
    """Actually post. Callers must pass tools.call_tool's world-ring preview gate."""
    if platform == "mastodon":
        token = os.environ.get("MASTODON_TOKEN")
        instance = os.environ.get("MASTODON_INSTANCE", "mastodon.social")
        if not token:
            return {"posted": False, "reason": "no MASTODON_TOKEN — draft only",
                    "draft": draft_post(platform, text)}
        import httpx
        r = httpx.post(f"https://{instance}/api/v1/statuses",
                       headers={"Authorization": f"Bearer {token}"},
                       json={"status": text}, timeout=20)
        return {"posted": r.status_code < 300, "status_code": r.status_code,
                "url": r.json().get("url") if r.status_code < 300 else None}
    if platform == "bluesky":
        handle, pw = os.environ.get("BLUESKY_HANDLE"), os.environ.get("BLUESKY_APP_PASSWORD")
        if not (handle and pw):
            return {"posted": False, "reason": "no BLUESKY_HANDLE/APP_PASSWORD — draft only",
                    "draft": draft_post(platform, text)}
        import datetime
        import httpx
        sess = httpx.post("https://bsky.social/xrpc/com.atproto.server.createSession",
                          json={"identifier": handle, "password": pw}, timeout=20).json()
        now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
        r = httpx.post("https://bsky.social/xrpc/com.atproto.repo.createRecord",
                       headers={"Authorization": f"Bearer {sess['accessJwt']}"},
                       json={"repo": sess["did"], "collection": "app.bsky.feed.post",
                             "record": {"text": text, "$type": "app.bsky.feed.post",
                                        "createdAt": now}}, timeout=20)
        return {"posted": r.status_code < 300, "status_code": r.status_code}
    return {"posted": False, "reason": f"posting to {platform} not supported "
                                       "(X requires paid API access; use draft + manual post)",
            "draft": draft_post(platform, text)}
