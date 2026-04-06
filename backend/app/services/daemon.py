"""
Janus Daemon — Background intelligence engine.
Runs 24/7 with circadian rhythms, watches markets, fetches news, detects events, explores autonomously.
Generates "pending thoughts" — things the system naturally wants to share.
"""

import time
import json
import logging
from datetime import datetime
from pathlib import Path
from app.services.market_watcher import MarketWatcher
from app.services.news_pulse import NewsPulse
from app.services.event_detector import EventDetector
from app.services.signal_queue import SignalQueue
from app.services.circadian_rhythm import CircadianRhythm
from app.services.dream_processor import DreamCycleProcessor
from app.services.curiosity_engine import CuriosityEngine
from app.config import DATA_DIR

logger = logging.getLogger(__name__)

PENDING_THOUGHTS_FILE = DATA_DIR / "daemon" / "pending_thoughts.json"
PENDING_THOUGHTS_FILE.parent.mkdir(parents=True, exist_ok=True)


class JanusDaemon:
    def __init__(self):
        self.market_watcher = MarketWatcher()
        self.news_pulse = NewsPulse()
        self.event_detector = EventDetector()
        self.signal_queue = SignalQueue()
        self.circadian = CircadianRhythm()
        self.dream_processor = DreamCycleProcessor()
        self.curiosity = CuriosityEngine()
        self.cycle_count = 0
        self.last_run = None
        self.last_dream = None
        self.last_curiosity_cycle = None
        self._pending_thoughts = self._load_pending_thoughts()

    def _load_pending_thoughts(self) -> list:
        if PENDING_THOUGHTS_FILE.exists():
            try:
                with open(PENDING_THOUGHTS_FILE) as f:
                    return json.load(f)
            except Exception:
                pass
        return []

    def _save_pending_thoughts(self):
        try:
            self._pending_thoughts = self._pending_thoughts[:30]
            with open(PENDING_THOUGHTS_FILE, "w") as f:
                json.dump(self._pending_thoughts, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save pending thoughts: {e}")

    def _generate_pending_thoughts(self, market_signals, news_signals, events):
        """Convert discoveries into natural thoughts the system wants to share."""
        new_thoughts = []

        for signal in market_signals[:3]:
            ticker = signal.get("ticker", "")
            change = signal.get("change_percent", 0)
            if abs(change) > 2:
                direction = "up" if change > 0 else "down"
                new_thoughts.append(
                    {
                        "thought": f"{ticker} moved {abs(change):.1f}% {direction} — might be worth looking into",
                        "priority": min(abs(change) / 10, 1.0),
                        "created_at": time.time(),
                        "source": "market",
                    }
                )

        for signal in news_signals[:2]:
            topic = signal.get("topic", "")
            headline = signal.get("headline", "")
            if topic and headline:
                new_thoughts.append(
                    {
                        "thought": f"Something happening with {topic}: {headline[:100]}",
                        "priority": 0.4,
                        "created_at": time.time(),
                        "source": "news",
                    }
                )

        for event in events[:2]:
            event_type = event.get("event_type", "")
            description = event.get("description", "")
            if event_type and description:
                new_thoughts.append(
                    {
                        "thought": f"Detected a {event_type} event — {description[:100]}",
                        "priority": 0.6,
                        "created_at": time.time(),
                        "source": "event",
                    }
                )

        if self.last_dream:
            insights = self.last_dream.get("insights", [])
            for insight in insights[:1]:
                new_thoughts.append(
                    {
                        "thought": f"I had a thought during my last dream cycle — {insight[:120]}",
                        "priority": 0.3,
                        "created_at": time.time(),
                        "source": "dream",
                    }
                )

        if self.last_curiosity_cycle:
            discoveries = self.last_curiosity_cycle.get("discoveries", [])
            for d in discoveries[:1]:
                new_thoughts.append(
                    {
                        "thought": f"I found something interesting while exploring — {str(d)[:120]}",
                        "priority": 0.35,
                        "created_at": time.time(),
                        "source": "curiosity",
                    }
                )

        self._pending_thoughts.extend(new_thoughts)
        self._pending_thoughts.sort(key=lambda x: x.get("priority", 0), reverse=True)
        self._pending_thoughts = self._pending_thoughts[:30]
        self._save_pending_thoughts()

        return new_thoughts

    def run(self):
        """Main daemon loop — runs forever with circadian awareness."""
        logger.info("=" * 60)
        logger.info("JANUS DAEMON STARTED — Living Intelligence Engine")
        logger.info(f"Watchlist: {self.market_watcher.watchlist}")
        logger.info(f"Topics: {self.news_pulse.topics}")
        logger.info(f"Circadian Phase: {self.circadian.get_current_phase().value}")
        logger.info("=" * 60)

        while True:
            cycle_start = time.time()
            self.cycle_count += 1
            self.last_run = datetime.utcnow().isoformat()

            phase = self.circadian.get_current_phase()
            phase_config = self.circadian.get_phase_config(phase)

            try:
                logger.info(
                    f"[DAEMON] Cycle #{self.cycle_count} — Phase: {phase.value} ({phase_config['name']})"
                )

                market_signals = self.market_watcher.poll()
                self.signal_queue.add_batch(market_signals)

                news_signals = self.news_pulse.fetch()
                self.signal_queue.add_batch(news_signals)

                all_signals = market_signals + news_signals
                events = self.event_detector.detect(all_signals)

                new_thoughts = self._generate_pending_thoughts(
                    market_signals, news_signals, events
                )
                if new_thoughts:
                    logger.info(
                        f"[DAEMON] Generated {len(new_thoughts)} pending thoughts"
                    )

                if phase.value == "night":
                    dream_report = self.dream_processor.run_dream_cycle()
                    self.last_dream = dream_report
                    logger.info(
                        f"[DAEMON] Dream cycle: {len(dream_report.get('insights', []))} insights, {len(dream_report.get('hypotheses', []))} hypotheses"
                    )

                    curiosity_report = self.curiosity.run_curiosity_cycle()
                    self.last_curiosity_cycle = curiosity_report
                    logger.info(
                        f"[DAEMON] Curiosity cycle: {curiosity_report.get('total_discoveries', 0)} discoveries, {curiosity_report.get('total_interests', 0)} interests"
                    )

                elapsed = time.time() - cycle_start
                stats = self.signal_queue.get_stats()

                logger.info(
                    f"[DAEMON] Cycle #{self.cycle_count} complete in {elapsed:.1f}s"
                )
                logger.info(
                    f"[DAEMON] Market signals: {len(market_signals)}, News signals: {len(news_signals)}, Events: {len(events)}"
                )
                logger.info(f"[DAEMON] Queue stats: {stats}")

            except Exception as e:
                logger.error(f"[DAEMON] Cycle #{self.cycle_count} failed: {e}")

            sleep_time = phase_config.get("poll_interval", 900)
            logger.info(f"[DAEMON] Sleeping for {sleep_time}s ({phase.value} phase)")
            time.sleep(sleep_time)

    def get_status(self) -> dict:
        """Get daemon status."""
        phase = self.circadian.get_current_phase()
        phase_config = self.circadian.get_phase_config(phase)

        return {
            "running": True,
            "cycle_count": self.cycle_count,
            "last_run": self.last_run,
            "circadian": {
                "current_phase": phase.value,
                "phase_name": phase_config["name"],
                "phase_description": phase_config["description"],
                "priority": phase_config["priority"],
                "current_tasks": phase_config["tasks"],
            },
            "watchlist": self.market_watcher.watchlist,
            "topics": self.news_pulse.topics,
            "signal_queue": self.signal_queue.get_stats(),
            "dream_processor": self.dream_processor.get_status(),
            "curiosity_engine": self.curiosity.get_status(),
            "last_dream": self.last_dream,
            "last_curiosity_cycle": self.last_curiosity_cycle,
            "pending_thoughts": self._pending_thoughts[:10],
        }
