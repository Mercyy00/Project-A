"""Messaging module for Project JARVIS.

Handles Telegram bot communications, owner-only authorization,
message routing, command dispatching, document delivery, tools,
WhatsApp messaging with contact book verification, persistent reminders,
and autonomous tool dispatch for JARVIS ReAct Brain.
"""

from messaging.telegram_bot import (
    get_bot_token,
    get_owner_id,
    send_telegram,
    start_bot,
    split_message,
    is_allowed_path,
)
from messaging.tools import (
    SendTelegramTool,
    SendWhatsAppTool,
    SetReminderTool,
    ListRemindersTool,
    TOOLS,
)
from messaging.contacts import load_contacts, find_contact
from messaging.whatsapp import send_whatsapp
from messaging.reminders import (
    set_reminder,
    load_reminders,
    save_reminders,
    parse_when,
    check_due_reminders,
    start_reminder_worker,
    stop_reminder_worker,
)

__all__ = [
    "get_bot_token",
    "get_owner_id",
    "send_telegram",
    "start_bot",
    "split_message",
    "is_allowed_path",
    "SendTelegramTool",
    "SendWhatsAppTool",
    "SetReminderTool",
    "ListRemindersTool",
    "TOOLS",
    "load_contacts",
    "find_contact",
    "send_whatsapp",
    "set_reminder",
    "load_reminders",
    "save_reminders",
    "parse_when",
    "check_due_reminders",
    "start_reminder_worker",
    "stop_reminder_worker",
]
