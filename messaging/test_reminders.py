"""Test script for persistent Telegram reminders (Trupti - Day 7).

Tests scheduling, persistence across restarts, and background polling.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
import time

# Ensure project root is available in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from messaging.reminders import (
    check_due_reminders,
    load_reminders,
    parse_when,
    save_reminders,
    set_reminder,
    start_reminder_worker,
    verify_reminders,
)


def run_interactive_reminder_test(when: str, text: str) -> None:
    """Set a reminder and demonstrate background dispatch."""
    print("=" * 60)
    print("JARVIS Telegram Reminders Test (Day 7)")
    print("=" * 60)

    print(f"Scheduling reminder: when='{when}', text='{text}'")
    result = set_reminder(when, text)
    print(f"Result: {result}\n")

    print("Currently persisted reminders in reminders.json:")
    reminders = load_reminders()
    for idx, r in enumerate(reminders, 1):
        print(f"  {idx}. [{r.get('display_time')}] {r.get('text')}")

    print("\nStarting background worker. Press Ctrl+C to stop.")
    worker = start_reminder_worker(interval=5.0)

    try:
        while True:
            time.sleep(1.0)
    except KeyboardInterrupt:
        print("\nStopping reminder worker gracefully.")


def main() -> None:
    """Entry point with CLI argument parsing."""
    parser = argparse.ArgumentParser(description="JARVIS Reminders Test Runner")
    parser.add_argument("--when", default="in 2 minutes", help="When to trigger (e.g. 'in 2 minutes' or '21:00')")
    parser.add_argument("--text", default="Check on project deployment status", help="Reminder text")
    parser.add_argument("--verify", action="store_true", help="Run automated test suite")

    args = parser.parse_args()

    if args.verify:
        success = verify_reminders()
        sys.exit(0 if success else 1)
    else:
        run_interactive_reminder_test(args.when, args.text)


if __name__ == "__main__":
    main()
