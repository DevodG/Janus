"""
Core crawler logic for Janus.
Navigate, wait, capture, retry — async-first.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field

from app.services.crawler.browser import BrowserManager
from app.services.crawler.processor import ContentProcessor
from app.config import CRAWLER_TIMEOUT

logger = logging.getLogger(__name__)


@dataclass
class CrawlResult:
    url: str
    success: bool
    markdown: str = ""
    title: str = ""
    links: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


class JanusCrawler:
    """
    Self-hosted web crawler — no API keys, no rate limits.
    Uses Playwright for browser automation with stealth.
    """

    def __init__(self, timeout: int = CRAWLER_TIMEOUT):
        self.timeout = timeout
        self._processor = ContentProcessor()

    async def crawl(self, url: str) -> CrawlResult:
        """Crawl a single URL and return clean content."""
        async with BrowserManager() as browser:
            page = await browser.get_page()

            try:
                response = await page.goto(
                    url,
                    wait_until="domcontentloaded",
                    timeout=self.timeout * 1000,
                )

                if response and response.status >= 400:
                    return CrawlResult(
                        url=url,
                        success=False,
                        error=f"HTTP {response.status}",
                    )

                await page.wait_for_load_state("networkidle", timeout=10000)

                html = await page.content()
                title = await page.title()

                markdown = self._processor.process(html)
                links = self._processor.extract_links(html, url)
                metadata = self._processor.extract_metadata(html, title)

                return CrawlResult(
                    url=url,
                    success=True,
                    markdown=markdown,
                    title=title,
                    links=links,
                    metadata=metadata,
                )

            except asyncio.TimeoutError:
                logger.warning(f"Crawl timeout: {url}")
                return CrawlResult(url=url, success=False, error="Timeout")
            except Exception as e:
                logger.warning(f"Crawl failed: {url} — {e}")
                return CrawlResult(url=url, success=False, error=str(e)[:200])

    async def crawl_batch(
        self, urls: List[str], max_concurrent: int = 3
    ) -> List[CrawlResult]:
        """Crawl multiple URLs concurrently."""
        semaphore = asyncio.Semaphore(max_concurrent)

        async def _crawl_one(url: str) -> CrawlResult:
            async with semaphore:
                return await self.crawl(url)

        tasks = [_crawl_one(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        return [
            r
            if isinstance(r, CrawlResult)
            else CrawlResult(url="", success=False, error=str(r))
            for r in results
        ]

    def crawl_sync(self, url: str) -> CrawlResult:
        """Synchronous wrapper for use in non-async contexts."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures

                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, self.crawl(url))
                    return future.result()
            return loop.run_until_complete(self.crawl(url))
        except RuntimeError:
            return asyncio.run(self.crawl(url))
