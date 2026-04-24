"""
Knowledge storage with LRU eviction and expiration management.

Stores knowledge items as JSON files with 200MB storage limit.
Implements LRU eviction when limit is reached.
"""

import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, List
import uuid

logger = logging.getLogger(__name__)


class KnowledgeStore:
    """Stores and retrieves knowledge items with storage limits."""
    
    def __init__(self, data_dir: str, max_size_mb: int = 200):
        self.data_dir = Path(data_dir) / "knowledge"
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.data_dir.mkdir(parents=True, exist_ok=True)
    
    def save_knowledge(self, item: Dict[str, Any]) -> str:
        """
        Save a knowledge item to storage.
        
        Args:
            item: Knowledge item to save
            
        Returns:
            Item ID
        """
        # Generate ID if not present
        if "id" not in item:
            item["id"] = str(uuid.uuid4())
        
        # Add metadata
        item["saved_at"] = datetime.utcnow().isoformat()
        item["last_accessed"] = datetime.utcnow().isoformat()
        
        # Check storage limit and evict if needed
        self._enforce_storage_limit()
        
        # Save to file
        file_path = self.data_dir / f"{item['id']}.json"
        with open(file_path, 'w') as f:
            json.dump(item, f, indent=2)
        
        logger.info(f"Saved knowledge item: {item['id']}")
        return item["id"]
    
    def get_knowledge(self, item_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a knowledge item by ID.
        
        Args:
            item_id: Item ID
            
        Returns:
            Knowledge item or None if not found
        """
        file_path = self.data_dir / f"{item_id}.json"
        if not file_path.exists():
            return None
        
        with open(file_path, 'r') as f:
            item = json.load(f)
        
        # Update last accessed time
        item["last_accessed"] = datetime.utcnow().isoformat()
        with open(file_path, 'w') as f:
            json.dump(item, f, indent=2)
        
        return item
    
    def search_knowledge(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search knowledge items by query.
        
        Args:
            query: Search query
            limit: Maximum number of results
            
        Returns:
            List of matching knowledge items
        """
        results = []
        query_lower = query.lower()
        
        for file_path in self.data_dir.glob("*.json"):
            try:
                with open(file_path, 'r') as f:
                    item = json.load(f)
                
                # Simple text search in title and summary
                title = item.get("title", "").lower()
                summary = item.get("summary", "").lower()
                
                if query_lower in title or query_lower in summary:
                    results.append(item)
                
                if len(results) >= limit:
                    break
            
            except Exception as e:
                logger.error(f"Failed to read knowledge item {file_path}: {e}")
        
        # Sort by relevance (title match first, then by recency)
        results.sort(key=lambda x: (
            query_lower not in x.get("title", "").lower(),
            x.get("saved_at", "")
        ), reverse=True)
        
        return results[:limit]
    
    def list_all(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        List all knowledge items.
        
        Args:
            limit: Maximum number of items to return
            
        Returns:
            List of knowledge items
        """
        items = []
        
        for file_path in self.data_dir.glob("*.json"):
            try:
                with open(file_path, 'r') as f:
                    item = json.load(f)
                items.append(item)
            except Exception as e:
                logger.error(f"Failed to read knowledge item {file_path}: {e}")
        
        # Sort by saved_at descending
        items.sort(key=lambda x: x.get("saved_at", ""), reverse=True)
        
        if limit:
            return items[:limit]
        return items
    
    def delete_expired_knowledge(self, expiration_days: int = 30) -> int:
        """
        Delete expired knowledge items.
        
        Args:
            expiration_days: Number of days before expiration
            
        Returns:
            Number of items deleted
        """
        cutoff = datetime.utcnow() - timedelta(days=expiration_days)
        deleted_count = 0
        
        for file_path in self.data_dir.glob("*.json"):
            try:
                with open(file_path, 'r') as f:
                    item = json.load(f)
                
                saved_at = datetime.fromisoformat(item.get("saved_at", ""))
                if saved_at < cutoff:
                    file_path.unlink()
                    deleted_count += 1
                    logger.info(f"Deleted expired knowledge item: {item.get('id')}")
            
            except Exception as e:
                logger.error(f"Failed to check expiration for {file_path}: {e}")
        
        logger.info(f"Deleted {deleted_count} expired knowledge items")
        return deleted_count
    
    def _enforce_storage_limit(self):
        """Enforce storage limit using LRU eviction."""
        current_size = self._get_storage_size()
        
        if current_size <= self.max_size_bytes:
            return
        
        logger.warning(f"Storage limit exceeded: {current_size / 1024 / 1024:.2f}MB / {self.max_size_bytes / 1024 / 1024:.2f}MB")
        
        # Get all items sorted by last_accessed (LRU)
        items = []
        for file_path in self.data_dir.glob("*.json"):
            try:
                with open(file_path, 'r') as f:
                    item = json.load(f)
                items.append((file_path, item.get("last_accessed", "")))
            except Exception as e:
                logger.error(f"Failed to read {file_path}: {e}")
        
        items.sort(key=lambda x: x[1])  # Sort by last_accessed ascending
        
        # Delete oldest items until under limit
        for file_path, _ in items:
            if current_size <= self.max_size_bytes:
                break
            
            file_size = file_path.stat().st_size
            file_path.unlink()
            current_size -= file_size
            logger.info(f"Evicted knowledge item (LRU): {file_path.name}")
    
    def _get_storage_size(self) -> int:
        """Get total storage size in bytes."""
        total_size = 0
        for file_path in self.data_dir.glob("*.json"):
            total_size += file_path.stat().st_size
        return total_size
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage statistics."""
        total_size = self._get_storage_size()
        item_count = len(list(self.data_dir.glob("*.json")))
        
        return {
            "total_size_mb": total_size / 1024 / 1024,
            "max_size_mb": self.max_size_bytes / 1024 / 1024,
            "usage_percent": (total_size / self.max_size_bytes) * 100 if self.max_size_bytes > 0 else 0,
            "item_count": item_count,
        }
