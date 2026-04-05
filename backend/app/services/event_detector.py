"""
Event Detector — Background daemon service for Janus.
Detects meaningful events from market and news signals, classifies event types.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent.parent / "data" / "daemon"
DATA_DIR.mkdir(parents=True, exist_ok=True)


class EventDetector:
    def __init__(self):
        self.event_types = {
            "earnings": [
                "earnings",
                "revenue",
                "profit",
                "loss",
                "guidance",
                "eps",
                "quarterly",
            ],
            "macro": [
                "fed",
                "rate",
                "inflation",
                "gdp",
                "cpi",
                "ppi",
                "unemployment",
                "jobs",
            ],
            "ma": ["merger", "acquisition", "buyout", "takeover", "deal"],
            "management": [
                "ceo",
                "cfo",
                "resign",
                "fired",
                "appointed",
                "hired",
                "stepping down",
            ],
            "product": [
                "launch",
                "release",
                "recall",
                "update",
                "upgrade",
                "new product",
            ],
            "legal": [
                "lawsuit",
                "sec",
                "investigation",
                "fine",
                "penalty",
                "settlement",
                "regulation",
            ],
            "geopolitical": [
                "sanction",
                "tariff",
                "trade war",
                "conflict",
                "war",
                "election",
            ],
            "supply_chain": ["shortage", "supply chain", "disruption", "delay", "chip"],
            "analyst": ["upgrade", "downgrade", "target price", "analyst", "rating"],
            "sector": ["sector", "industry", "market cap", "benchmark", "index"],
        }
        self.events: List[Dict] = []
        self._load_events()

    def _load_events(self):
        """Load events from disk."""
        events_file = DATA_DIR / "events.json"
        if events_file.exists():
            try:
                with open(events_file) as f:
                    self.events = json.load(f)
            except:
                self.events = []

    def _save_events(self):
        """Save events to disk."""
        events_file = DATA_DIR / "events.json"
        with open(events_file, "w") as f:
            json.dump(self.events[-500:], f, indent=2)  # Keep last 500

    def detect(self, signals: List[Dict]) -> List[Dict]:
        """Detect events from signals. Returns list of classified events."""
        events = []
        for signal in signals:
            event = self._classify_signal(signal)
            if event:
                events.append(event)
                self.events.append(event)

        if events:
            self._save_events()
            logger.info(f"[EVENT] Detected {len(events)} events")

        return events

    def _classify_signal(self, signal: Dict) -> Optional[Dict]:
        """Classify a signal into an event type."""
        text = ""
        if signal.get("type") == "news":
            text = f"{signal.get('title', '')} {signal.get('description', '')}".lower()
        elif signal.get("type") == "market":
            text = f"{' '.join(signal.get('signals', []))}".lower()

        if not text:
            return None

        detected_types = []
        for event_type, keywords in self.event_types.items():
            if any(kw in text for kw in keywords):
                detected_types.append(event_type)

        if not detected_types:
            return None

        event = {
            "type": "event",
            "event_types": detected_types,
            "primary_type": detected_types[0],
            "source": signal,
            "timestamp": signal.get("timestamp", datetime.utcnow().isoformat()),
            "severity": signal.get("severity", "low"),
        }

        logger.info(f"[EVENT] {detected_types}: {text[:100]}...")
        return event

    def get_recent_events(self, limit: int = 20) -> List[Dict]:
        """Get recent events."""
        return self.events[-limit:]

    def get_events_by_type(self, event_type: str) -> List[Dict]:
        """Get events by type."""
        return [e for e in self.events if event_type in e.get("event_types", [])]
