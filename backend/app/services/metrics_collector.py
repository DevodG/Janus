"""
Track model impact on query quality.
"""

import json
import os
import logging
from datetime import datetime
from typing import Dict, Any, List
from pathlib import Path

logger = logging.getLogger(__name__)

class MetricsCollector:
    """Tracks model usage and quality metrics."""
    
    def __init__(self, metrics_dir: Optional[str] = None):
        if metrics_dir is None:
            from app.config import DATA_DIR
            self.metrics_dir = Path(DATA_DIR) / "metrics"
        else:
            self.metrics_dir = Path(metrics_dir)
            
        self.metrics_dir.mkdir(parents=True, exist_ok=True)
        self.metrics_file = self.metrics_dir / "model_impact.jsonl"
    
    def log_query(
        self,
        domain: str,
        model_enhanced: bool,
        insight_count: int,
        latency_ms: float,
        query: str
    ) -> None:
        """Log a single query event."""
        metric = {
            "timestamp": datetime.now().isoformat(),
            "domain": domain,
            "model_enhanced": model_enhanced,
            "insight_count": insight_count,
            "latency_ms": latency_ms,
            "query": query[:100]  # Truncate for privacy/size
        }
        
        try:
            with open(self.metrics_file, 'a') as f:
                f.write(json.dumps(metric) + '\n')
        except Exception as e:
            logger.error(f"Failed to log metrics: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """Aggregate stats from the log file."""
        if not self.metrics_file.exists():
            return {"total_queries": 0, "status": "no data"}
            
        metrics = []
        try:
            with open(self.metrics_file) as f:
                for line in f:
                    if line.strip():
                        metrics.append(json.loads(line))
        except Exception as e:
            logger.error(f"Error reading metrics: {e}")
            return {"error": str(e)}

        if not metrics:
            return {"total_queries": 0}

        enhanced = [m for m in metrics if m.get("model_enhanced")]
        
        return {
            "total_queries": len(metrics),
            "enhanced_queries": len(enhanced),
            "enhancement_rate": f"{(len(enhanced) / len(metrics) * 100):.1f}%",
            "avg_insights": sum(m.get("insight_count", 0) for m in enhanced) / len(enhanced) if enhanced else 0,
            "avg_latency_ms": sum(m.get("latency_ms", 0) for m in metrics) / len(metrics),
            "domains": self._count_by(metrics, "domain")
        }

    def _count_by(self, metrics: List[Dict], key: str) -> Dict[str, int]:
        counts = {}
        for m in metrics:
            val = m.get(key, "unknown")
            counts[val] = counts.get(val, 0) + 1
        return counts
