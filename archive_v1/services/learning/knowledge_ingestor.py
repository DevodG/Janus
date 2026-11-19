"""
Knowledge ingestion from external sources.

Ingests knowledge from web search, URLs, and news sources,
compressing content to 2-4KB summaries for efficient storage.
"""

import logging
from typing import Dict, Any, Optional
import httpx
from datetime import datetime

logger = logging.getLogger(__name__)


class KnowledgeIngestor:
    """Ingests knowledge from external sources."""
    
    def __init__(self, tavily_key: Optional[str], newsapi_key: Optional[str], model_fn):
        self.tavily_key = tavily_key
        self.newsapi_key = newsapi_key
        self.model_fn = model_fn
        self.jina_reader_base = "https://r.jina.ai/"
    
    async def ingest_from_search(self, query: str, max_results: int = 5) -> list[Dict[str, Any]]:
        """
        Ingest knowledge from web search using Tavily API.
        
        Args:
            query: Search query
            max_results: Maximum number of results to ingest
            
        Returns:
            List of knowledge items with compressed content
        """
        if not self.tavily_key:
            logger.warning("Tavily API key not configured")
            return []
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "https://api.tavily.com/search",
                    json={
                        "api_key": self.tavily_key,
                        "query": query,
                        "max_results": max_results,
                    }
                )
                response.raise_for_status()
                data = response.json()
            
            items = []
            for result in data.get("results", []):
                summary = await self.compress_content(result.get("content", ""))
                items.append({
                    "source": "tavily_search",
                    "query": query,
                    "url": result.get("url"),
                    "title": result.get("title"),
                    "summary": summary,
                    "ingested_at": datetime.utcnow().isoformat(),
                })
            
            logger.info(f"Ingested {len(items)} items from Tavily search: {query}")
            return items
        
        except Exception as e:
            logger.error(f"Failed to ingest from Tavily search: {e}")
            return []
    
    async def ingest_from_url(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Ingest knowledge from a specific URL using Jina Reader.
        
        Args:
            url: URL to ingest
            
        Returns:
            Knowledge item with compressed content, or None if failed
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(f"{self.jina_reader_base}{url}")
                response.raise_for_status()
                content = response.text
            
            summary = await self.compress_content(content)
            
            item = {
                "source": "jina_reader",
                "url": url,
                "summary": summary,
                "ingested_at": datetime.utcnow().isoformat(),
            }
            
            logger.info(f"Ingested content from URL: {url}")
            return item
        
        except Exception as e:
            logger.error(f"Failed to ingest from URL {url}: {e}")
            return None
    
    async def ingest_from_news(self, query: str, max_results: int = 10) -> list[Dict[str, Any]]:
        """
        Ingest knowledge from news sources using NewsAPI.
        
        Args:
            query: News search query
            max_results: Maximum number of articles to ingest
            
        Returns:
            List of knowledge items with compressed content
        """
        if not self.newsapi_key:
            logger.warning("NewsAPI key not configured")
            return []
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    "https://newsapi.org/v2/everything",
                    params={
                        "apiKey": self.newsapi_key,
                        "q": query,
                        "pageSize": max_results,
                        "sortBy": "publishedAt",
                    }
                )
                response.raise_for_status()
                data = response.json()
            
            items = []
            for article in data.get("articles", []):
                content = f"{article.get('title', '')} {article.get('description', '')} {article.get('content', '')}"
                summary = await self.compress_content(content)
                items.append({
                    "source": "newsapi",
                    "query": query,
                    "url": article.get("url"),
                    "title": article.get("title"),
                    "published_at": article.get("publishedAt"),
                    "summary": summary,
                    "ingested_at": datetime.utcnow().isoformat(),
                })
            
            logger.info(f"Ingested {len(items)} articles from NewsAPI: {query}")
            return items
        
        except Exception as e:
            logger.error(f"Failed to ingest from NewsAPI: {e}")
            return []
    
    async def compress_content(self, content: str) -> str:
        """
        Compress content to 2-4KB summary using LLM.
        
        Args:
            content: Raw content to compress
            
        Returns:
            Compressed summary (2-4KB)
        """
        if not content:
            return ""
        
        # If already small enough, return as-is
        if len(content.encode('utf-8')) <= 4096:
            return content
        
        prompt = f"""Summarize the following content into a concise summary of 500-1000 words.
Focus on key facts, insights, and actionable information.

Content:
{content[:10000]}

Summary:"""
        
        try:
            summary = await self.model_fn(prompt, max_tokens=1500)
            
            # Ensure summary is within 2-4KB range
            summary_bytes = summary.encode('utf-8')
            if len(summary_bytes) > 4096:
                # Truncate if too long
                summary = summary_bytes[:4096].decode('utf-8', errors='ignore')
            
            return summary
        
        except Exception as e:
            logger.error(f"Failed to compress content: {e}")
            # Return truncated content as fallback
            return content[:4096]
