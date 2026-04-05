"""
Janus Daemon — Background intelligence engine.
Runs 24/7 with circadian rhythms, watches markets, fetches news, detects events, explores autonomously.
"""

import time
import logging
from datetime import datetime
from app.services.market_watcher import MarketWatcher
from app.services.news_pulse import NewsPulse
from app.services.event_detector import EventDetector
from app.services.signal_queue import SignalQueue
from app.services.circadian_rhythm import CircadianRhythm
from app.services.dream_processor import DreamCycleProcessor
from app.services.curiosity_engine import CuriosityEngine

logger = logging.getLogger(__name__)


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

            # Get current circadian phase
            phase = self.circadian.get_current_phase()
            phase_config = self.circadian.get_phase_config(phase)

            try:
                logger.info(
                    f"[DAEMON] Cycle #{self.cycle_count} — Phase: {phase.value} ({phase_config['name']})"
                )

                # 1. Poll markets
                market_signals = self.market_watcher.poll()
                self.signal_queue.add_batch(market_signals)

                # 2. Fetch news
                news_signals = self.news_pulse.fetch()
                self.signal_queue.add_batch(news_signals)

                # 3. Detect events from all signals
                all_signals = market_signals + news_signals
                events = self.event_detector.detect(all_signals)

                # 4. Phase-specific processing
                if phase.value == "night":
                    # Dream cycle during night phase
                    dream_report = self.dream_processor.run_dream_cycle()
                    self.last_dream = dream_report
                    logger.info(
                        f"[DAEMON] Dream cycle: {len(dream_report.get('insights', []))} insights, {len(dream_report.get('hypotheses', []))} hypotheses"
                    )

                    # Curiosity cycle during night (exploration time)
                    curiosity_report = self.curiosity.run_curiosity_cycle()
                    self.last_curiosity_cycle = curiosity_report
                    logger.info(
                        f"[DAEMON] Curiosity cycle: {curiosity_report.get('total_discoveries', 0)} discoveries, {curiosity_report.get('total_interests', 0)} interests"
                    )

                # 5. Log summary
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

            # Sleep based on current phase
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
        }
