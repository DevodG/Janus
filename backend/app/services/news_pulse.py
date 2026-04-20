"""
News Pulse — Background daemon service for Janus.
Fetches news from NewsAPI, classifies signal vs noise, stores signals.
"""

import os
import json
import time
import logging
import httpx
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

try:
    from app.config import DATA_DIR as BASE_DATA_DIR
except ImportError:
    BASE_DATA_DIR = Path(__file__).resolve().parent.parent / "data"

DATA_DIR = Path(BASE_DATA_DIR) / "daemon"
DATA_DIR.mkdir(parents=True, exist_ok=True)


class NewsPulse:
    def __init__(self, topics: List[str] = None):
        self.api_key = os.getenv("NEWS_API_KEY", os.getenv("NEWSAPI_KEY", ""))
        self.topics = topics or [
            "artificial intelligence",
            "global equities",
            "S&P 500",
            "Nasdaq",
            "federal reserve",
            "European Central Bank",
            "Bank of Japan",
            "China economy",
            "India markets",
            "cryptocurrency",
            "semiconductor",
            "oil market",
            "top companies earnings",
            "electric vehicles",
        ]
        self.seen_titles: set = set()
        self._load_seen_titles()

    def _load_seen_titles(self):
        """Load seen titles to avoid duplicates."""
        seen_file = DATA_DIR / "news_seen.json"
        if seen_file.exists():
            try:
                with open(seen_file) as f:
                    self.seen_titles = set(json.load(f))
            except:
                self.seen_titles = set()

    def _save_seen_titles(self):
        """Save seen titles."""
        seen_file = DATA_DIR / "news_seen.json"
        with open(seen_file, "w") as f:
            json.dump(list(self.seen_titles)[-5000:], f)  # Keep last 5000

    def fetch(self) -> List[Dict]:
        """Fetch news for all topics. Returns list of signals."""
        if not self.api_key:
            logger.warning("[NEWS] No NewsAPI key")
            return []

        signals = []
        for topic in self.topics:
            try:
                articles = self._fetch_news(topic)
                for article in articles:
                    signal = self._classify_article(article, topic)
                    if signal:
                        signals.append(signal)
            except Exception as e:
                logger.error(f"[NEWS] Error fetching {topic}: {e}")

        if signals:
            logger.info(
                f"[NEWS] Generated {len(signals)} signals from {len(self.topics)} topics"
            )

        self._save_seen_titles()
        return signals

    def _fetch_news(self, topic: str) -> List[Dict]:
        """Fetch news for a topic from NewsAPI."""
        url = f"https://newsapi.org/v2/everything?q={topic}&sortBy=publishedAt&language=en&pageSize=10&apiKey={self.api_key}"
        r = httpx.get(url, timeout=10)
        r.raise_for_status()
        data = r.json()
        return data.get("articles", [])

    def _classify_article(self, article: Dict, topic: str) -> Optional[Dict]:
        """Classify a news article for signal vs noise. Returns signal if meaningful."""
        title = article.get("title", "")
        description = article.get("description", "")
        source = article.get("source", {}).get("name", "")
        published_at = article.get("publishedAt", "")
        url = article.get("url", "")

        if not title:
            return None

        # Skip duplicates
        if title in self.seen_titles:
            return None

        self.seen_titles.add(title)

        # Signal detection
        signals = []
        severity = "low"

        # Breaking news detection
        breaking_keywords = ["breaking", "urgent", "just in", "exclusive", "alert"]
        if any(kw in title.lower() for kw in breaking_keywords):
            signals.append("Breaking news")
            severity = "high"

        # Market-moving event detection
        market_keywords = [
            "earnings",
            "revenue",
            "profit",
            "loss",
            "guidance",
            "fed",
            "rate",
            "inflation",
            "gdp",
            "merger",
            "acquisition",
            "buyout",
            "sec",
            "investigation",
            "lawsuit",
            "ceo",
            "resign",
            "fired",
            "appointed",
            "layoff",
            "hire",
            "expansion",
            "regulation",
            "ban",
            "approval",
            "breakthrough",
            "launch",
            "recall",
            "crash",
            "surge",
            "plunge",
            "rally",
        ]

        for kw in market_keywords:
            if kw in title.lower() or kw in (description or "").lower():
                signals.append(f"Market-relevant: {kw}")
                if severity == "low":
                    severity = "medium"

        # Sentiment detection
        positive_words = [
            "surge",
            "rally",
            "beat",
            "record",
            "growth",
            "breakthrough",
            "approval",
            "launch",
        ]
        negative_words = [
            "crash",
            "plunge",
            "miss",
            "loss",
            "scandal",
            "investigation",
            "recall",
            "ban",
        ]

        sentiment = "neutral"
        if any(w in title.lower() for w in positive_words):
            sentiment = "positive"
        if any(w in title.lower() for w in negative_words):
            sentiment = "negative"

        if not signals:
            return None

        signal = {
            "type": "news",
            "title": title,
            "description": description or "",
            "source": source,
            "topic": topic,
            "signals": signals,
            "severity": severity,
            "sentiment": sentiment,
            "url": url,
            "timestamp": published_at or datetime.utcnow().isoformat(),
        }

        logger.info(f"[NEWS] {topic}: {title[:80]}... ({severity})")
        return signal

    def get_recent_news(self, limit: int = 20) -> List[Dict]:
        """Get recent news from disk."""
        news_file = DATA_DIR / "news_archive.json"
        if news_file.exists():
            try:
                with open(news_file) as f:
                    news = json.load(f)
                return news[-limit:]
            except:
                pass
        return []
