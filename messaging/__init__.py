"""Messaging module for Project JARVIS.

Handles Telegram bot communications, owner-only authorization,
message routing, command dispatching, document delivery, and tools.
"""

from messaging.telegram_bot import (
    get_bot_token,
    get_owner_id,
    send_telegram,
    start_bot,
    split_message,
    is_allowed_path,
)
from messaging.tools import SendTelegramTool, TOOLS

__all__ = [
    "get_bot_token",
    "get_owner_id",
    "send_telegram",
    "start_bot",
    "split_message",
    "is_allowed_path",
    "SendTelegramTool",
    "TOOLS",
]
