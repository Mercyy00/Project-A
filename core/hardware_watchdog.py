"""
Hardware Watchdog and Proactive Monitor for Project JARVIS.
Author: Pair A & C (Jay & Abhijit)

Monitors hardware telemetry and scheduled events in background:
1. Battery status: checks percentage (e.g. alerts when <= 20% or 15% and discharging).
2. Disk space: alerts when any drive is almost full (> 90% or free space < 10GB).
3. Memory and CPU spikes: alerts on prolonged high resource exhaustion.
4. Meeting and Reminder alerts: detects meetings scheduled within the next 10 minutes.
5. Smart debouncing: prevents repetitive spamming within quiet intervals.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
import logging
import os
from pathlib import Path
import time
from typing import Any, Dict, List, Optional, Tuple

import psutil

from core.scheduler import JarvisScheduler

logger = logging.getLogger(__name__)


class HardwareWatchdog:
    """Monitors system hardware health and upcoming deadlines proactively."""

    _instance: Optional[HardwareWatchdog] = None

    @classmethod
    def get_instance(cls) -> HardwareWatchdog:
        """Singleton accessor."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(
        self,
        battery_threshold_low: int = 20,
        battery_threshold_critical: int = 15,
        disk_threshold_percent: float = 90.0,
        cpu_threshold_percent: float = 92.0,
        ram_threshold_percent: float = 92.0,
        meeting_window_minutes: int = 10,
        debounce_seconds: float = 600.0,  # 10 minutes between duplicate alerts
    ) -> None:
        self.battery_threshold_low = battery_threshold_low
        self.battery_threshold_critical = battery_threshold_critical
        self.disk_threshold_percent = disk_threshold_percent
        self.cpu_threshold_percent = cpu_threshold_percent
        self.ram_threshold_percent = ram_threshold_percent
        self.meeting_window_minutes = meeting_window_minutes
        self.debounce_seconds = debounce_seconds

        self._last_alert_times: Dict[str, float] = {}
        self._is_monitoring = False
        self._monitor_task: Optional[asyncio.Task] = None

    def _should_debounce(self, alert_key: str) -> bool:
        """Determines whether an alert with this key was dispatched recently."""
        now = time.time()
        last = self._last_alert_times.get(alert_key, 0.0)
        if now - last < self.debounce_seconds:
            return True
        self._last_alert_times[alert_key] = now
        return False

    def check_battery(self) -> Optional[Dict[str, Any]]:
        """Checks battery level and charging state; dispatches alert if low and discharging."""
        try:
            battery = psutil.sensors_battery()
            if not battery:
                return None

            percent = battery.percent
            plugged = battery.power_plugged

            if not plugged:
                if percent <= self.battery_threshold_critical:
                    key = "battery_critical"
                    if not self._should_debounce(key):
                        title = f"Battery {percent}% (Critical)"
                        msg = f"Battery charge has dropped to {percent}%. Please connect the charger immediately."
                        return JarvisScheduler.get_instance().dispatch_alert(
                            title=title, message=msg, level="critical", category="hardware"
                        )
                elif percent <= self.battery_threshold_low:
                    key = "battery_low"
                    if not self._should_debounce(key):
                        title = f"Battery {percent}%"
                        msg = f"Battery is at {percent}%. Consider plugging in your power adapter."
                        return JarvisScheduler.get_instance().dispatch_alert(
                            title=title, message=msg, level="warning", category="hardware"
                        )
        except Exception as exc:
            logger.debug("Watchdog battery inspection error: %s", exc)
        return None

    def check_disk(self) -> List[Dict[str, Any]]:
        """Checks available disk space across partitions; alerts if any drive is almost full."""
        dispatched: List[Dict[str, Any]] = []
        try:
            partitions = psutil.disk_partitions(all=False)
            for part in partitions:
                # Skip virtual / read-only mounts
                if "cdrom" in part.opts or not part.device:
                    continue
                try:
                    usage = psutil.disk_usage(part.mountpoint)
                    free_gb = round(usage.free / (1024 ** 3), 1)
                    percent = usage.percent

                    if percent >= self.disk_threshold_percent or free_gb < 8.0:
                        key = f"disk_{part.mountpoint}"
                        if not self._should_debounce(key):
                            title = f"Disk Almost Full ({part.mountpoint})"
                            msg = f"Drive {part.mountpoint} is {percent}% full with only {free_gb} GB remaining free."
                            alert = JarvisScheduler.get_instance().dispatch_alert(
                                title=title, message=msg, level="warning", category="hardware"
                            )
                            dispatched.append(alert)
                except (PermissionError, OSError):
                    continue
        except Exception as exc:
            logger.debug("Watchdog disk inspection error: %s", exc)
        return dispatched

    def check_cpu_and_ram(self) -> Optional[Dict[str, Any]]:
        """Checks system CPU and RAM loads."""
        try:
            cpu = psutil.cpu_percent(interval=None)
            ram = psutil.virtual_memory().percent

            if cpu >= self.cpu_threshold_percent:
                key = "cpu_overload"
                if not self._should_debounce(key):
                    title = f"High CPU Load ({cpu}%)"
                    msg = f"Processor utilization has reached {cpu}%. Multiple heavy background tasks may be active."
                    return JarvisScheduler.get_instance().dispatch_alert(
                        title=title, message=msg, level="info", category="hardware"
                    )

            if ram >= self.ram_threshold_percent:
                key = "ram_overload"
                if not self._should_debounce(key):
                    title = f"High Memory Usage ({ram}%)"
                    msg = f"System RAM usage is at {ram}%. Consider closing inactive applications."
                    return JarvisScheduler.get_instance().dispatch_alert(
                        title=title, message=msg, level="info", category="hardware"
                    )
        except Exception as exc:
            logger.debug("Watchdog CPU/RAM inspection error: %s", exc)
        return None

    def check_upcoming_meetings(self) -> List[Dict[str, Any]]:
        """Checks for meetings or scheduled reminders occurring in the next 10 minutes."""
        alerts: List[Dict[str, Any]] = []
        now = datetime.now()

        # 1. Check reminders from messaging/reminders.py
        try:
            from messaging.reminders import load_reminders
            reminders = load_reminders()
            for r in reminders:
                if r.get("status") == "sent":
                    continue
                rem_dt_str = r.get("remind_at")
                if not rem_dt_str:
                    continue
                try:
                    rem_dt = datetime.fromisoformat(rem_dt_str)
                    diff = (rem_dt - now).total_seconds()
                    # If within meeting window (0 to 10 minutes)
                    if 0 <= diff <= (self.meeting_window_minutes * 60):
                        key = f"reminder_{r.get('id')}"
                        if not self._should_debounce(key):
                            mins = max(1, int(diff // 60))
                            text = r.get("text", "Upcoming Event")
                            title = f"Meeting in {mins} minutes"
                            msg = f"Upcoming reminder: {text} (scheduled for {rem_dt.strftime('%H:%M')})."
                            alert = JarvisScheduler.get_instance().dispatch_alert(
                                title=title, message=msg, level="urgent", category="reminder"
                            )
                            alerts.append(alert)
                except Exception:
                    continue
        except Exception as r_err:
            logger.debug("Could not inspect reminders for meetings: %s", r_err)

        # 2. Check Google Calendar events if configured
        try:
            from tools.google_workspace_tool import get_cached_or_quick_events
            cal_events = get_cached_or_quick_events()
            for ev in cal_events:
                start_iso = ev.get("start")
                if not start_iso:
                    continue
                try:
                    ev_dt = datetime.fromisoformat(start_iso)
                    diff = (ev_dt - now).total_seconds()
                    if 0 <= diff <= (self.meeting_window_minutes * 60):
                        ev_id = ev.get("id", ev.get("summary", "meeting"))
                        key = f"cal_{ev_id}"
                        if not self._should_debounce(key):
                            mins = max(1, int(diff // 60))
                            summary = ev.get("summary", "Scheduled Meeting")
                            title = f"Meeting in {mins} minutes"
                            msg = f"Upcoming event: '{summary}' starts in {mins} minutes."
                            alert = JarvisScheduler.get_instance().dispatch_alert(
                                title=title, message=msg, level="urgent", category="reminder"
                            )
                            alerts.append(alert)
                except Exception:
                    continue
        except Exception:
            pass

        return alerts

    def run_all_checks(self) -> List[Dict[str, Any]]:
        """Runs a complete check sweep across battery, disk, resources, and meetings."""
        results: List[Dict[str, Any]] = []
        bat = self.check_battery()
        if bat:
            results.append(bat)
        results.extend(self.check_disk())
        res = self.check_cpu_and_ram()
        if res:
            results.append(res)
        results.extend(self.check_upcoming_meetings())
        return results

    async def _watchdog_loop(self, poll_interval_seconds: float = 30.0) -> None:
        """Continuous background async watchdog loop."""
        logger.info("Hardware Watchdog background monitoring loop started (interval=%ss).", poll_interval_seconds)
        while self._is_monitoring:
            try:
                self.run_all_checks()
            except Exception as e:
                logger.debug("Error in watchdog check sweep: %s", e)
            await asyncio.sleep(poll_interval_seconds)

    def start_background_monitoring(self, poll_interval_seconds: float = 30.0) -> None:
        """Starts the background async watchdog monitoring task."""
        if self._is_monitoring:
            return
        self._is_monitoring = True
        try:
            loop = asyncio.get_running_loop()
            self._monitor_task = loop.create_task(self._watchdog_loop(poll_interval_seconds))
        except RuntimeError:
            # If no running loop in current thread, schedule on scheduler
            JarvisScheduler.get_instance().add_job(
                self.run_all_checks,
                trigger="interval",
                seconds=int(poll_interval_seconds)
            )

    def stop_background_monitoring(self) -> None:
        """Stops the watchdog monitoring task."""
        self._is_monitoring = False
        if self._monitor_task and not self._monitor_task.done():
            self._monitor_task.cancel()
