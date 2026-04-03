"""
Sentinel Capability Tracker - System Capability Metrics

Computes and tracks a composite capability score across 6 dimensions.
Reads existing data directories. Never calls any LLM. Never writes to
any existing data directory - only writes to data/sentinel/.
"""

import json
import logging
import os
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

# IMPORTANT COMMENT (must appear in source code):
# agi_progression_index is a VANITY METRIC for developer motivation.
# It is a weighted composite of system health indicators:
# error rate, confidence scores, trust quality, skill growth, etc.
# It does NOT measure general intelligence, emergent reasoning, or AGI.
# The name is aspirational and intentionally optimistic, not scientific.


class CapabilitySnapshot:
    """Represents a snapshot of system capabilities."""
    
    def __init__(
        self,
        scores: Dict[str, float],
        agi_progression_index: float,
        delta_from_last: Dict[str, float]
    ):
        self.snapshot_id = str(uuid.uuid4())
        self.timestamp = datetime.utcnow().isoformat()
        self.scores = scores
        self.agi_progression_index = agi_progression_index
        self.delta_from_last = delta_from_last
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "timestamp": self.timestamp,
            "scores": self.scores,
            "agi_progression_index": self.agi_progression_index,
            "delta_from_last": self.delta_from_last,
        }


class CapabilityTracker:
    """Tracks system capability metrics over time."""
    
    def __init__(self):
        self.data_dir = Path("backend/app/data")
        self.sentinel_dir = self.data_dir / "sentinel"
        self.sentinel_dir.mkdir(parents=True, exist_ok=True)
    
    def snapshot(self) -> CapabilitySnapshot:
        """
        Compute current capability snapshot.
        
        Returns:
            CapabilitySnapshot with all dimensions and AGI index
        """
        # Compute all 6 dimensions
        scores = {
            "reasoning_depth": self._compute_reasoning_depth(),
            "source_trust_avg": self._compute_source_trust_avg(),
            "skill_coverage": self._compute_skill_coverage(),
            "prompt_win_rate_avg": self._compute_prompt_win_rate_avg(),
            "stability": self._compute_stability(),
            "self_correction_rate": self._compute_self_correction_rate(),
        }
        
        # Compute AGI progression index
        agi_index = self._compute_agi_index(scores)
        
        # Get delta from last snapshot
        delta_from_last = self._compute_delta(scores, agi_index)
        
        # Create snapshot
        snapshot = CapabilitySnapshot(
            scores=scores,
            agi_progression_index=agi_index,
            delta_from_last=delta_from_last
        )
        
        # Save to history
        self._save_snapshot(snapshot)
        
        return snapshot
    
    def trend(self, days: int = 7) -> List[Dict[str, Any]]:
        """
        Get capability trend over specified days.
        
        Args:
            days: Number of days to look back
            
        Returns:
            List of CapabilitySnapshot dicts
        """
        try:
            history_file = self.sentinel_dir / "capability_history.json"
            
            if not history_file.exists():
                return []
            
            with open(history_file, 'r') as f:
                history = json.load(f)
            
            # Filter to last N days
            cutoff = datetime.utcnow() - timedelta(days=days)
            
            filtered = []
            for entry in history:
                try:
                    entry_time = datetime.fromisoformat(entry["timestamp"])
                    if entry_time >= cutoff:
                        filtered.append(entry)
                except:
                    continue
            
            return filtered
        
        except Exception as e:
            logger.error(f"Failed to get capability trend: {e}")
            return []
    
    def _compute_reasoning_depth(self) -> float:
        """Compute reasoning depth from case confidence scores."""
        try:
            memory_dir = self.data_dir / "memory"
            
            if not memory_dir.exists():
                return 0.5
            
            case_files = sorted(memory_dir.glob("*.json"), key=os.path.getmtime, reverse=True)[:30]
            
            if not case_files:
                return 0.5
            
            all_confidences = []
            
            for case_file in case_files:
                try:
                    with open(case_file, 'r') as f:
                        case_data = json.load(f)
                    
                    outputs = case_data.get("outputs", [])
                    
                    for output in outputs:
                        if isinstance(output, dict):
                            confidence = output.get("confidence")
                            if confidence is not None:
                                all_confidences.append(confidence)
                except:
                    continue
            
            if not all_confidences:
                return 0.5
            
            return sum(all_confidences) / len(all_confidences)
        
        except Exception as e:
            logger.warning(f"Failed to compute reasoning depth: {e}")
            return 0.5
    
    def _compute_source_trust_avg(self) -> float:
        """Compute average source trust score."""
        try:
            config_file = self.sentinel_dir / "sentinel_config.json"
            
            if not config_file.exists():
                return 0.5
            
            with open(config_file, 'r') as f:
                config = json.load(f)
            
            trust_scores = config.get("source_trust_scores", {})
            
            if not trust_scores:
                return 0.5
            
            values = [v for v in trust_scores.values() if isinstance(v, (int, float))]
            
            if not values:
                return 0.5
            
            return sum(values) / len(values)
        
        except Exception as e:
            logger.warning(f"Failed to compute source trust avg: {e}")
            return 0.5
    
    def _compute_skill_coverage(self) -> float:
        """Compute skill coverage metric."""
        try:
            skills_dir = self.data_dir / "skills"
            
            if not skills_dir.exists():
                return 0.0
            
            skill_count = len(list(skills_dir.glob("*.json")))
            
            # Normalize to 0-1 scale (20 skills = 1.0)
            return min(skill_count / 20.0, 1.0)
        
        except Exception as e:
            logger.warning(f"Failed to compute skill coverage: {e}")
            return 0.0
    
    def _compute_prompt_win_rate_avg(self) -> float:
        """Compute average prompt win rate."""
        try:
            prompt_versions_dir = self.data_dir / "prompt_versions"
            
            if not prompt_versions_dir.exists():
                return 0.5
            
            win_rates = []
            
            for version_file in prompt_versions_dir.glob("*.json"):
                try:
                    with open(version_file, 'r') as f:
                        version_data = json.load(f)
                    
                    win_rate = version_data.get("win_rate")
                    if win_rate is not None:
                        win_rates.append(win_rate)
                except:
                    continue
            
            if not win_rates:
                return 0.5
            
            return sum(win_rates) / len(win_rates)
        
        except Exception as e:
            logger.warning(f"Failed to compute prompt win rate avg: {e}")
            return 0.5
    
    def _compute_stability(self) -> float:
        """Compute stability (1.0 - error_rate)."""
        try:
            memory_dir = self.data_dir / "memory"
            
            if not memory_dir.exists():
                return 1.0
            
            # Get cases from last 7 days
            cutoff = datetime.utcnow() - timedelta(days=7)
            
            total_count = 0
            failed_count = 0
            
            for case_file in memory_dir.glob("*.json"):
                try:
                    # Check file modification time
                    mtime = datetime.fromtimestamp(case_file.stat().st_mtime)
                    if mtime < cutoff:
                        continue
                    
                    with open(case_file, 'r') as f:
                        case_data = json.load(f)
                    
                    total_count += 1
                    
                    # Check if case failed
                    final_answer = case_data.get("final_answer", "")
                    outputs = case_data.get("outputs", [])
                    
                    if not final_answer or not outputs:
                        failed_count += 1
                except:
                    continue
            
            if total_count == 0:
                return 1.0
            
            error_rate = failed_count / total_count
            return 1.0 - error_rate
        
        except Exception as e:
            logger.warning(f"Failed to compute stability: {e}")
            return 1.0
    
    def _compute_self_correction_rate(self) -> float:
        """Compute self-correction rate."""
        try:
            # Get patches from last 7 days
            patch_history_file = self.sentinel_dir / "patch_history.json"
            alert_history_file = self.sentinel_dir / "alert_history.json"
            
            cutoff = datetime.utcnow() - timedelta(days=7)
            
            patch_count = 0
            if patch_history_file.exists():
                with open(patch_history_file, 'r') as f:
                    patches = json.load(f)
                
                for patch in patches:
                    try:
                        patch_time = datetime.fromisoformat(patch["timestamp"])
                        if patch_time >= cutoff:
                            patch_count += 1
                    except:
                        continue
            
            alert_count = 0
            if alert_history_file.exists():
                with open(alert_history_file, 'r') as f:
                    alerts = json.load(f)
                
                for alert in alerts:
                    try:
                        alert_time = datetime.fromisoformat(alert["timestamp"])
                        if alert_time >= cutoff:
                            alert_count += 1
                    except:
                        continue
            
            if alert_count == 0:
                return 0.0
            
            return min(patch_count / alert_count, 1.0)
        
        except Exception as e:
            logger.warning(f"Failed to compute self-correction rate: {e}")
            return 0.0
    
    def _compute_agi_index(self, scores: Dict[str, float]) -> float:
        """
        Compute AGI progression index from dimension scores.
        
        Formula:
          index = (
            (reasoning_depth * 0.25) +
            (source_trust_avg * 0.15) +
            (skill_coverage * 0.20) +
            (prompt_win_rate_avg * 0.20) +
            (stability * 0.10) +
            (self_correction_rate * 0.10)
          )
        """
        index = (
            (scores.get("reasoning_depth", 0.5) * 0.25) +
            (scores.get("source_trust_avg", 0.5) * 0.15) +
            (scores.get("skill_coverage", 0.0) * 0.20) +
            (scores.get("prompt_win_rate_avg", 0.5) * 0.20) +
            (scores.get("stability", 1.0) * 0.10) +
            (scores.get("self_correction_rate", 0.0) * 0.10)
        )
        
        # Clamp to [0.0, 1.0]
        return max(0.0, min(1.0, index))
    
    def _compute_delta(self, scores: Dict[str, float], agi_index: float) -> Dict[str, float]:
        """Compute delta from last snapshot."""
        try:
            history_file = self.sentinel_dir / "capability_history.json"
            
            if not history_file.exists():
                return {k: 0.0 for k in scores.keys()}
            
            with open(history_file, 'r') as f:
                history = json.load(f)
            
            if not history:
                return {k: 0.0 for k in scores.keys()}
            
            last_snapshot = history[-1]
            last_scores = last_snapshot.get("scores", {})
            
            delta = {}
            for key, value in scores.items():
                last_value = last_scores.get(key, value)
                delta[key] = value - last_value
            
            delta["agi_progression_index"] = agi_index - last_snapshot.get("agi_progression_index", agi_index)
            
            return delta
        
        except Exception as e:
            logger.warning(f"Failed to compute delta: {e}")
            return {k: 0.0 for k in scores.keys()}
    
    def _save_snapshot(self, snapshot: CapabilitySnapshot):
        """Save snapshot to history."""
        try:
            history_file = self.sentinel_dir / "capability_history.json"
            
            # Load existing history
            if history_file.exists():
                with open(history_file, 'r') as f:
                    history = json.load(f)
            else:
                history = []
            
            # Append new snapshot
            history.append(snapshot.to_dict())
            
            # Keep only last 500 entries
            if len(history) > 500:
                history = history[-500:]
            
            # Save back
            with open(history_file, 'w') as f:
                json.dump(history, f, indent=2)
        
        except Exception as e:
            logger.error(f"Failed to save capability snapshot: {e}")
