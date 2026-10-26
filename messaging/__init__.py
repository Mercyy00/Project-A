"""Messaging module for Project JARVIS.

Handles Telegram bot communications, owner-only authorization,
message routing, command dispatching, document delivery, tools,
WhatsApp messaging with contact book verification, persistent reminders,
WhatsApp file sharing, voice notes, inline confirmations,
and autonomous tool dispatch for JARVIS ReAct Brain.
"""

from messaging.telegram_bot import (
    get_bot_token,
    get_owner_id,
    send_telegram,
    send_telegram_with_confirmation,
    start_bot,
    split_message,
    is_allowed_path,
)
from messaging.tools import (
    SendTelegramTool,
    SearchWhatsAppContactsTool,
    SendWhatsAppTool,
    SendWhatsAppFileTool,
    SetReminderTool,
    ListRemindersTool,
    TOOLS,
)
from messaging.contacts import load_contacts, load_saved_contacts, find_contact
from messaging.whatsapp import send_whatsapp, share_whatsapp_file
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
    "send_telegram_with_confirmation",
    "start_bot",
    "split_message",
    "is_allowed_path",
    "SendTelegramTool",
    "SearchWhatsAppContactsTool",
    "SendWhatsAppTool",
    "SendWhatsAppFileTool",
    "SetReminderTool",
    "ListRemindersTool",
    "TOOLS",
    "load_contacts",
    "load_saved_contacts",
    "find_contact",
    "send_whatsapp",
    "share_whatsapp_file",
    "set_reminder",
    "load_reminders",
    "save_reminders",
    "parse_when",
    "check_due_reminders",
    "start_reminder_worker",
    "stop_reminder_worker",
]
