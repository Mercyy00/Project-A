"""Test script for running JARVIS Telegram Echo Bot in a background thread.

Authored by: Trupti (Messaging Engineer)
Starts the bot in a background thread and cleanly stops on Ctrl+C.
Includes runnable verification test mode.
"""

from __future__ import annotations

import logging
import os
import sys
import threading
import time
from typing import Callable, Optional

# Ensure project root is available in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from messaging.telegram_bot import (
    create_bot,
    get_bot_token,
    get_owner_id,
    start_bot,
)

logger = logging.getLogger("messaging.test_bot")


def run_echo_bot_thread(
    handler: Optional[Callable[[str], str]] = None,
    bot_instance: Optional[object] = None,
) -> threading.Thread:
    """Launch the Telegram bot inside a background daemon thread.

    Args:
        handler: Message processing function. Defaults to echo bot.
        bot_instance: Optional mock or existing bot instance.

    Returns:
        threading.Thread: The started daemon thread.
    """
    bot_thread = threading.Thread(
        target=start_bot,
        kwargs={"handler": handler, "bot_instance": bot_instance},
        daemon=True,
        name="TelegramBotThread",
    )
    bot_thread.start()
    return bot_thread


def main() -> None:
    """Run the echo bot in a background thread and wait for Ctrl+C."""
    print("=" * 60)
    print("JARVIS Telegram Echo Bot - Day 2 Runner")
    print("=" * 60)

    try:
        token = get_bot_token()
        owner_id = get_owner_id()
        print("[OK] TELEGRAM_BOT_TOKEN detected.")
        if owner_id:
            print(f"[OK] TELEGRAM_OWNER_ID configured: {owner_id}")
        else:
            print("[NOTICE] TELEGRAM_OWNER_ID is not set yet.")
            print("         Send any message to your bot on Telegram.")
            print("         The console will print your numeric chat ID to put in .env.")
    except ValueError as err:
        print(f"\n[CONFIGURATION ERROR] {err}")
        print("Please edit .env file with your BotFather token before running.\n")
        sys.exit(1)

    print("\nStarting bot in background thread...")
    thread = run_echo_bot_thread()
    print("Bot is running! Press Ctrl+C to stop.")

    try:
        while thread.is_alive():
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nCtrl+C detected. Shutting down echo bot...")
    finally:
        print("Bot process terminated safely.")


def verify_test_bot() -> bool:
    """Verification test script for background thread execution logic.

    Returns:
        bool: True if thread creation and lifecycle logic succeed.
    """
    print("Running verification for messaging/test_bot.py...")

    class DummyBot:
        def __init__(self) -> None:
            self.polling = False

        def message_handler(self, *args, **kwargs):
            def decorator(fn):
                return fn
            return decorator

        def infinity_polling(self, timeout=10, long_polling_timeout=5):
            self.polling = True
            time.sleep(0.2)
            self.polling = False

    dummy = DummyBot()
    thread = run_echo_bot_thread(bot_instance=dummy)
    assert thread.is_alive(), "Thread failed to start"
    thread.join(timeout=2.0)
    assert not thread.is_alive(), "Thread failed to terminate"

    print("[PASS] Background thread lifecycle verified successfully.")
    return True


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--verify":
        verify_test_bot()
    else:
        main()
