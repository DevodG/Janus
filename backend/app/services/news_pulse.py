"""
News Pulse — Background daemon service for Janus.
Fetches news from multiple providers (NewsAPI, GNews, NewsData) with fallback logic.
"""

import os
import json
import time
import logging
import httpx
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from app.config import DATA_DIR as BASE_DATA_DIR, NEWS_API_KEY, GNEWS_API_KEY, NEWDATA_API_KEY

logger = logging.getLogger(__name__)

DATA_DIR = Path(BASE_DATA_DIR) / "daemon"
DATA_DIR.mkdir(parents=True, exist_ok=True)


class NewsPulse:
    def __init__(self, topics: List[str] = None):
        self.providers = {
            "newsapi": NEWS_API_KEY,
            "gnews": GNEWS_API_KEY,
            "newsdata": NEWDATA_API_KEY
        }
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
        
        # Diagnostics
        self.last_error = None
        self.active_provider = "newsapi"
        self.total_fetched_last_cycle = 0
        self.total_signals_last_cycle = 0
        self._current_topic_index = 0

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
        """
        Fetch news with provider fallback and topic cycling.
        Attempts NewsAPI -> GNews -> NewsData.
        """
        self.total_fetched_last_cycle = 0
        self.total_signals_last_cycle = 0
        
        # Select topics for this cycle (rotating queue)
        topics_to_fetch = []
        for _ in range(2):
            topics_to_fetch.append(self.topics[self._current_topic_index])
            self._current_topic_index = (self._current_topic_index + 1) % len(self.topics)

        signals = []
        for topic in topics_to_fetch:
            # Try providers in order
            fetched_articles = []
            provider_chain = ["newsapi", "gnews", "newsdata"]
            
            for provider in provider_chain:
                key = self.providers.get(provider)
                if not key:
                    continue
                
                try:
                    self.active_provider = provider
                    if provider == "newsapi":
                        fetched_articles = self._fetch_newsapi(topic, key)
                    elif provider == "gnews":
                        fetched_articles = self._fetch_gnews(topic, key)
                    elif provider == "newsdata":
                        fetched_articles = self._fetch_newsdata(topic, key)
                    
                    if fetched_articles:
                        self.last_error = None # Clear error if successful
                        break
                except Exception as e:
                    self.last_error = f"{provider} error: {str(e)}"
                    logger.warning(f"[NEWS] Provider {provider} failed for {topic}: {e}")
                    continue # Try next provider

            self.total_fetched_last_cycle += len(fetched_articles)
            for article in fetched_articles:
                signal = self._classify_article(article, topic)
                if signal:
                    signals.append(signal)

        self.total_signals_last_cycle = len(signals)
        if signals:
            logger.info(
                f"[NEWS] Generated {len(signals)} signals via {self.active_provider}"
            )

        self._save_seen_titles()
        return signals

    def _fetch_newsapi(self, topic: str, key: str) -> List[Dict]:
        """Fetch from NewsAPI.org."""
        url = f"https://newsapi.org/v2/everything?q={topic}&sortBy=publishedAt&language=en&pageSize=10&apiKey={key}"
        r = httpx.get(url, timeout=10)
        r.raise_for_status()
        return r.json().get("articles", [])

    def _fetch_gnews(self, topic: str, key: str) -> List[Dict]:
        """Fetch from GNews.io."""
        url = f"https://gnews.io/api/v4/search?q={topic}&lang=en&max=10&apikey={key}"
        r = httpx.get(url, timeout=10)
        r.raise_for_status()
        # Normalize GNews format to match NewsAPI roughly
        articles = r.json().get("articles", [])
        for a in articles:
            a["source"] = {"name": a.get("source", {}).get("name", "GNews")}
        return articles

    def _fetch_newsdata(self, topic: str, key: str) -> List[Dict]:
        """Fetch from NewsData.io."""
        url = f"https://newsdata.io/api/1/news?apikey={key}&q={topic}&language=en"
        r = httpx.get(url, timeout=10)
        r.raise_for_status()
        # Normalize NewsData format
        results = r.json().get("results", [])
        normalized = []
        for res in results:
            normalized.append({
                "title": res.get("title"),
                "description": res.get("description"),
                "url": res.get("link"),
                "source": {"name": res.get("source_id", "NewsData")},
                "publishedAt": res.get("pubDate")
            })
        return normalized

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
            "earnings", "revenue", "profit", "loss", "guidance", "fed", "rate", 
            "inflation", "gdp", "merger", "acquisition", "buyout", "sec", 
            "investigation", "lawsuit", "ceo", "resign", "fired", "appointed", 
            "layoff", "hire", "expansion", "regulation", "ban", "approval", 
            "breakthrough", "launch", "recall", "crash", "surge", "plunge", "rally"
        ]

        for kw in market_keywords:
            if kw in title.lower() or kw in (description or "").lower():
                signals.append(f"Market-relevant: {kw}")
                if severity == "low":
                    severity = "medium"

        # Sentiment detection
        positive_words = ["surge", "rally", "beat", "record", "growth", "breakthrough", "approval", "launch"]
        negative_words = ["crash", "plunge", "miss", "loss", "scandal", "investigation", "recall", "ban"]

        sentiment = "neutral"
        if any(w in title.lower() for w in positive_words):
            sentiment = "positive"
        if any(w in title.lower() for w in negative_words):
            sentiment = "negative"

        if not signals:
            return None

        return {
            "type": "news",
            "title": title,
            "description": description or "",
            "source": f"{source} ({self.active_provider})",
            "topic": topic,
            "signals": signals,
            "severity": severity,
            "sentiment": sentiment,
            "url": url,
            "timestamp": published_at or datetime.utcnow().isoformat(),
        }

    def get_status(self) -> dict:
        """Get status for monitoring."""
        return {
            "topics_count": len(self.topics),
            "current_topic_index": self._current_topic_index,
            "active_provider": self.active_provider,
            "last_error": self.last_error,
            "total_fetched_last_cycle": self.total_fetched_last_cycle,
            "total_signals_last_cycle": self.total_signals_last_cycle,
        }

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
