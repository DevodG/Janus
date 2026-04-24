"""
Sentinel Scheduler - Background Cycle Execution

Runs sentinel cycles on a schedule with CPU/battery safeguards.
Uses asyncio for non-blocking background execution.
"""

import asyncio
import logging
import os
from datetime import datetime, timedelta
from typing import Optional

try:
    import psutil
except ImportError:
    psutil = None

logger = logging.getLogger(__name__)

# Module-level state
_scheduler_task: Optional[asyncio.Task] = None
_scheduler_running: bool = False


async def _sentinel_cycle_loop():
    """Background loop that runs sentinel cycles."""
    from app.services.sentinel.sentinel_engine import SentinelEngine
    
    global _scheduler_running
    
    engine = SentinelEngine()
    interval_minutes = int(os.getenv("SENTINEL_CYCLE_INTERVAL_MINUTES", "60"))
    
    logger.info(f"Sentinel scheduler started (interval: {interval_minutes} minutes)")
    
    while _scheduler_running:
        try:
            # Check if sentinel is enabled
            if not os.getenv("SENTINEL_ENABLED", "true").lower() == "true":
                logger.debug("Sentinel disabled, skipping cycle")
                await asyncio.sleep(60)
                continue
            
            # Check CPU/battery safeguards
            if not _check_safeguards():
                logger.info("Sentinel cycle skipped due to safeguards (high CPU or low battery)")
                await asyncio.sleep(300)  # Wait 5 minutes before checking again
                continue
            
            # Run cycle
            logger.info("Starting scheduled sentinel cycle")
            report = engine.run_cycle()
            logger.info(f"Sentinel cycle complete: {report.cycle_id}")
            
            # Wait for next cycle
            await asyncio.sleep(interval_minutes * 60)
        
        except asyncio.CancelledError:
            logger.info("Sentinel scheduler cancelled")
            break
        except Exception as e:
            logger.error(f"Sentinel cycle error: {e}")
            await asyncio.sleep(300)  # Wait 5 minutes on error


def _check_safeguards() -> bool:
    """
    Check CPU and battery safeguards.
    
    Returns:
        True if safe to run, False otherwise
    """
    if psutil is None:
        # If psutil not available, assume safe
        return True
    
    try:
        # Check CPU usage
        cpu_threshold = float(os.getenv("SENTINEL_CPU_THRESHOLD", "80.0"))
        cpu_percent = psutil.cpu_percent(interval=1)
        
        if cpu_percent > cpu_threshold:
            logger.debug(f"CPU usage too high: {cpu_percent}% > {cpu_threshold}%")
            return False
        
        # Check battery (if on laptop)
        battery = psutil.sensors_battery()
        if battery is not None:
            battery_threshold = float(os.getenv("SENTINEL_BATTERY_THRESHOLD", "20.0"))
            
            if battery.percent < battery_threshold and not battery.power_plugged:
                logger.debug(f"Battery too low: {battery.percent}% < {battery_threshold}%")
                return False
        
        return True
    
    except Exception as e:
        logger.warning(f"Safeguard check failed: {e}")
        return True  # Fail open


def start_sentinel_scheduler():
    """
    Start the sentinel scheduler in the background.
    
    This function is called from main.py on app startup.
    """
    global _scheduler_task, _scheduler_running
    
    if _scheduler_running:
        logger.warning("Sentinel scheduler already running")
        return
    
    _scheduler_running = True
    _scheduler_task = asyncio.create_task(_sentinel_cycle_loop())
    logger.info("Sentinel scheduler task created")


def stop_sentinel_scheduler():
    """
    Stop the sentinel scheduler.
    
    This function can be called to gracefully shut down the scheduler.
    """
    global _scheduler_task, _scheduler_running
    
    if not _scheduler_running:
        logger.warning("Sentinel scheduler not running")
        return
    
    _scheduler_running = False
    
    if _scheduler_task:
        _scheduler_task.cancel()
        logger.info("Sentinel scheduler stopped")


def is_scheduler_running() -> bool:
    """Check if scheduler is running."""
    return _scheduler_running
