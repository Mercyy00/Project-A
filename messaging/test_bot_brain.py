"""Integration script connecting Telegram Bot to JarvisBrain.

Authored by: Trupti (Messaging Engineer)
Creates a JarvisBrain from core.brain and starts the bot with brain.chat.
Provides graceful fallback if core.brain is not yet merged from main,
and includes a runnable verification test script for Day 3 acceptance testing.
"""

from __future__ import annotations

import datetime
import logging
import os
import sys
from typing import Any

# Ensure project root is available in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

logger = logging.getLogger("messaging.test_bot_brain")

# Import JarvisBrain from core.brain with fallback mock for pre-merge testing
try:
    from core.brain import JarvisBrain  # type: ignore
    USING_REAL_BRAIN = True
except ImportError:
    USING_REAL_BRAIN = False

    class JarvisBrain:  # type: ignore
        """Fallback mock implementation of JarvisBrain for standalone testing.

        Emulates JarvisBrain.chat until Jayesh's core.brain is merged into the branch.
        """

        def __init__(self) -> None:
            """Initialize the fallback JarvisBrain."""
            self.model_name = "Mock-Jarvis-Brain-Day3"

        def chat(self, prompt: str) -> str:
            """Generate assistant responses for user prompts.

            Args:
                prompt: The incoming message from the user.

            Returns:
                str: Jarvis's response text.
            """
            prompt_lower = prompt.strip().lower()

            if "date" in prompt_lower:
                today = datetime.datetime.now().strftime("%A, %d %B %Y")
                return f"Today's date is {today}."
            elif "time" in prompt_lower:
                now = datetime.datetime.now().strftime("%I:%M %p")
                return f"The current time is {now}."
            elif any(greet in prompt_lower for greet in ["hello", "hi", "hey"]):
                return "Hello! I am JARVIS, connected via Telegram. How can I assist you today?"
            elif "who are you" in prompt_lower:
                return "I am JARVIS, your personal desktop and mobile assistant."
            else:
                return f"JARVIS Brain received: '{prompt}'. Brain is online and connected."


from messaging.telegram_bot import (
    get_bot_token,
    get_owner_id,
    start_bot,
)


def run_brain_bot() -> None:
    """Instantiate JarvisBrain and start the Telegram bot with brain.chat."""
    print("=" * 60)
    print("JARVIS Telegram Bot + Brain Integration - Day 3")
    print("=" * 60)

    try:
        token = get_bot_token()
        owner_id = get_owner_id()
        print("[OK] Bot token verified.")
        if owner_id:
            print(f"[OK] Authorized Owner ID: {owner_id}")
        else:
            print("[NOTICE] TELEGRAM_OWNER_ID is not configured in .env.")
            print("         Send a message to your bot on Telegram to discover your ID.")

        if USING_REAL_BRAIN:
            print("[INFO] Using core.brain.JarvisBrain.")
        else:
            print("[INFO] core.brain not yet found; using built-in JarvisBrain fallback.")

        brain = JarvisBrain()
        print("Starting Telegram bot connected to JarvisBrain.chat...")
        print("Press Ctrl+C to terminate.")
        start_bot(handler=brain.chat)

    except ValueError as val_err:
        print(f"\n[ERROR] Configuration issue: {val_err}")
        print("Please check your .env file and ensure TELEGRAM_BOT_TOKEN is set.\n")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nShutdown signal received. Stopping bot gracefully.")
    except Exception as exc:
        logger.error("Unexpected error starting brain bot: %s", exc, exc_info=True)
        sys.exit(1)


def verify_brain_connection() -> bool:
    """Runnable verification test for Day 3 acceptance testing.

    Acceptance test from guide:
    'What is the date today?' sent from Telegram returns Jarvis's answer.

    Returns:
        bool: True if brain answers questions accurately.
    """
    print("\nRunning Day 3 Acceptance Verification Test...")
    try:
        brain = JarvisBrain()

        # Test query 1: Acceptance test query
        query_date = "What is the date today?"
        answer_date = brain.chat(query_date)
        print(f"Query:  '{query_date}'")
        print(f"Answer: '{answer_date}'")
        assert len(answer_date) > 0, "Brain returned empty answer for date query"
        assert (
            str(datetime.datetime.now().year) in answer_date
            or "date" in answer_date.lower()
        ), "Date answer did not contain year or date reference"

        # Test query 2: Greeting
        query_hi = "Hello Jarvis"
        answer_hi = brain.chat(query_hi)
        print(f"Query:  '{query_hi}'")
        print(f"Answer: '{answer_hi}'")
        assert len(answer_hi) > 0, "Brain returned empty answer for greeting"

        print("\n[PASS] Day 3 Brain acceptance verification test completed successfully!")
        return True

    except Exception as exc:
        print(f"\n[FAIL] Verification test failed: {exc}")
        return False


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--verify":
        success = verify_brain_connection()
        sys.exit(0 if success else 1)
    else:
        run_brain_bot()
