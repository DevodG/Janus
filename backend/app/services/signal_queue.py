"""
Signal Queue — Priority queue for Janus background signals.
Stores, prioritizes, and surfaces alerts.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent.parent / "data" / "daemon"
DATA_DIR.mkdir(parents=True, exist_ok=True)

SEVERITY_PRIORITY = {
    "critical": 4,
    "high": 3,
    "medium": 2,
    "low": 1,
}


class SignalQueue:
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self.signals: List[Dict] = []
        self._load_signals()

    def _load_signals(self):
        """Load signals from disk."""
        signals_file = DATA_DIR / "signal_queue.json"
        if signals_file.exists():
            try:
                with open(signals_file) as f:
                    self.signals = json.load(f)
            except:
                self.signals = []

    def _save_signals(self):
        """Save signals to disk."""
        signals_file = DATA_DIR / "signal_queue.json"
        with open(signals_file, "w") as f:
            json.dump(self.signals[-self.max_size :], f, indent=2)

    def add(self, signal: Dict):
        """Add a signal to the queue."""
        self.signals.append(signal)
        # Keep only max_size most recent
        self.signals = self.signals[-self.max_size :]
        self._save_signals()

    def add_batch(self, signals: List[Dict]):
        """Add multiple signals."""
        for signal in signals:
            self.add(signal)

    def get_alerts(self, limit: int = 20, min_severity: str = "low") -> List[Dict]:
        """Get alerts sorted by priority."""
        min_priority = SEVERITY_PRIORITY.get(min_severity, 0)
        filtered = [
            s
            for s in self.signals
            if SEVERITY_PRIORITY.get(s.get("severity", "low"), 0) >= min_priority
        ]
        # Sort by severity (desc) then timestamp (desc)
        filtered.sort(
            key=lambda s: (
                SEVERITY_PRIORITY.get(s.get("severity", "low"), 0),
                s.get("timestamp", ""),
            ),
            reverse=True,
        )
        return filtered[:limit]

    def get_stats(self) -> Dict:
        """Get queue statistics."""
        severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        type_counts = {}

        for signal in self.signals:
            sev = signal.get("severity", "low")
            if sev in severity_counts:
                severity_counts[sev] += 1

            sig_type = signal.get("type", "unknown")
            type_counts[sig_type] = type_counts.get(sig_type, 0) + 1

        return {
            "total_signals": len(self.signals),
            "severity_counts": severity_counts,
            "type_counts": type_counts,
            "latest_signal": self.signals[-1].get("timestamp")
            if self.signals
            else None,
        }

    def clear_old(self, days: int = 7):
        """Clear signals older than N days."""
        cutoff = datetime.utcnow().timestamp() - (days * 86400)
        self.signals = [
            s
            for s in self.signals
            if datetime.fromisoformat(s.get("timestamp", "2000-01-01")).timestamp()
            > cutoff
        ]
        self._save_signals()
