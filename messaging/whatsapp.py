"""WhatsApp messaging module for Project JARVIS (Trupti - Day 6).

Sends WhatsApp messages to pre-saved verified contacts via pywhatkit.
Enforces contact book validation: never sends to unverified or unknown contacts.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
import sys
from typing import Optional

# Ensure project root is prioritized in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from messaging.contacts import find_contact

logger = logging.getLogger("messaging.whatsapp")


def send_whatsapp(contact: str, message: str) -> str:
    """Send a WhatsApp message to a saved contact using pywhatkit.

    Strict security & reliability rules:
    1. Looks up the contact in saved contacts.
    2. If contact is unknown, returns a polite refusal message without sending.
    3. Never sends to any phone number not listed in the contacts file.
    4. Never raises an unhandled exception; returns clean status string.
    5. Uses pywhatkit.sendwhatmsg_instantly with ~15s wait and tab closing.

    Args:
        contact: Name of the contact to find in saved contacts.
        message: The message body to deliver via WhatsApp.

    Returns:
        str: Human-readable execution outcome.
    """
    try:
        if not contact or not str(contact).strip():
            return "Please provide a valid contact name."

        if not message or not str(message).strip():
            return "Cannot send an empty WhatsApp message."

        contact_clean = str(contact).strip()
        message_clean = str(message).strip()

        # Contact validation check
        phone_number: Optional[str] = find_contact(contact_clean)
        if not phone_number:
            logger.warning("WhatsApp send refused: Contact '%s' is not in saved contacts.", contact_clean)
            return (
                f"Contact '{contact_clean}' is not in your saved contacts list. "
                "WhatsApp message was not sent for safety."
            )

        logger.info("Queuing WhatsApp message to %s (%s)...", contact_clean, phone_number)

        try:
            import pywhatkit

            # pywhatkit.sendwhatmsg_instantly sends message with ~15 sec wait and closes the tab
            pywhatkit.sendwhatmsg_instantly(
                phone_no=phone_number,
                message=message_clean,
                wait_time=15,
                tab_close=True,
                close_time=3,
            )
            return f"WhatsApp message successfully queued for {contact_clean} ({phone_number})."
        except Exception as api_err:
            logger.error("pywhatkit dispatch error: %s", api_err, exc_info=True)
            return f"Failed to send WhatsApp message via web automation: {api_err}"

    except Exception as exc:
        logger.error("Unexpected error in send_whatsapp: %s", exc, exc_info=True)
        return f"An error occurred while attempting to send WhatsApp message: {exc}"


def verify_whatsapp() -> bool:
    """Runnable verification test for WhatsApp dispatch logic and contact guard."""
    print("Verifying messaging.whatsapp...")

    # 1. Test unknown contact guard
    unknown_result = send_whatsapp("UnknownPerson99", "Hello there")
    assert "not in your saved contacts" in unknown_result, "Unknown contact should be refused"

    # 2. Test empty message guard
    empty_result = send_whatsapp("Jayesh", "")
    assert "empty" in empty_result.lower(), "Empty message should be rejected"

    print("[PASS] messaging.whatsapp safety guards verified successfully!")
    return True


if __name__ == "__main__":
    success = verify_whatsapp()
    sys.exit(0 if success else 1)
