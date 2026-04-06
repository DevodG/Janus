"""
Custom web crawler for Janus.

Replaces external API dependencies (Tavily, NewsAPI) with self-hosted crawling.
Built on Playwright for browser automation, with stealth and noise removal.
"""

from app.services.crawler.core import JanusCrawler

__all__ = ["JanusCrawler"]
