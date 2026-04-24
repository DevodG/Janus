"""
HTML → Markdown conversion with noise removal for Janus crawler.
Strips ads, nav, footer, scripts, styles — keeps the content.
"""

import re
import logging
from typing import List, Dict, Any
from urllib.parse import urljoin

logger = logging.getLogger(__name__)

NOISE_SELECTORS = [
    "script",
    "style",
    "noscript",
    "iframe",
    "svg",
    "canvas",
    "nav",
    "footer",
    "header",
    "aside",
    ".ad",
    ".ads",
    ".advertisement",
    ".ad-container",
    ".sidebar",
    ".navigation",
    ".menu",
    ".breadcrumb",
    ".cookie",
    ".cookie-banner",
    ".gdpr",
    ".social-share",
    ".share-buttons",
    ".comments",
    ".comment-section",
    ".newsletter",
    ".subscribe",
    ".popup",
    ".modal",
    ".overlay",
    "#ad",
    "#ads",
    "#sidebar",
    "#navigation",
    "#footer",
    ".footer",
    ".header",
]

CONTENT_SELECTORS = [
    "article",
    "main",
    ".content",
    ".article",
    ".post",
    ".entry",
    "#content",
    "#main",
    "#article",
    ".post-content",
    ".article-body",
    ".story-body",
]


class ContentProcessor:
    """Convert HTML to clean Markdown with noise removal."""

    def process(self, html: str) -> str:
        """Convert HTML to clean Markdown."""
        if not html:
            return ""

        html = self._strip_noise(html)
        markdown = self._html_to_markdown(html)
        markdown = self._clean_markdown(markdown)
        return markdown

    def _strip_noise(self, html: str) -> str:
        """Remove noise elements from HTML."""
        for selector in NOISE_SELECTORS:
            if selector.startswith("."):
                pattern = rf'<[^>]*class="[^"]*{re.escape(selector[1:])}[^"]*"[^>]*>.*?</[^>]+>'
                html = re.sub(pattern, "", html, flags=re.DOTALL | re.IGNORECASE)
            elif selector.startswith("#"):
                pattern = (
                    rf'<[^>]*id="[^"]*{re.escape(selector[1:])}[^"]*"[^>]*>.*?</[^>]+>'
                )
                html = re.sub(pattern, "", html, flags=re.DOTALL | re.IGNORECASE)
            else:
                pattern = rf"<{selector}[^>]*>.*?</{selector}>"
                html = re.sub(pattern, "", html, flags=re.DOTALL | re.IGNORECASE)

        html = re.sub(r"<!--.*?-->", "", html, flags=re.DOTALL)
        html = re.sub(r"\s+", " ", html)
        return html

    def _html_to_markdown(self, html: str) -> str:
        """Convert HTML to Markdown."""
        try:
            from markdownify import markdownify as md

            return md(html, heading_style="ATX", bullets="-", strip=["img"])
        except ImportError:
            return self._fallback_html_to_text(html)

    def _fallback_html_to_text(self, html: str) -> str:
        """Fallback HTML to text conversion without markdownify."""
        text = re.sub(r"<br\s*/?>", "\n", html)
        text = re.sub(r"</(?:p|div|h[1-6]|li|tr)>", "\n\n", text, flags=re.IGNORECASE)
        text = re.sub(
            r"<h([1-6])[^>]*>",
            lambda m: f"\n\n{'#' * int(m.group(1))} ",
            text,
            flags=re.IGNORECASE,
        )
        text = re.sub(r"</?(?:b|strong)>", "**", text, flags=re.IGNORECASE)
        text = re.sub(r"</?(?:i|em)>", "*", text, flags=re.IGNORECASE)
        text = re.sub(
            r'<a[^>]*href="([^"]*)"[^>]*>(.*?)</a>',
            r"\2 (\1)",
            text,
            flags=re.IGNORECASE,
        )
        text = re.sub(r"<[^>]+>", "", text)
        text = re.sub(r"&nbsp;", " ", text)
        text = re.sub(r"&amp;", "&", text)
        text = re.sub(r"&lt;", "<", text)
        text = re.sub(r"&gt;", ">", text)
        text = re.sub(r"&quot;", '"', text)
        text = re.sub(r"&#39;", "'", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    def _clean_markdown(self, markdown: str) -> str:
        """Clean up the markdown output."""
        lines = markdown.split("\n")
        cleaned = []
        prev_blank = False

        for line in lines:
            line = line.strip()
            if not line:
                if not prev_blank:
                    cleaned.append("")
                prev_blank = True
            else:
                cleaned.append(line)
                prev_blank = False

        result = "\n".join(cleaned).strip()
        if len(result) > 50000:
            result = (
                result[:50000]
                + "\n\n[Content truncated — too long for full extraction]"
            )
        return result

    def extract_links(self, html: str, base_url: str = "") -> List[str]:
        """Extract all links from HTML."""
        links = []
        pattern = r'<a[^>]*href=["\']([^"\']+)["\'][^>]*>'
        for match in re.finditer(pattern, html, re.IGNORECASE):
            url = match.group(1)
            if url and not url.startswith(("#", "javascript:", "mailto:")):
                if base_url and not url.startswith(("http://", "https://")):
                    url = urljoin(base_url, url)
                links.append(url)
        return list(set(links))

    def extract_metadata(self, html: str, title: str = "") -> Dict[str, Any]:
        """Extract metadata from HTML."""
        metadata = {}

        if title:
            metadata["title"] = title

        og_title = re.search(
            r'<meta[^>]*property="og:title"[^>]*content="([^"]*)"', html, re.IGNORECASE
        )
        if og_title:
            metadata["og_title"] = og_title.group(1)

        og_desc = re.search(
            r'<meta[^>]*property="og:description"[^>]*content="([^"]*)"',
            html,
            re.IGNORECASE,
        )
        if og_desc:
            metadata["og_description"] = og_desc.group(1)

        og_image = re.search(
            r'<meta[^>]*property="og:image"[^>]*content="([^"]*)"', html, re.IGNORECASE
        )
        if og_image:
            metadata["og_image"] = og_image.group(1)

        author = re.search(
            r'<meta[^>]*name="author"[^>]*content="([^"]*)"', html, re.IGNORECASE
        )
        if author:
            metadata["author"] = author.group(1)

        pub_date = re.search(
            r'<meta[^>]*property="article:published_time"[^>]*content="([^"]*)"',
            html,
            re.IGNORECASE,
        )
        if pub_date:
            metadata["published_at"] = pub_date.group(1)

        return metadata
