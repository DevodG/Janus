"""
Sentinel Watcher - System Health Scanner

Scans existing data directories for signs of system degradation.
Reads only - never writes. Never calls any LLM.
"""

import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional
import uuid

logger = logging.getLogger(__name__)


class SentinelAlert:
    """Represents a system health alert."""
    
    def __init__(
        self,
        layer: int,
        component: str,
        issue_type: str,
        severity: str,
        raw_evidence: str
    ):
        self.alert_id = str(uuid.uuid4())
        self.layer = layer
        self.component = component
        self.issue_type = issue_type
        self.severity = severity
        self.raw_evidence = raw_evidence
        self.timestamp = datetime.utcnow().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "alert_id": self.alert_id,
            "layer": self.layer,
            "component": self.component,
            "issue_type": self.issue_type,
            "severity": self.severity,
            "raw_evidence": self.raw_evidence,
            "timestamp": self.timestamp,
        }


from app.config import DATA_DIR


class SentinelWatcher:
    """Scans system for health issues."""
    
    def __init__(self):
        self.data_dir = DATA_DIR
        self._last_scan_time: Optional[datetime] = None
        self._last_scan_result: Optional[bool] = None
        self._cache_duration = timedelta(minutes=5)
    
    def scan(self) -> List[SentinelAlert]:
        """
        Perform comprehensive system health scan.
        
        Returns:
            List of SentinelAlert objects found during scan
        """
        alerts = []
        
        # Check 1: Log Errors (Layer 1)
        alerts.extend(self._check_log_errors())
        
        # Check 2: Failed Cases (Layer 2)
        alerts.extend(self._check_failed_cases())
        
        # Check 3: Provider Fallback Rate (Layer 1)
        alerts.extend(self._check_provider_fallbacks())
        
        # Check 4: Low Confidence Pattern (Layer 2)
        alerts.extend(self._check_low_confidence())
        
        # Check 5: Knowledge Store Health (Layer 5)
        alerts.extend(self._check_knowledge_health())
        
        # Save alerts to history
        self._save_alert_history(alerts)
        
        logger.info(f"Sentinel scan complete: {len(alerts)} alerts found")
        return alerts
    
    def is_healthy(self) -> bool:
        """
        Check if system is healthy (no high or critical alerts).
        
        Returns:
            True if healthy, False otherwise
        """
        # Use cached result if recent
        if self._last_scan_time and self._last_scan_result is not None:
            if datetime.utcnow() - self._last_scan_time < self._cache_duration:
                return self._last_scan_result
        
        # Perform new scan
        alerts = self.scan()
        high_or_critical = [a for a in alerts if a.severity in ("high", "critical")]
        
        result = len(high_or_critical) == 0
        self._last_scan_time = datetime.utcnow()
        self._last_scan_result = result
        
        return result
    
    def _check_log_errors(self) -> List[SentinelAlert]:
        """Check for errors in log files."""
        alerts = []
        logs_dir = self.data_dir / "logs"
        
        if not logs_dir.exists():
            return alerts
        
        try:
            error_count = 0
            first_error = None
            
            for log_file in logs_dir.glob("*.log"):
                try:
                    with open(log_file, 'r') as f:
                        lines = f.readlines()
                        recent_lines = lines[-200:] if len(lines) > 200 else lines
                        
                        for line in recent_lines:
                            if any(keyword in line for keyword in ["ERROR", "CRITICAL", "Exception", "Traceback"]):
                                error_count += 1
                                if first_error is None:
                                    first_error = line.strip()[:300]
                except Exception as e:
                    logger.warning(f"Failed to read log file {log_file}: {e}")
                    continue
            
            if error_count > 10:
                alerts.append(SentinelAlert(
                    layer=1,
                    component="logs",
                    issue_type="error",
                    severity="high",
                    raw_evidence=f"Found {error_count} errors in logs. First: {first_error or 'N/A'}"
                ))
        
        except Exception as e:
            logger.warning(f"Failed to check log errors: {e}")
        
        return alerts
    
    def _check_failed_cases(self) -> List[SentinelAlert]:
        """Check for failed case executions."""
        alerts = []
        memory_dir = self.data_dir / "memory"
        
        if not memory_dir.exists() or not any(memory_dir.iterdir()):
            return alerts
        
        try:
            case_files = sorted(memory_dir.glob("*.json"), key=os.path.getmtime, reverse=True)[:50]
            
            if not case_files:
                return alerts
            
            total_count = 0
            failed_count = 0
            
            for case_file in case_files:
                try:
                    with open(case_file, 'r') as f:
                        case_data = json.load(f)
                    
                    total_count += 1
                    
                    # Check if case failed
                    final_answer = case_data.get("final_answer", "")
                    outputs = case_data.get("outputs", [])
                    
                    is_failed = False
                    
                    if not final_answer or not outputs:
                        is_failed = True
                    else:
                        # Check for low confidence in any agent output
                        for output in outputs:
                            if isinstance(output, dict):
                                confidence = output.get("confidence", 1.0)
                                if confidence < 0.4:
                                    is_failed = True
                                    break
                    
                    if is_failed:
                        failed_count += 1
                
                except Exception as e:
                    logger.warning(f"Failed to read case file {case_file}: {e}")
                    continue
            
            if total_count > 0:
                failure_rate = failed_count / total_count
                
                if failure_rate > 0.3:
                    severity = "critical" if failure_rate > 0.6 else "high"
                    alerts.append(SentinelAlert(
                        layer=2,
                        component="agents",
                        issue_type="degradation",
                        severity=severity,
                        raw_evidence=f"Failed case rate: {failure_rate*100:.1f}% of last {total_count} cases"
                    ))
        
        except Exception as e:
            logger.warning(f"Failed to check failed cases: {e}")
        
        return alerts
    
    def _check_provider_fallbacks(self) -> List[SentinelAlert]:
        """Check for excessive provider fallbacks."""
        alerts = []
        logs_dir = self.data_dir / "logs"
        
        if not logs_dir.exists():
            return alerts
        
        try:
            fallback_count = 0
            
            for log_file in logs_dir.glob("*.log"):
                try:
                    with open(log_file, 'r') as f:
                        lines = f.readlines()
                        recent_lines = lines[-200:] if len(lines) > 200 else lines
                        
                        for line in recent_lines:
                            if any(keyword in line for keyword in ["fallback", "Fallback", "primary provider failed"]):
                                fallback_count += 1
                except Exception as e:
                    logger.warning(f"Failed to read log file {log_file}: {e}")
                    continue
            
            if fallback_count > 20:
                severity = "high" if fallback_count > 50 else "medium"
                alerts.append(SentinelAlert(
                    layer=1,
                    component="provider",
                    issue_type="degradation",
                    severity=severity,
                    raw_evidence=f"Provider fallback triggered {fallback_count} times in recent logs"
                ))
        
        except Exception as e:
            logger.warning(f"Failed to check provider fallbacks: {e}")
        
        return alerts
    
    def _check_low_confidence(self) -> List[SentinelAlert]:
        """Check for low confidence pattern across cases."""
        alerts = []
        memory_dir = self.data_dir / "memory"
        
        if not memory_dir.exists() or not any(memory_dir.iterdir()):
            return alerts
        
        try:
            case_files = sorted(memory_dir.glob("*.json"), key=os.path.getmtime, reverse=True)[:50]
            
            if not case_files:
                return alerts
            
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
                
                except Exception as e:
                    logger.warning(f"Failed to read case file {case_file}: {e}")
                    continue
            
            if all_confidences:
                avg_confidence = sum(all_confidences) / len(all_confidences)
                
                if avg_confidence < 0.4:
                    alerts.append(SentinelAlert(
                        layer=2,
                        component="synthesizer",
                        issue_type="degradation",
                        severity="medium",
                        raw_evidence=f"Average agent confidence: {avg_confidence:.2f}"
                    ))
        
        except Exception as e:
            logger.warning(f"Failed to check low confidence: {e}")
        
        return alerts
    
    def _check_knowledge_health(self) -> List[SentinelAlert]:
        """Check knowledge store health."""
        alerts = []
        knowledge_dir = self.data_dir / "knowledge"
        
        if not knowledge_dir.exists():
            return alerts
        
        try:
            stale_count = 0
            cutoff = datetime.utcnow() - timedelta(days=7)
            
            for knowledge_file in knowledge_dir.glob("*.json"):
                try:
                    mtime = datetime.fromtimestamp(knowledge_file.stat().st_mtime)
                    if mtime < cutoff:
                        stale_count += 1
                except Exception as e:
                    logger.warning(f"Failed to check knowledge file {knowledge_file}: {e}")
                    continue
            
            if stale_count > 10:
                alerts.append(SentinelAlert(
                    layer=5,
                    component="knowledge_store",
                    issue_type="anomaly",
                    severity="low",
                    raw_evidence=f"{stale_count} knowledge items older than 7 days"
                ))
        
        except Exception as e:
            logger.warning(f"Failed to check knowledge health: {e}")
        
        return alerts
    
    def _save_alert_history(self, alerts: List[SentinelAlert]):
        """Save alerts to history file."""
        try:
            sentinel_dir = self.data_dir / "sentinel"
            sentinel_dir.mkdir(parents=True, exist_ok=True)
            
            history_file = sentinel_dir / "alert_history.json"
            
            # Load existing history
            if history_file.exists():
                with open(history_file, 'r') as f:
                    history = json.load(f)
            else:
                history = []
            
            # Append new alerts
            for alert in alerts:
                history.append(alert.to_dict())
            
            # Keep only last 200 entries
            if len(history) > 200:
                history = history[-200:]
            
            # Save back
            with open(history_file, 'w') as f:
                json.dump(history, f, indent=2)
        
        except Exception as e:
            logger.error(f"Failed to save alert history: {e}")
