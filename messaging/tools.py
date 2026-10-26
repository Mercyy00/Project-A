"""Tools module for JARVIS Messaging (Trupti - Days 4, 8 & 9).

Exports BaseTool-compliant tools for function calling and autonomous integration
with Jarvis Brain and tool registry:
- SendTelegramTool: Remote messaging and document dispatch to the owner on Telegram.
- SearchWhatsAppContactsTool: Search saved verified contacts without leaking numbers.
- SendWhatsAppTool: Verified contacts messaging via WhatsApp automation.
- SendWhatsAppFileTool: Verified contacts document/image file sharing via WhatsApp.
- SetReminderTool: Persistent reminder scheduling with Telegram dispatch.
- ListRemindersTool: List all active pending reminders.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
import sys
import time
from typing import Any, Dict, List, Optional

# Ensure project root is prioritized in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if sys.path[0] != PROJECT_ROOT:
    sys.path.insert(0, PROJECT_ROOT)

from tools.base import BaseTool, ToolResult
from messaging.telegram_bot import send_telegram
from messaging.whatsapp import send_whatsapp, share_whatsapp_file
from messaging.contacts import load_saved_contacts, find_contact
from messaging.reminders import set_reminder, load_reminders

logger = logging.getLogger("messaging.tools")


class SendTelegramTool(BaseTool):
    """Tool allowing JARVIS Brain to autonomously send messages and attachments to the owner on Telegram."""

    name: str = "send_telegram"
    description: str = (
        "Send a message or document attachment to the owner's Telegram. Use this whenever the user asks "
        "to send a message, alert, notification, or file/document to their phone."
    )

    def run(self, text: str = "", file_path: str = "", **kwargs: Any) -> ToolResult:
        """Execute the tool by calling send_telegram with the provided text and optional file attachment.

        Args:
            text: The message string to deliver to the owner's Telegram.
            file_path: Optional file path of a document/photo in workspace/ to attach.

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
                att_msg = f" with attachment '{os.path.basename(attachment)}'" if attachment else ""
                return ToolResult(
                    success=True,
                    data={"text": cleaned_text, "file_path": attachment},
                    message=f"Telegram message sent to owner: '{preview}'{att_msg}.",
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

    def run(self, query: str = "", **kwargs: Any) -> ToolResult:
        """Return saved contact names matching a query."""
        try:
            clean_query = str(query or "").strip().casefold()
            if not clean_query:
                return ToolResult(success=False, message="A contact name or search term is required.")
            saved = load_saved_contacts()
            names = sorted(
                name for name in saved
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
    """Tool allowing JARVIS Brain to autonomously send WhatsApp text messages to saved contacts."""

    name: str = "send_whatsapp"
    description: str = (
        "Send a WhatsApp text message to a contact in the user's saved verified contacts "
        "(e.g., 'Jayesh', 'MyPhone'). For safety, messages are only sent to recognized contacts."
    )

    def run(self, contact: str = "", message: str = "", **kwargs: Any) -> ToolResult:
        """Execute WhatsApp text dispatch to a verified contact.

        Args:
            contact: Name of the recipient in saved contacts.
            message: Body text of the WhatsApp message.

        Returns:
            ToolResult: Execution outcome with safety guarantees.
        """
        try:
            if not contact or not str(contact).strip():
                return ToolResult(
                    success=False,
                    data=None,
                    message="Recipient 'contact' name is required.",
                )
            if not message or not str(message).strip():
                return ToolResult(
                    success=False,
                    data=None,
                    message="Cannot send an empty WhatsApp message. Please provide 'message'.",
                )

            contact_clean = str(contact).strip()
            message_clean = str(message).strip()
            outcome = send_whatsapp(contact=contact_clean, message=message_clean)

            if "not in your saved contacts" in outcome or "Failed to send" in outcome:
                return ToolResult(
                    success=False,
                    data={"contact": contact_clean, "outcome": outcome},
                    message=outcome,
                )

            return ToolResult(
                success=True,
                data={"contact": contact_clean, "message": message_clean},
                message=outcome,
            )

        except Exception as exc:
            logger.error("Exception in SendWhatsAppTool.run: %s", exc, exc_info=True)
            return ToolResult(
                success=False,
                data=None,
                message=f"Error executing SendWhatsAppTool: {exc}",
            )

    def get_schema(self) -> Dict[str, Any]:
        """Returns JSON schema for LLM function calling."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "contact": {
                        "type": "string",
                        "description": "Name of the recipient contact saved in contacts list (e.g. 'Jayesh').",
                    },
                    "message": {
                        "type": "string",
                        "description": "The message body to deliver to the contact on WhatsApp.",
                    },
                },
                "required": ["contact", "message"],
            },
        }


class SendWhatsAppFileTool(BaseTool):
    """Tool allowing JARVIS Brain to share files, documents, and images via WhatsApp."""

    name: str = "send_whatsapp_file"
    description: str = (
        "Send a document, PDF, report, or image file to a verified saved WhatsApp contact. "
        "Accepts 'contact', 'file_path', and optional 'caption'."
    )

    def run(self, contact: str = "", file_path: str = "", caption: str = "", **kwargs: Any) -> ToolResult:
        """Share a file with a verified WhatsApp contact.

        Args:
            contact: Name of the verified contact in saved contacts.
            file_path: Path of the file to share (e.g. 'workspace/report.pdf').
            caption: Optional caption accompanying the file.

        Returns:
            ToolResult: Execution outcome with delivery status.
        """
        try:
            if not contact or not str(contact).strip():
                return ToolResult(success=False, message="Recipient 'contact' name is required.")
            if not file_path or not str(file_path).strip():
                return ToolResult(success=False, message="Please provide a valid 'file_path' to share.")

            contact_clean = str(contact).strip()
            file_clean = str(file_path).strip()
            caption_clean = str(caption).strip() if caption else None

            outcome = share_whatsapp_file(contact=contact_clean, file_path=file_clean, caption=caption_clean)

            if "not in your saved contacts" in outcome or "not found" in outcome or "Failed" in outcome:
                return ToolResult(
                    success=False,
                    data={"contact": contact_clean, "file_path": file_clean},
                    message=outcome,
                )

            return ToolResult(
                success=True,
                data={"contact": contact_clean, "file_path": file_clean, "caption": caption_clean},
                message=outcome,
            )

        except Exception as exc:
            logger.error("Exception in SendWhatsAppFileTool.run: %s", exc, exc_info=True)
            return ToolResult(
                success=False,
                data=None,
                message=f"Error executing SendWhatsAppFileTool: {exc}",
            )

    def get_schema(self) -> Dict[str, Any]:
        """Returns JSON schema for LLM function calling."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "contact": {
                        "type": "string",
                        "description": "Name of the saved contact to receive the file (e.g. 'Jayesh').",
                    },
                    "file_path": {
                        "type": "string",
                        "description": "Path to the file to be shared (e.g. 'workspace/report.pdf').",
                    },
                    "caption": {
                        "type": "string",
                        "description": "Optional text caption accompanying the file.",
                    },
                },
                "required": ["contact", "file_path"],
            },
        }


class SetReminderTool(BaseTool):
    """Tool allowing JARVIS Brain to schedule persistent reminders."""

    name: str = "set_reminder"
    description: str = (
        "Schedule a reminder that alerts the user on Telegram at a specified time. "
        "Accepts 'when' ('HH:MM' 24h format like '18:30' or 'in N minutes' like 'in 15 minutes') and 'text'."
    )

    def run(self, when: str = "", text: str = "", **kwargs: Any) -> ToolResult:
        """Execute reminder registration.

        Args:
            when: When the reminder should trigger ('HH:MM' or 'in N minutes').
            text: Message to be delivered when the reminder fires.

        Returns:
            ToolResult: Execution outcome with persistence details.
        """
        try:
            if not when or not str(when).strip():
                return ToolResult(
                    success=False,
                    data=None,
                    message="Please provide a trigger time 'when' (e.g. 'in 10 minutes' or '17:30').",
                )
            if not text or not str(text).strip():
                return ToolResult(
                    success=False,
                    data=None,
                    message="Please provide reminder 'text'.",
                )

            when_clean = str(when).strip()
            text_clean = str(text).strip()
            outcome = set_reminder(when=when_clean, text=text_clean)

            if "Could not set reminder" in outcome or "Failed" in outcome:
                return ToolResult(
                    success=False,
                    data={"when": when_clean, "text": text_clean},
                    message=outcome,
                )

            return ToolResult(
                success=True,
                data={"when": when_clean, "text": text_clean},
                message=outcome,
            )

        except Exception as exc:
            logger.error("Error in SetReminderTool.run: %s", exc, exc_info=True)
            return ToolResult(
                success=False,
                data=None,
                message=f"Error executing SetReminderTool: {exc}",
            )

    def get_schema(self) -> Dict[str, Any]:
        """Returns JSON schema for LLM function calling."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "when": {
                        "type": "string",
                        "description": (
                            "Timing for the reminder. Use 'HH:MM' 24h format (e.g. '18:30') "
                            "or relative time (e.g. 'in 15 minutes')."
                        ),
                    },
                    "text": {
                        "type": "string",
                        "description": "Content of the reminder notification.",
                    },
                },
                "required": ["when", "text"],
            },
        }


class ListRemindersTool(BaseTool):
    """Tool allowing JARVIS Brain to query active pending reminders."""

    name: str = "list_reminders"
    description: str = "List all active, pending reminders currently scheduled."

    def run(self, **kwargs: Any) -> ToolResult:
        """Inspect and return scheduled reminders."""
        try:
            reminders = load_reminders()
            if not reminders:
                return ToolResult(
                    success=True,
                    data=[],
                    message="No pending reminders found. Your schedule is clear.",
                )

            now_epoch = time.time()
            active = [r for r in reminders if r.get("due_timestamp", 0) > now_epoch]
            if not active:
                return ToolResult(
                    success=True,
                    data=[],
                    message="No active upcoming reminders found.",
                )

            lines = [
                f"- [{r.get('display_time', 'Scheduled')}]: {r.get('text', '')}"
                for r in active
            ]
            msg = f"You have {len(active)} active reminder(s):\n" + "\n".join(lines)

            return ToolResult(
                success=True,
                data=active,
                message=msg,
            )

        except Exception as exc:
            logger.error("Exception in ListRemindersTool.run: %s", exc, exc_info=True)
            return ToolResult(
                success=False,
                data=None,
                message=f"Error listing reminders: {exc}",
            )

    def get_schema(self) -> Dict[str, Any]:
        """Returns JSON schema for LLM function calling."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        }


# Canonical exported tools list for Abhijit's registry auto-loader (Catch-Up Plan Section 4 & 7)
TOOLS: List[BaseTool] = [
    SendTelegramTool(),
    SearchWhatsAppContactsTool(),
    SendWhatsAppTool(),
    SendWhatsAppFileTool(),
    SetReminderTool(),
    ListRemindersTool(),
]


def verify_tools() -> bool:
    """Runnable verification test script for messaging tools."""
    print("Verifying messaging.tools (Days 4, 8 & 9)...")

    # 1. Verify SendTelegramTool
    tg_tool = SendTelegramTool()
    assert tg_tool.get_schema()["name"] == "send_telegram"
    assert not tg_tool.run(text="").success

    # 2. Verify SearchWhatsAppContactsTool
    search_tool = SearchWhatsAppContactsTool()
    assert search_tool.get_schema()["name"] == "search_whatsapp_contacts"
    assert not search_tool.run(query="").success

    # 3. Verify SendWhatsAppTool
    wa_tool = SendWhatsAppTool()
    assert wa_tool.get_schema()["name"] == "send_whatsapp"
    assert not wa_tool.run(contact="", message="hello").success
    assert not wa_tool.run(contact="Jayesh", message="").success

    # 4. Verify SendWhatsAppFileTool
    file_tool = SendWhatsAppFileTool()
    assert file_tool.get_schema()["name"] == "send_whatsapp_file"
    assert not file_tool.run(contact="", file_path="sample.pdf").success

    # 5. Verify SetReminderTool
    rem_tool = SetReminderTool()
    assert rem_tool.get_schema()["name"] == "set_reminder"
    assert not rem_tool.run(when="", text="msg").success
    assert not rem_tool.run(when="invalid time", text="msg").success

    # 6. Verify ListRemindersTool
    list_tool = ListRemindersTool()
    assert list_tool.get_schema()["name"] == "list_reminders"
    list_res = list_tool.run()
    assert list_res.success

    print("[PASS] All 6 messaging tools verified successfully.")
    return True


if __name__ == "__main__":
    success = verify_tools()
    sys.exit(0 if success else 1)
