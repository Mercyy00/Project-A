"""Contacts management module for JARVIS Messaging (Trupti - Day 6).

Loads contacts from messaging/contacts.json (or falls back to contacts.example.json)
and provides case-insensitive, whitespace-agnostic contact phone lookup.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
import re
import sys
from typing import Dict, Optional

logger = logging.getLogger("messaging.contacts")

MODULE_DIR = Path(__file__).resolve().parent
CONTACTS_REAL_FILE = MODULE_DIR / "contacts.json"
CONTACTS_EXAMPLE_FILE = MODULE_DIR / "contacts.example.json"


def load_contacts() -> Dict[str, str]:
    """Load saved contacts from contacts.json if present, else contacts.example.json.

    Returns:
        Dict[str, str]: Dictionary mapping contact name to international phone number.
    """
    try:
        target_file = CONTACTS_REAL_FILE if CONTACTS_REAL_FILE.is_file() else CONTACTS_EXAMPLE_FILE
        if not target_file.is_file():
            logger.warning("No contacts file found at %s or %s", CONTACTS_REAL_FILE, CONTACTS_EXAMPLE_FILE)
            return {}

        with open(target_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                # Ensure all keys and values are clean strings
                return {str(k).strip(): str(v).strip() for k, v in data.items()}
            logger.error("Contacts file format invalid (expected dictionary): %s", target_file)
            return {}
    except Exception as exc:
        logger.error("Failed to load contacts: %s", exc, exc_info=True)
        return {}


def _normalize_name(name: str) -> str:
    """Normalize contact name by removing whitespace and lowercasing."""
    return re.sub(r"\s+", "", str(name or "")).lower()


def find_contact(name: str) -> Optional[str]:
    """Find a phone number by contact name, case-insensitively and ignoring spaces.

    Args:
        name: Name or alias of the contact to find (e.g. 'jayesh', 'Jayesh ', 'JAYESH').

    Returns:
        Optional[str]: E.164 phone number string if found, otherwise None.
    """
    try:
        if not name or not str(name).strip():
            return None

        clean_query = _normalize_name(name)
        contacts = load_contacts()

        for contact_name, phone in contacts.items():
            if _normalize_name(contact_name) == clean_query:
                return phone

        return None
    except Exception as exc:
        logger.error("Error finding contact for query '%s': %s", name, exc)
        return None


def verify_contacts() -> bool:
    """Runnable verification test for contacts lookup logic."""
    print("Verifying messaging.contacts...")
    contacts = load_contacts()
    assert len(contacts) > 0, "Failed to load any contacts"
    assert "Jayesh" in contacts or any("jayesh" in k.lower() for k in contacts), "Sample contact missing"

    # Test case-insensitivity and whitespace resilience
    phone1 = find_contact("Jayesh")
    phone2 = find_contact("  jayesh  ")
    phone3 = find_contact("JAYESH")
    assert phone1 is not None and phone1 == phone2 == phone3, "find_contact normalization failed"

    # Test unknown contact
    unknown = find_contact("NonExistentUser12345")
    assert unknown is None, "Unknown contact should return None"

    print("[PASS] messaging.contacts verified successfully!")
    return True


if __name__ == "__main__":
    success = verify_contacts()
    sys.exit(0 if success else 1)
