"""
Sentinel Engine - Core Orchestration

Coordinates watcher, diagnostician, patcher, and capability tracker
to perform complete sentinel cycles.
"""

import json
import logging
import os
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional

from app.services.sentinel.watcher import SentinelWatcher
from app.services.sentinel.diagnostician import SentinelDiagnostician
from app.services.sentinel.patcher import SentinelPatcher
from app.services.sentinel.capability_tracker import CapabilityTracker

logger = logging.getLogger(__name__)

# Module-level state
SENTINEL_RUNNING: bool = False
_last_cycle_at: Optional[str] = None
_last_cycle_report: Optional[dict] = None


class SentinelCycleReport:
    """Represents the result of a sentinel cycle."""
    
    def __init__(
        self,
        cycle_id: str,
        started_at: str,
        completed_at: str,
        alerts_found: int,
        diagnoses_made: int,
        patches_applied: int,
        patches_pending_review: int,
        capability_snapshot
    ):
        self.cycle_id = cycle_id
        self.started_at = started_at
        self.completed_at = completed_at
        self.alerts_found = alerts_found
        self.diagnoses_made = diagnoses_made
        self.patches_applied = patches_applied
        self.patches_pending_review = patches_pending_review
        self.capability_snapshot = capability_snapshot
    
    def dict(self) -> Dict[str, Any]:
        return {
            "cycle_id": self.cycle_id,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "alerts_found": self.alerts_found,
            "diagnoses_made": self.diagnoses_made,
            "patches_applied": self.patches_applied,
            "patches_pending_review": self.patches_pending_review,
            "capability_snapshot": self.capability_snapshot.to_dict() if hasattr(self.capability_snapshot, 'to_dict') else self.capability_snapshot,
        }


from app.config import SENTINEL_DIR


class SentinelEngine:
    """Core sentinel orchestration engine."""
    
    def __init__(self):
        self.watcher = SentinelWatcher()
        self.diagnostician = SentinelDiagnostician()
        self.patcher = SentinelPatcher()
        self.tracker = CapabilityTracker()
        self.max_diagnoses = int(os.getenv("SENTINEL_MAX_DIAGNOSES_PER_CYCLE", "5"))
        self.logger = logging.getLogger("sentinel.engine")
        self.data_dir = SENTINEL_DIR
        self.data_dir.mkdir(parents=True, exist_ok=True)
    
    def run_cycle(self) -> SentinelCycleReport:
        """
        Run a complete sentinel cycle.
        
        Returns:
            SentinelCycleReport with cycle results
        """
        global SENTINEL_RUNNING, _last_cycle_at, _last_cycle_report
        
        # Check if already running
        if SENTINEL_RUNNING:
            self.logger.warning("Sentinel cycle already running, skipping")
            if _last_cycle_report:
                return SentinelCycleReport(**_last_cycle_report)
            else:
                # Return stub report
                return SentinelCycleReport(
                    cycle_id="stub",
                    started_at=datetime.utcnow().isoformat(),
                    completed_at=datetime.utcnow().isoformat(),
                    alerts_found=0,
                    diagnoses_made=0,
                    patches_applied=0,
                    patches_pending_review=0,
                    capability_snapshot=self.tracker.snapshot()
                )
        
        SENTINEL_RUNNING = True
        cycle_id = str(uuid.uuid4())
        started_at = datetime.utcnow().isoformat()
        patches_applied = 0
        patches_pending = 0
        diagnoses_made = 0
        
        try:
            # Step 1: Scan for alerts
            self.logger.info(f"Starting sentinel cycle {cycle_id}")
            all_alerts = self.watcher.scan()
            self.logger.info(f"Sentinel scan found {len(all_alerts)} alerts")
            
            # Step 2: Filter to high/critical only, respect max_diagnoses limit
            priority_alerts = [a for a in all_alerts if a.severity in ("high", "critical")]
            priority_alerts = sorted(
                priority_alerts,
                key=lambda a: (a.severity == "critical", a.timestamp),
                reverse=True
            )
            priority_alerts = priority_alerts[:self.max_diagnoses]
            
            self.logger.info(f"Processing {len(priority_alerts)} priority alerts")
            
            # Step 3: Diagnose each alert
            diagnoses = []
            for alert in priority_alerts:
                try:
                    self.logger.info(f"Diagnosing alert {alert.alert_id}")
                    diagnosis = self.diagnostician.diagnose(alert)
                    diagnoses.append(diagnosis)
                    diagnoses_made += 1
                except Exception as e:
                    self.logger.warning(f"Diagnosis failed for alert {alert.alert_id}: {e}")
                    continue
            
            # Step 4: Apply patches
            for diagnosis in diagnoses:
                try:
                    self.logger.info(f"Applying patch for diagnosis {diagnosis.diagnosis_id}")
                    result = self.patcher.apply(diagnosis)
                    
                    if result.applied:
                        patches_applied += 1
                        self.logger.info(f"Patch applied: {result.patch_id}")
                    elif result.requires_human_review:
                        patches_pending += 1
                        self.logger.info(f"Patch queued for review: {result.patch_id}")
                except Exception as e:
                    self.logger.error(f"Patch application failed: {e}")
                    continue
            
            # Step 5: Capability snapshot
            self.logger.info("Computing capability snapshot")
            capability_snapshot = self.tracker.snapshot()
            
            # Step 6: Build report
            completed_at = datetime.utcnow().isoformat()
            report = SentinelCycleReport(
                cycle_id=cycle_id,
                started_at=started_at,
                completed_at=completed_at,
                alerts_found=len(all_alerts),
                diagnoses_made=diagnoses_made,
                patches_applied=patches_applied,
                patches_pending_review=patches_pending,
                capability_snapshot=capability_snapshot
            )
            
            # Step 7: Save to cycle history
            self._save_cycle_history(report)
            
            # Update module state
            _last_cycle_at = completed_at
            _last_cycle_report = report.dict()
            
            self.logger.info(f"Sentinel cycle {cycle_id} complete: {patches_applied} patches applied, {patches_pending} pending review")
            
            return report
        
        finally:
            SENTINEL_RUNNING = False
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get current sentinel status.
        
        Returns:
            Status dict with health and metrics
        """
        try:
            # Count recent alerts
            alerts_this_week = self._count_recent_items("alert_history.json", days=7)
            
            # Count recent patches
            patches_this_week = self._count_recent_applied_patches(days=7)
            
            # Count pending patches
            pending_count = self._count_pending_patches()
            
            # Get latest AGI index
            agi_index = self._get_latest_agi_index()
            
            return {
                "sentinel_enabled": os.getenv("SENTINEL_ENABLED", "true").lower() == "true",
                "current_health": self.watcher.is_healthy(),
                "last_cycle_at": _last_cycle_at,
                "sentinel_running": SENTINEL_RUNNING,
                "agi_progression_index": agi_index,
                "alerts_this_week": alerts_this_week,
                "patches_applied_this_week": patches_this_week,
                "pending_review_count": pending_count,
            }
        
        except Exception as e:
            self.logger.error(f"Failed to get status: {e}")
            return {
                "sentinel_enabled": os.getenv("SENTINEL_ENABLED", "true").lower() == "true",
                "current_health": True,
                "last_cycle_at": _last_cycle_at,
                "sentinel_running": SENTINEL_RUNNING,
                "agi_progression_index": 0.0,
                "alerts_this_week": 0,
                "patches_applied_this_week": 0,
                "pending_review_count": 0,
            }
    
    def _save_cycle_history(self, report: SentinelCycleReport):
        """Save cycle report to history."""
        try:
            history_file = self.data_dir / "cycle_history.json"
            
            # Load existing history
            if history_file.exists():
                with open(history_file, 'r') as f:
                    history = json.load(f)
            else:
                history = []
            
            # Append new report
            history.append(report.dict())
            
            # Keep only last 20 entries
            if len(history) > 20:
                history = history[-20:]
            
            # Save back
            with open(history_file, 'w') as f:
                json.dump(history, f, indent=2)
        
        except Exception as e:
            self.logger.error(f"Failed to save cycle history: {e}")
    
    def _count_recent_items(self, filename: str, days: int) -> int:
        """Count items in a history file from last N days."""
        try:
            file_path = self.data_dir / filename
            
            if not file_path.exists():
                return 0
            
            with open(file_path, 'r') as f:
                items = json.load(f)
            
            cutoff = datetime.utcnow() - timedelta(days=days)
            count = 0
            
            for item in items:
                try:
                    item_time = datetime.fromisoformat(item["timestamp"])
                    if item_time >= cutoff:
                        count += 1
                except:
                    continue
            
            return count
        
        except Exception as e:
            self.logger.warning(f"Failed to count recent items in {filename}: {e}")
            return 0
    
    def _count_recent_applied_patches(self, days: int) -> int:
        """Count applied patches from last N days."""
        try:
            file_path = self.data_dir / "patch_history.json"
            
            if not file_path.exists():
                return 0
            
            with open(file_path, 'r') as f:
                patches = json.load(f)
            
            cutoff = datetime.utcnow() - timedelta(days=days)
            count = 0
            
            for patch in patches:
                try:
                    if not patch.get("applied", False):
                        continue
                    
                    patch_time = datetime.fromisoformat(patch["timestamp"])
                    if patch_time >= cutoff:
                        count += 1
                except:
                    continue
            
            return count
        
        except Exception as e:
            self.logger.warning(f"Failed to count recent applied patches: {e}")
            return 0
    
    def _count_pending_patches(self) -> int:
        """Count pending patches."""
        try:
            pending_dir = self.data_dir / "pending_patches"
            
            if not pending_dir.exists():
                return 0
            
            return len(list(pending_dir.glob("*.patch.json")))
        
        except Exception as e:
            self.logger.warning(f"Failed to count pending patches: {e}")
            return 0
    
    def _get_latest_agi_index(self) -> float:
        """Get latest AGI progression index."""
        try:
            history_file = self.data_dir / "capability_history.json"
            
            if not history_file.exists():
                return 0.0
            
            with open(history_file, 'r') as f:
                history = json.load(f)
            
            if not history:
                return 0.0
            
            return history[-1].get("agi_progression_index", 0.0)
        
        except Exception as e:
            self.logger.warning(f"Failed to get latest AGI index: {e}")
            return 0.0
