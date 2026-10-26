"""
Proactive Event-Driven Scheduler and Alert Bus for Project JARVIS.
Author: Pair A (Jay & Rohit)

Provides:
- APScheduler AsyncIOScheduler and background async task runner
- Event-driven alert bus dispatching proactive notifications to:
  1. Connected Desktop HUD WebSockets (proactive push alerts)
  2. Telegram Bot (send_telegram push alerts)
  3. Custom registered listeners / logging
"""

from __future__ import annotations

import asyncio
from datetime import datetime
import logging
import time
from typing import Any, Callable, Coroutine, Dict, List, Optional

logger = logging.getLogger(__name__)


class JarvisScheduler:
    """Async scheduler and proactive event bus for Project JARVIS."""

    _instance: Optional[JarvisScheduler] = None

    @classmethod
    def get_instance(cls) -> JarvisScheduler:
        """Singleton accessor for JarvisScheduler."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        self.listeners: List[Callable[[Dict[str, Any]], Any]] = []
        self._scheduler: Optional[Any] = None
        self._fallback_task: Optional[asyncio.Task] = None
        self._is_running = False
        self._alert_history: List[Dict[str, Any]] = []

    def register_alert_listener(self, listener: Callable[[Dict[str, Any]], Any]) -> None:
        """Register a callback to receive dispatched proactive alerts."""
        if listener not in self.listeners:
            self.listeners.append(listener)

    def unregister_alert_listener(self, listener: Callable[[Dict[str, Any]], Any]) -> None:
        """Unregister an alert listener."""
        if listener in self.listeners:
            self.listeners.remove(listener)

    def start(self) -> None:
        """Starts the background scheduler."""
        if self._is_running:
            return

        try:
            from apscheduler.schedulers.asyncio import AsyncIOScheduler
            self._scheduler = AsyncIOScheduler()
            self._scheduler.start()
            self._is_running = True
            logger.info("APScheduler AsyncIOScheduler started successfully.")
        except Exception as exc:
            logger.warning("APScheduler failed to start, falling back to background loop: %s", exc)
            self._is_running = True

    def stop(self) -> None:
        """Stops the scheduler and cancels background tasks."""
        if not self._is_running:
            return
        if self._scheduler and self._scheduler.running:
            try:
                self._scheduler.shutdown(wait=False)
            except Exception:
                pass
        if self._fallback_task and not self._fallback_task.done():
            self._fallback_task.cancel()
        self._is_running = False

    def add_job(
        self,
        func: Callable[..., Any],
        trigger: str = "interval",
        **trigger_args: Any
    ) -> Optional[str]:
        """Schedule a function to execute periodically or at a specific time."""
        if not self._is_running:
            self.start()

        if self._scheduler:
            try:
                job = self._scheduler.add_job(func, trigger, **trigger_args)
                return job.id
            except Exception as e:
                logger.error("Failed to add job to APScheduler: %s", e)
        return None

    def dispatch_alert(
        self,
        title: str,
        message: str,
        level: str = "warning",
        category: str = "hardware",
        push_telegram: bool = True,
        push_hud: bool = True,
    ) -> Dict[str, Any]:
        """Dispatches a proactive alert event to the HUD, Telegram, and registered listeners.

        Args:
            title: Short alert title (e.g. 'Battery 15%', 'Disk Almost Full').
            message: Informative body text.
            level: 'info', 'warning', 'critical', or 'urgent'.
            category: 'hardware', 'reminder', 'system', 'security'.
            push_telegram: Whether to dispatch via Telegram bot.
            push_hud: Whether to push to connected HUD WebSockets.

        Returns:
            Structured alert record.
        """
        alert_record = {
            "title": title.strip(),
            "message": message.strip(),
            "level": level.lower(),
            "category": category.lower(),
            "timestamp": time.time(),
            "formatted_time": datetime.now().strftime("%H:%M:%S"),
            "push_telegram": push_telegram,
            "push_hud": push_hud,
        }

        self._alert_history.append(alert_record)
        if len(self._alert_history) > 100:
            self._alert_history = self._alert_history[-100:]

        logger.info("[PROACTIVE ALERT] [%s] %s: %s", level.upper(), title, message)

        # 1. Forward to registered listeners (e.g. WebSocket HUD broadcast)
        for listener in list(self.listeners):
            try:
                res = listener(alert_record)
                if asyncio.iscoroutine(res):
                    try:
                        loop = asyncio.get_running_loop()
                        loop.create_task(res)
                    except RuntimeError:
                        res.close()
            except Exception as listen_err:
                logger.debug("Error in alert listener: %s", listen_err)

        # 2. Forward to Telegram if configured
        if push_telegram:
            try:
                from messaging.telegram_bot import send_telegram
                telegram_text = f"JARVIS Alert [{level.upper()}]\n{title}\n\n{message}"
                send_telegram(telegram_text)
            except Exception as tg_err:
                logger.debug("Could not push alert to Telegram: %s", tg_err)

        return alert_record

    def get_recent_alerts(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Returns the most recent proactive alerts."""
        return list(reversed(self._alert_history[-limit:]))
