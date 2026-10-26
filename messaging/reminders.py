"""Persistent Reminders module for Project JARVIS (Trupti - Day 7).

Parses natural reminder timings ('HH:MM' 24h format or 'in N minutes'),
persists reminders in messaging/reminders.json to survive application restarts,
and runs a resilient background daemon that dispatches due reminders via send_telegram().
"""

from __future__ import annotations

from datetime import datetime, timedelta
import json
import logging
from pathlib import Path
import re
import sys
import threading
import time
from typing import Any, Dict, List, Optional, Tuple

# Ensure project root is available in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from messaging.telegram_bot import send_telegram

logger = logging.getLogger("messaging.reminders")

MODULE_DIR = Path(__file__).resolve().parent
REMINDERS_FILE = MODULE_DIR / "reminders.json"

_worker_thread: Optional[threading.Thread] = None
_stop_event = threading.Event()
_reminders_lock = threading.Lock()


def load_reminders() -> List[Dict[str, Any]]:
    """Load reminders from messaging/reminders.json safely.

    Returns:
        List[Dict[str, Any]]: List of reminder entries.
    """
    with _reminders_lock:
        if not REMINDERS_FILE.is_file():
            return []
        try:
            with open(REMINDERS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except Exception as exc:
            logger.error("Failed to load reminders from %s: %s", REMINDERS_FILE, exc)
            return []


def save_reminders(reminders: List[Dict[str, Any]]) -> bool:
    """Save reminders list to messaging/reminders.json atomically.

    Args:
        reminders: List of reminder records to persist.

    Returns:
        bool: True on success, False otherwise.
    """
    with _reminders_lock:
        try:
            temp_file = REMINDERS_FILE.with_suffix(".tmp")
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(reminders, f, indent=2, ensure_ascii=False)
            temp_file.replace(REMINDERS_FILE)
            return True
        except Exception as exc:
            logger.error("Failed to save reminders to %s: %s", REMINDERS_FILE, exc)
            return False


def parse_when(when: str) -> Tuple[float, str]:
    """Parse 'HH:MM' (24h) or 'in N minutes' into epoch timestamp and readable string.

    Args:
        when: Timing string (e.g. '21:00', '09:30', 'in 5 minutes', 'in 2 min').

    Returns:
        Tuple[float, str]: (target_epoch_seconds, formatted_display_time)

    Raises:
        ValueError: If 'when' format is invalid or unparseable.
    """
    raw = when.strip()
    now = datetime.now()

    # Pattern 1: 'in N minute(s)' / 'in N min(s)'
    in_min_match = re.match(r"^in\s+(\d+(?:\.\d+)?)\s*(?:minute|minutes|min|mins)$", raw, re.IGNORECASE)
    if in_min_match:
        minutes = float(in_min_match.group(1))
        target_dt = now + timedelta(minutes=minutes)
        min_display = int(minutes) if minutes.is_integer() else minutes
        display = f"{target_dt.strftime('%I:%M %p')} (in {min_display} min)"
        return target_dt.timestamp(), display

    # Pattern 2: 'HH:MM' 24-hour time format
    hh_mm_match = re.match(r"^(\d{1,2}):(\d{2})$", raw)
    if hh_mm_match:
        hour = int(hh_mm_match.group(1))
        minute = int(hh_mm_match.group(2))
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValueError(f"Hour must be 0-23 and minute 0-59 in '{when}'")

        target_dt = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        # If target time is earlier today, schedule for tomorrow
        if target_dt <= now:
            target_dt += timedelta(days=1)

        display = target_dt.strftime("%Y-%m-%d %H:%M")
        return target_dt.timestamp(), display

    raise ValueError(
        f"Invalid timing format '{when}'. Please use 'HH:MM' (24h, e.g. '21:00') "
        "or 'in N minutes' (e.g. 'in 5 minutes')."
    )


def set_reminder(when: str, text: str) -> str:
    """Register and persist a new reminder to be sent to Telegram.

    Args:
        when: Target execution time ('HH:MM' or 'in N minutes').
        text: Reminder message text.

    Returns:
        str: Friendly confirmation message with target time.
    """
    try:
        if not text or not str(text).strip():
            return "Please specify reminder text."

        target_epoch, display_time = parse_when(when)

        reminder_entry: Dict[str, Any] = {
            "id": f"rem_{int(time.time() * 1000)}",
            "due_timestamp": target_epoch,
            "display_time": display_time,
            "text": str(text).strip(),
            "created_at": datetime.now().isoformat(),
        }

        reminders = load_reminders()
        reminders.append(reminder_entry)
        # Sort reminders by due timestamp ascending
        reminders.sort(key=lambda r: r.get("due_timestamp", 0))

        if save_reminders(reminders):
            # Ensure background checker thread is active
            ensure_worker_running()
            return f"⏰ Reminder set for {display_time}: '{text.strip()}'"
        else:
            return "Failed to save reminder to disk."

    except ValueError as val_err:
        return f"Could not set reminder: {val_err}"
    except Exception as exc:
        logger.error("Error setting reminder: %s", exc, exc_info=True)
        return f"Unexpected error while setting reminder: {exc}"


def check_due_reminders() -> int:
    """Inspect stored reminders and dispatch any due alerts via Telegram.

    Returns:
        int: Number of reminders dispatched and cleared.
    """
    reminders = load_reminders()
    if not reminders:
        return 0

    now_epoch = time.time()
    due_items: List[Dict[str, Any]] = []
    remaining_items: List[Dict[str, Any]] = []

    for r in reminders:
        if r.get("due_timestamp", 0) <= now_epoch:
            due_items.append(r)
        else:
            remaining_items.append(r)

    if not due_items:
        return 0

    logger.info("Dispatching %d due reminder(s)...", len(due_items))

    for item in due_items:
        reminder_msg = f"⏰ REMINDER: {item.get('text', '')}"
        try:
            send_telegram(reminder_msg)
        except Exception as exc:
            logger.error("Failed to deliver reminder '%s': %s", item.get("text"), exc)

    # Persist updated reminders list (with due items removed)
    save_reminders(remaining_items)
    return len(due_items)


def _reminder_loop(interval: float = 20.0) -> None:
    """Background monitoring loop checking for due reminders every interval seconds."""
    logger.info("Reminder background worker started (polling interval: %g sec).", interval)
    while not _stop_event.is_set():
        try:
            check_due_reminders()
        except Exception as exc:
            logger.error("Error in reminder background loop: %s", exc, exc_info=True)

        _stop_event.wait(interval)
    logger.info("Reminder background worker stopped.")


def start_reminder_worker(interval: float = 20.0) -> threading.Thread:
    """Start the background reminder monitoring thread.

    Args:
        interval: Polling frequency in seconds (default 20.0).

    Returns:
        threading.Thread: Started background daemon thread.
    """
    global _worker_thread
    if _worker_thread is not None and _worker_thread.is_alive():
        return _worker_thread

    _stop_event.clear()
    _worker_thread = threading.Thread(
        target=_reminder_loop,
        kwargs={"interval": interval},
        daemon=True,
        name="JarvisReminderWorker",
    )
    _worker_thread.start()
    return _worker_thread


def stop_reminder_worker() -> None:
    """Signal background worker to stop gracefully."""
    _stop_event.set()
    if _worker_thread is not None and _worker_thread.is_alive():
        _worker_thread.join(timeout=2.0)


def ensure_worker_running() -> None:
    """Start worker daemon if not already executing."""
    if _worker_thread is None or not _worker_thread.is_alive():
        start_reminder_worker()


def verify_reminders() -> bool:
    """Runnable verification test script for parsing and persistence."""
    print("Verifying messaging.reminders...")

    # 1. Test 'in N minutes' parsing
    ts1, disp1 = parse_when("in 2 minutes")
    assert ts1 > time.time(), "Timestamp should be in the future"
    assert "min" in disp1.lower(), "Display string mismatch"

    # 2. Test 'HH:MM' parsing
    ts2, disp2 = parse_when("21:00")
    assert ts2 > 0, "HH:MM parsing failed"

    # 3. Test persistence roundtrip
    test_text = f"Test reminder at {time.time()}"
    res = set_reminder("in 10 minutes", test_text)
    assert "Reminder set for" in res, f"set_reminder failed: {res}"

    active_reminders = load_reminders()
    matching = [r for r in active_reminders if r.get("text") == test_text]
    assert len(matching) > 0, "Reminder was not found in reminders.json"

    # Clean up test reminder
    cleaned = [r for r in active_reminders if r.get("text") != test_text]
    save_reminders(cleaned)

    print("[PASS] messaging.reminders verified successfully!")
    return True


if __name__ == "__main__":
    success = verify_reminders()
    sys.exit(0 if success else 1)
