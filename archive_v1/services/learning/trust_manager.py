"""
Trust and freshness management for sources and knowledge.

Tracks source reliability and content freshness over time.
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


class TrustManager:
    """Manages trust scores and freshness for sources."""
    
    def __init__(self, data_dir: str):
        self.data_dir = Path(data_dir) / "learning"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.trust_file = self.data_dir / "source_trust.json"
        self.freshness_file = self.data_dir / "freshness_scores.json"
        
        # Initialize files if they don't exist
        if not self.trust_file.exists():
            self._save_trust_data({})
        if not self.freshness_file.exists():
            self._save_freshness_data({})
    
    def get_trust_score(self, source: str) -> float:
        """
        Get trust score for a source.
        
        Args:
            source: Source identifier (URL or name)
            
        Returns:
            Trust score (0.0 to 1.0)
        """
        trust_data = self._load_trust_data()
        source_data = trust_data.get(source, {})
        return source_data.get("trust_score", 0.5)  # Default to neutral
    
    def update_trust(self, source: str, verification_outcome: bool, weight: float = 1.0):
        """
        Update trust score based on verification outcome.
        
        Args:
            source: Source identifier
            verification_outcome: True if verified, False if not
            weight: Weight of this update (0.0 to 1.0)
        """
        trust_data = self._load_trust_data()
        
        if source not in trust_data:
            trust_data[source] = {
                "trust_score": 0.5,
                "verification_count": 0,
                "success_count": 0,
                "last_updated": datetime.utcnow().isoformat(),
            }
        
        source_data = trust_data[source]
        
        # Update counts
        source_data["verification_count"] += 1
        if verification_outcome:
            source_data["success_count"] += 1
        
        # Calculate new trust score using exponential moving average
        current_score = source_data["trust_score"]
        outcome_score = 1.0 if verification_outcome else 0.0
        alpha = 0.1 * weight  # Learning rate
        new_score = (1 - alpha) * current_score + alpha * outcome_score
        
        source_data["trust_score"] = new_score
        source_data["last_updated"] = datetime.utcnow().isoformat()
        
        trust_data[source] = source_data
        self._save_trust_data(trust_data)
        
        logger.info(f"Updated trust for {source}: {new_score:.3f} (outcome={verification_outcome})")
    
    def list_trusted_sources(self, min_trust: float = 0.7, min_verifications: int = 3) -> List[Dict[str, Any]]:
        """
        List trusted sources.
        
        Args:
            min_trust: Minimum trust score
            min_verifications: Minimum number of verifications
            
        Returns:
            List of trusted sources
        """
        trust_data = self._load_trust_data()
        
        trusted = []
        for source, data in trust_data.items():
            if data["trust_score"] >= min_trust and data["verification_count"] >= min_verifications:
                trusted.append({
                    "source": source,
                    "trust_score": data["trust_score"],
                    "verification_count": data["verification_count"],
                    "success_rate": data["success_count"] / data["verification_count"],
                })
        
        # Sort by trust score descending
        trusted.sort(key=lambda x: x["trust_score"], reverse=True)
        return trusted
    
    def list_untrusted_sources(self, max_trust: float = 0.3, min_verifications: int = 3) -> List[Dict[str, Any]]:
        """
        List untrusted sources.
        
        Args:
            max_trust: Maximum trust score
            min_verifications: Minimum number of verifications
            
        Returns:
            List of untrusted sources
        """
        trust_data = self._load_trust_data()
        
        untrusted = []
        for source, data in trust_data.items():
            if data["trust_score"] <= max_trust and data["verification_count"] >= min_verifications:
                untrusted.append({
                    "source": source,
                    "trust_score": data["trust_score"],
                    "verification_count": data["verification_count"],
                    "success_rate": data["success_count"] / data["verification_count"],
                })
        
        # Sort by trust score ascending
        untrusted.sort(key=lambda x: x["trust_score"])
        return untrusted
    
    def calculate_freshness(self, item: Dict[str, Any], domain: Optional[str] = None) -> float:
        """
        Calculate freshness score for a knowledge item.
        
        Args:
            item: Knowledge item
            domain: Domain for domain-specific rules
            
        Returns:
            Freshness score (0.0 to 1.0)
        """
        # Get age in days
        saved_at = datetime.fromisoformat(item.get("saved_at", datetime.utcnow().isoformat()))
        age_days = (datetime.utcnow() - saved_at).days
        
        # Domain-specific expiration rules
        if domain == "finance":
            # Financial data expires quickly
            half_life_days = 7  # 50% fresh after 7 days
        else:
            # General knowledge expires slowly
            half_life_days = 30  # 50% fresh after 30 days
        
        # Calculate freshness using exponential decay
        freshness = 2 ** (-age_days / half_life_days)
        
        return max(0.0, min(1.0, freshness))
    
    def update_freshness(self, item_id: str, freshness_score: float):
        """
        Update freshness score for an item.
        
        Args:
            item_id: Item ID
            freshness_score: New freshness score
        """
        freshness_data = self._load_freshness_data()
        
        freshness_data[item_id] = {
            "freshness_score": freshness_score,
            "last_updated": datetime.utcnow().isoformat(),
        }
        
        self._save_freshness_data(freshness_data)
    
    def get_stale_items(self, items: List[Dict[str, Any]], threshold: float = 0.3) -> List[Dict[str, Any]]:
        """
        Get stale items that need refreshing.
        
        Args:
            items: List of knowledge items
            threshold: Freshness threshold
            
        Returns:
            List of stale items
        """
        stale = []
        
        for item in items:
            freshness = self.calculate_freshness(item)
            if freshness < threshold:
                stale.append({
                    "item_id": item.get("id"),
                    "title": item.get("title"),
                    "freshness": freshness,
                    "age_days": (datetime.utcnow() - datetime.fromisoformat(item.get("saved_at", datetime.utcnow().isoformat()))).days,
                })
        
        # Sort by freshness ascending (stalest first)
        stale.sort(key=lambda x: x["freshness"])
        return stale
    
    def recommend_refresh(self, stale_items: List[Dict[str, Any]], max_recommendations: int = 10) -> List[Dict[str, Any]]:
        """
        Recommend items to refresh.
        
        Args:
            stale_items: List of stale items
            max_recommendations: Maximum number of recommendations
            
        Returns:
            List of recommended items to refresh
        """
        # Prioritize by staleness and importance
        recommendations = stale_items[:max_recommendations]
        
        return recommendations
    
    def _load_trust_data(self) -> Dict[str, Any]:
        """Load trust data from disk."""
        with open(self.trust_file, 'r') as f:
            return json.load(f)
    
    def _save_trust_data(self, data: Dict[str, Any]):
        """Save trust data to disk."""
        with open(self.trust_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def _load_freshness_data(self) -> Dict[str, Any]:
        """Load freshness data from disk."""
        with open(self.freshness_file, 'r') as f:
            return json.load(f)
    
    def _save_freshness_data(self, data: Dict[str, Any]):
        """Save freshness data to disk."""
        with open(self.freshness_file, 'w') as f:
            json.dump(data, f, indent=2)
