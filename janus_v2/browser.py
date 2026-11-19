"""browser.py — roam like a human: real Chromium, rendered pages, natural moves.

Playwright-driven: open page, let JS render, scroll in steps, read visible
text + links, follow the most relevant link, repeat — with human pacing
(0.8-2.0s pauses, scroll dwell). Bounds are hard: max pages/depth, same-domain
by default, robots.txt respected, every hop receipt-logged.
Not included, by design: fingerprint spoofing, captcha solving, or any
bot-detection evasion. Roaming like a human means browsing, not deceiving.
"""
from __future__ import annotations

import random
import time
import urllib.robotparser
from urllib.parse import urljoin, urlparse

_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 JanusV2/1.0"


def _allowed(url: str, cache: dict) -> bool:
    host = urlparse(url).netloc
    if host not in cache:
        rp = urllib.robotparser.RobotFileParser()
        try:
            rp.set_url(f"https://{host}/robots.txt")
            rp.read()
        except Exception:
            rp = None
        cache[host] = rp
    rp = cache[host]
    return True if rp is None else rp.can_fetch(_UA, url)


def act(url: str, actions: list[dict]) -> dict:
    """Stagehand/browser-use style actions: observe -> act -> extract, in a real browser.

    Actions: {"do": "click_text", "text": "..."} | {"do": "fill", "selector": "...",
    "value": "..."} | {"do": "extract", "selector": "..."} | {"do": "goto", "url": "..."}
    Human pacing between actions; every step recorded in the trail.
    """
    from playwright.sync_api import sync_playwright

    trail, extracted = [], {}
    rng = random.Random(7)
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page(user_agent=_UA)
        page.goto(url, wait_until="domcontentloaded", timeout=20000)
        for step in actions:
            time.sleep(rng.uniform(0.6, 1.4))
            kind = step.get("do")
            if kind == "click_text":
                page.get_by_text(step["text"], exact=False).first.click(timeout=8000)
                page.wait_for_load_state("domcontentloaded", timeout=15000)
                trail.append(f"click_text:{step['text']} -> {page.url}")
            elif kind == "fill":
                page.fill(step["selector"], step["value"], timeout=8000)
                trail.append(f"fill:{step['selector']}")
            elif kind == "extract":
                extracted[step.get("name", step["selector"])] = page.inner_text(
                    step["selector"], timeout=8000)[:4000]
                trail.append(f"extract:{step['selector']}")
            elif kind == "goto":
                page.goto(step["url"], wait_until="domcontentloaded", timeout=20000)
                trail.append(f"goto:{step['url']}")
            else:
                trail.append(f"unknown-action:{kind}")
        result = {"url": page.url, "title": page.title(), "trail": trail, "extracted": extracted}
        browser.close()
    return result


def roam(start_url: str, goal_keywords: list[str], max_pages: int = 5,
         max_depth: int = 2, same_domain: bool = True) -> dict:
    """Browser-roam from start_url toward goal_keywords. Returns findings+trail."""
    from playwright.sync_api import sync_playwright  # local: import cost only when used

    findings, trail, visited = [], [], set()
    queue = [(start_url, 0)]
    robots: dict = {}
    rng = random.Random(11)
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page(user_agent=_UA)
        while queue and len(visited) < max_pages:
            url, depth = queue.pop(0)
            if url in visited or not _allowed(url, robots):
                continue
            visited.add(url)
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=20000)
                time.sleep(rng.uniform(0.8, 2.0))  # human pause: read the page
                for _ in range(3):  # scroll like reading
                    page.mouse.wheel(0, 900)
                    time.sleep(rng.uniform(0.4, 1.1))
                text = page.inner_text("body")[:6000]
                links = page.eval_on_selector_all(
                    "a[href]", "els => els.map(e => [e.innerText.slice(0,80), e.href])")
            except Exception as e:
                trail.append({"url": url, "error": str(e)[:120]})
                continue
            score = sum(k.lower() in text.lower() for k in goal_keywords)
            findings.append({"url": url, "depth": depth, "relevance": score,
                             "text": text[:2000]})
            trail.append({"url": url, "depth": depth, "links": len(links)})
            if depth < max_depth:
                host = urlparse(start_url).netloc
                ranked = sorted(
                    links, key=lambda kv: -sum(k.lower() in (kv[0] or "").lower()
                                               for k in goal_keywords))
                for label, href in ranked[:4]:
                    full = urljoin(url, href)
                    if same_domain and urlparse(full).netloc != host:
                        continue
                    if full not in visited:
                        queue.append((full, depth + 1))
        browser.close()
    findings.sort(key=lambda f: -f["relevance"])
    return {"findings": findings, "trail": trail, "pages_visited": len(visited)}
