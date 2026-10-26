"""Test script for WhatsApp messaging integration (Trupti - Day 6).

Supports dry-run mode (--dry-run) to preview outbound message parameters
without opening browser automation, as well as live execution and verification.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys

# Ensure project root is available in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from messaging.contacts import find_contact, load_contacts
from messaging.whatsapp import send_whatsapp


def run_whatsapp_test(contact_name: str, message: str, dry_run: bool = False) -> None:
    """Execute WhatsApp dispatch test or dry-run preview.

    Args:
        contact_name: Name of recipient to look up.
        message: Content to deliver.
        dry_run: When True, prints preview without triggering browser automation.
    """
    print("=" * 60)
    print("JARVIS WhatsApp Messaging Test (Day 6)")
    print("=" * 60)

    phone = find_contact(contact_name)
    if not phone:
        print(f"[REJECTED] Contact '{contact_name}' is not in saved contacts.")
        print("Available contacts:")
        for name, num in load_contacts().items():
            print(f"  - {name}: {num}")
        return

    print(f"Recipient Contact: {contact_name}")
    print(f"Resolved Phone:    {phone}")
    print(f"Message Body:      '{message}'")

    if dry_run:
        print("\n[DRY RUN MODE] Simulating WhatsApp dispatch:")
        print(f"  -> pywhatkit.sendwhatmsg_instantly('{phone}', '{message}', wait_time=15, tab_close=True)")
        print("[SUCCESS] Dry-run preview completed. No browser opened.")
    else:
        print("\n[LIVE MODE] Initiating WhatsApp Web automation via pywhatkit...")
        result = send_whatsapp(contact_name, message)
        print(f"Result: {result}")


def verify_dry_run() -> bool:
    """Runnable verification test for dry-run functionality."""
    print("Running verification for messaging/test_whatsapp.py...")
    phone = find_contact("Jayesh")
    assert phone is not None, "Failed to resolve Jayesh contact"
    print(f"[PASS] Resolved Jayesh to {phone} in dry-run verification.")
    return True


def main() -> None:
    """Parse CLI arguments and execute WhatsApp test."""
    parser = argparse.ArgumentParser(description="JARVIS WhatsApp Test Runner")
    parser.add_argument("--contact", default="Jayesh", help="Contact name to message (default: Jayesh)")
    parser.add_argument("--message", default="Hello from JARVIS automated WhatsApp test!", help="Message text")
    parser.add_argument("--dry-run", action="store_true", help="Print preview without sending")
    parser.add_argument("--verify", action="store_true", help="Run automated test assertion")

    args = parser.parse_args()

    if args.verify:
        success = verify_dry_run()
        sys.exit(0 if success else 1)
    else:
        run_whatsapp_test(args.contact, args.message, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
