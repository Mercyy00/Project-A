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

logger = logging.getLogger("messaging.tools")


class SendTelegramTool(BaseTool):
    """Tool allowing JARVIS Brain to autonomously send messages to the owner on Telegram."""

    name: str = "send_telegram"
    description: str = (
        "Send a message to the owner's Telegram. Use this whenever the user asks "
        "to send a message, alert, notification, or greeting to their phone."
    )

    def run(self, text: str = "", **kwargs: Any) -> ToolResult:
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
            success = send_telegram(cleaned_text)

            if success:
                preview = cleaned_text if len(cleaned_text) <= 50 else cleaned_text[:47] + "..."
                return ToolResult(
                    success=True,
                    data={"text": cleaned_text},
                    message=f"Telegram message sent to owner: '{preview}'",
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
                    }
                },
                "required": ["text"],
            },
        }


# Export tools list as required by ARCHITECTURE.md and tools.registry
TOOLS: List[BaseTool] = [SendTelegramTool()]


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
