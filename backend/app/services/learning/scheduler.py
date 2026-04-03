"""
Learning scheduler with safeguards for laptop deployment.

Schedules learning tasks with CPU, battery, and system idle checks.
"""

import asyncio
import logging
import psutil
from datetime import datetime, timedelta
from typing import Dict, Any, Callable, Optional

logger = logging.getLogger(__name__)


class LearningScheduler:
    """Schedules learning tasks with system safeguards."""
    
    def __init__(
        self,
        max_cpu_percent: float = 50.0,
        min_battery_percent: float = 30.0,
        check_interval_seconds: int = 60,
    ):
        self.max_cpu_percent = max_cpu_percent
        self.min_battery_percent = min_battery_percent
        self.check_interval_seconds = check_interval_seconds
        self.scheduled_tasks = {}
        self.running = False
        self.last_run = {}
    
    def schedule_task(
        self,
        task_name: str,
        task_fn: Callable,
        interval_hours: int,
        run_immediately: bool = False,
    ):
        """
        Schedule a learning task.
        
        Args:
            task_name: Task name
            task_fn: Async function to run
            interval_hours: Interval in hours
            run_immediately: Whether to run immediately on first check
        """
        self.scheduled_tasks[task_name] = {
            "fn": task_fn,
            "interval": timedelta(hours=interval_hours),
            "last_run": None if run_immediately else datetime.utcnow(),
        }
        logger.info(f"Scheduled task: {task_name} (interval={interval_hours}h)")
    
    async def start(self):
        """Start the scheduler."""
        if self.running:
            logger.warning("Scheduler already running")
            return
        
        self.running = True
        logger.info("Learning scheduler started")
        
        while self.running:
            try:
                await self._check_and_run_tasks()
                await asyncio.sleep(self.check_interval_seconds)
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
                await asyncio.sleep(self.check_interval_seconds)
    
    def stop(self):
        """Stop the scheduler."""
        self.running = False
        logger.info("Learning scheduler stopped")
    
    async def run_once(self, task_name: str) -> Dict[str, Any]:
        """
        Run a task once manually.
        
        Args:
            task_name: Task name
            
        Returns:
            Task result
        """
        if task_name not in self.scheduled_tasks:
            raise ValueError(f"Task not found: {task_name}")
        
        task = self.scheduled_tasks[task_name]
        
        logger.info(f"Running task manually: {task_name}")
        
        try:
            result = await task["fn"]()
            task["last_run"] = datetime.utcnow()
            self.last_run[task_name] = task["last_run"].isoformat()
            
            return {
                "task_name": task_name,
                "status": "success",
                "result": result,
                "timestamp": task["last_run"].isoformat(),
            }
        
        except Exception as e:
            logger.error(f"Task failed: {task_name}: {e}")
            return {
                "task_name": task_name,
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            }
    
    def is_system_idle(self) -> bool:
        """
        Check if system is idle (low CPU usage).
        
        Returns:
            True if system is idle
        """
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            is_idle = cpu_percent < self.max_cpu_percent
            
            if not is_idle:
                logger.debug(f"System not idle: CPU={cpu_percent:.1f}% (max={self.max_cpu_percent}%)")
            
            return is_idle
        
        except Exception as e:
            logger.error(f"Failed to check CPU usage: {e}")
            return False  # Assume not idle on error
    
    def is_battery_ok(self) -> bool:
        """
        Check if battery level is sufficient.
        
        Returns:
            True if battery is OK or plugged in
        """
        try:
            battery = psutil.sensors_battery()
            
            # If no battery (desktop) or plugged in, always OK
            if battery is None or battery.power_plugged:
                return True
            
            # Check battery percentage
            is_ok = battery.percent >= self.min_battery_percent
            
            if not is_ok:
                logger.debug(f"Battery too low: {battery.percent:.1f}% (min={self.min_battery_percent}%)")
            
            return is_ok
        
        except Exception as e:
            logger.error(f"Failed to check battery: {e}")
            return True  # Assume OK on error (might be desktop)
    
    async def _check_and_run_tasks(self):
        """Check and run scheduled tasks if conditions are met."""
        # Check system conditions
        if not self.is_system_idle():
            logger.debug("Skipping scheduled tasks: system not idle")
            return
        
        if not self.is_battery_ok():
            logger.debug("Skipping scheduled tasks: battery too low")
            return
        
        # Check each task
        now = datetime.utcnow()
        
        for task_name, task in self.scheduled_tasks.items():
            # Check if task is due
            if task["last_run"] is not None:
                time_since_last_run = now - task["last_run"]
                if time_since_last_run < task["interval"]:
                    continue
            
            # Run task
            logger.info(f"Running scheduled task: {task_name}")
            
            try:
                result = await task["fn"]()
                task["last_run"] = now
                self.last_run[task_name] = now.isoformat()
                logger.info(f"Task completed: {task_name}")
            
            except Exception as e:
                logger.error(f"Task failed: {task_name}: {e}")
                # Still update last_run to avoid retry loop
                task["last_run"] = now
                self.last_run[task_name] = now.isoformat()
    
    def get_status(self) -> Dict[str, Any]:
        """Get scheduler status."""
        tasks_status = []
        
        for task_name, task in self.scheduled_tasks.items():
            last_run = task["last_run"]
            next_run = None
            
            if last_run is not None:
                next_run = (last_run + task["interval"]).isoformat()
            
            tasks_status.append({
                "name": task_name,
                "interval_hours": task["interval"].total_seconds() / 3600,
                "last_run": last_run.isoformat() if last_run else None,
                "next_run": next_run,
            })
        
        return {
            "running": self.running,
            "system_idle": self.is_system_idle(),
            "battery_ok": self.is_battery_ok(),
            "tasks": tasks_status,
        }
