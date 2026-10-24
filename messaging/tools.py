"""Tools module for JARVIS Messaging (Trupti - Day 4).

Exports SendTelegramTool inheriting from BaseTool for function calling
and integration with Jarvis Brain and tool registry.
"""

from __future__ import annotations

import logging
import os
import sys
from typing import Any, Dict, List

# Ensure project root is prioritized in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if sys.path[0] != PROJECT_ROOT:
    sys.path.insert(0, PROJECT_ROOT)

from tools.base import BaseTool, ToolResult
from messaging.telegram_bot import send_telegram
from messaging.whatsapp import send_whatsapp
from messaging.contacts import load_saved_contacts

logger = logging.getLogger("messaging.tools")


class SendTelegramTool(BaseTool):
    """Tool allowing JARVIS Brain to autonomously send messages to the owner on Telegram."""

    name: str = "send_telegram"
    description: str = (
        "Send a message to the owner's Telegram. Use this whenever the user asks "
        "to send a message, alert, notification, or greeting to their phone."
    )

    def run(self, text: str = "", file_path: str = "", **kwargs: Any) -> ToolResult:
        """Execute the tool by calling send_telegram with the provided text.

        Args:
            text: The message string to deliver to the owner's Telegram.

        Returns:
            ToolResult: Standardized tool response with execution status and message.
        """
        try:
            if not text or not str(text).strip():
                return ToolResult(
                    success=False,
                    data=None,
                    message="Cannot send an empty Telegram message. Please provide 'text'.",
                )

            cleaned_text = str(text).strip()
            attachment = str(file_path or "").strip() or None
            success = send_telegram(cleaned_text, file_path=attachment)

            if success:
                preview = cleaned_text if len(cleaned_text) <= 50 else cleaned_text[:47] + "..."
                return ToolResult(
                    success=True,
                    data={"text": cleaned_text, "file_path": attachment},
                    message=(
                        f"Telegram message sent to owner: '{preview}'"
                        + (f" with attachment '{os.path.basename(attachment)}'." if attachment else ".")
                    ),
                )
            else:
                return ToolResult(
                    success=False,
                    data=None,
                    message=(
                        "Failed to send Telegram message. "
                        "Please verify TELEGRAM_BOT_TOKEN and TELEGRAM_OWNER_ID in .env."
                    ),
                )

        except Exception as exc:
            logger.error("Exception in SendTelegramTool.run: %s", exc, exc_info=True)
            return ToolResult(
                success=False,
                data=None,
                message=f"Error executing SendTelegramTool: {exc}",
            )

    def get_schema(self) -> Dict[str, Any]:
        """Returns JSON schema for LLM automatic function calling."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "The exact message content to send to the owner's phone on Telegram.",
                    },
                    "file_path": {
                        "type": "string",
                        "description": "Optional existing file path to attach, such as a generated PDF in workspace/.",
                    },
                },
                "required": ["text"],
            },
        }


class SearchWhatsAppContactsTool(BaseTool):
    """Search locally saved WhatsApp contacts without exposing their phone numbers."""

    name: str = "search_whatsapp_contacts"
    description: str = "Search the user's locally saved, verified WhatsApp contacts by name."

    def run(self, query: str, **kwargs: Any) -> ToolResult:
        """Return saved contact names matching a query."""
        try:
            clean_query = str(query or "").strip().casefold()
            if not clean_query:
                return ToolResult(success=False, message="A contact name or search term is required.")
            names = sorted(
                name for name in load_saved_contacts()
                if clean_query in name.casefold()
            )
            if not names:
                return ToolResult(success=True, data={"contacts": []}, message="No saved contacts matched.")
            return ToolResult(
                success=True,
                data={"contacts": names},
                message="Saved contact matches: " + ", ".join(names),
            )
        except Exception as exc:
            logger.exception("Contact search failed: %s", exc)
            return ToolResult(success=False, message=f"Could not search saved contacts: {exc}")

    def get_schema(self) -> Dict[str, Any]:
        """Return the function-calling schema."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string", "description": "Name to search for."}},
                "required": ["query"],
            },
        }


class SendWhatsAppTool(BaseTool):
    """Send a text message to a verified saved WhatsApp contact."""

    name: str = "send_whatsapp"
    description: str = (
        "Send a WhatsApp text message to a contact in the user's saved verified contacts. "
        "The exact message and contact will require user confirmation before delivery."
    )

    def run(self, contact: str, message: str, **kwargs: Any) -> ToolResult:
        """Dispatch a WhatsApp message only to a known saved contact."""
        try:
            if not contact or not str(contact).strip():
                return ToolResult(success=False, message="A saved contact name is required.")
            if not message or not str(message).strip():
                return ToolResult(success=False, message="Cannot send an empty WhatsApp message.")
            outcome = send_whatsapp(str(contact).strip(), str(message).strip())
            succeeded = outcome.startswith("WhatsApp message successfully queued")
            safe_outcome = (
                f"WhatsApp message queued for {str(contact).strip()}."
                if succeeded else outcome
            )
            return ToolResult(
                success=succeeded,
                data={"contact": str(contact).strip(), "message": str(message).strip()},
                message=safe_outcome,
            )
        except Exception as exc:
            logger.exception("WhatsApp message preparation failed: %s", exc)
            return ToolResult(success=False, message=f"Could not send WhatsApp message: {exc}")

    def get_schema(self) -> Dict[str, Any]:
        """Return the function-calling schema."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "contact": {"type": "string", "description": "Exact saved contact name."},
                    "message": {"type": "string", "description": "Exact message body to send."},
                },
                "required": ["contact", "message"],
            },
        }


# Export tools list as required by ARCHITECTURE.md and tools.registry
TOOLS: List[BaseTool] = [SendTelegramTool(), SearchWhatsAppContactsTool(), SendWhatsAppTool()]


def verify_tools() -> bool:
    """Runnable verification test script for SendTelegramTool."""
    print("Verifying messaging.tools...")
    tool = SendTelegramTool()
    schema = tool.get_schema()
    assert schema["name"] == "send_telegram", "Schema name mismatch"
    assert "text" in schema["parameters"]["properties"], "Missing text property in schema"

    # Test empty input handling
    res_empty = tool.run(text="")
    assert not res_empty.success, "Empty text should fail"

    print("[PASS] SendTelegramTool schema and validation verified successfully.")
    return True


if __name__ == "__main__":
    success = verify_tools()
    sys.exit(0 if success else 1)
