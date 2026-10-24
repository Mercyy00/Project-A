"""Comprehensive unit and integration test suite for JARVIS Messaging.

Authored by: Trupti (Messaging Engineer)
Covers Day 1 through Day 5 deliverables:
- Environment variable loading and token protection
- Message splitting for Telegram's 4096-character limit
- Owner-only authorization filtering
- send_telegram() sending text, photos (.png/.jpg/.jpeg), and documents
- Directory restriction (workspace/ or temp_*) and 45 MB size limit
- Bot commands: /start, /help, /status, /screenshot
- Incoming photo handler saving to workspace/ and replying 'Saved'
- SendTelegramTool inheriting BaseTool for Jarvis Brain execution
- Day 3-5 acceptance tests
"""

from __future__ import annotations

import os
from pathlib import Path
import sys
import tempfile
import time
from typing import Any, List
from unittest.mock import MagicMock, patch

import pytest

# Ensure project root is available in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from messaging.telegram_bot import (
    TELEGRAM_MAX_MESSAGE_LENGTH,
    get_bot_token,
    get_owner_id,
    is_allowed_path,
    send_telegram,
    split_message,
    start_bot,
)
from messaging.test_bot_brain import JarvisBrain
from messaging.tools import SendTelegramTool, TOOLS


# ==============================================================================
# 1. Message Splitting Tests
# ==============================================================================

def test_split_message_short() -> None:
    """Short message should return a single chunk without alterations."""
    text = "Hello JARVIS"
    chunks = split_message(text)
    assert len(chunks) == 1
    assert chunks[0] == text


def test_split_message_empty() -> None:
    """Empty string should return a list with a single empty string."""
    chunks = split_message("")
    assert chunks == [""]


def test_split_message_exact_limit() -> None:
    """Message of exact max_length characters should not be split."""
    text = "X" * TELEGRAM_MAX_MESSAGE_LENGTH
    chunks = split_message(text, max_length=TELEGRAM_MAX_MESSAGE_LENGTH)
    assert len(chunks) == 1
    assert len(chunks[0]) == TELEGRAM_MAX_MESSAGE_LENGTH


def test_split_message_long_text() -> None:
    """Message longer than max_length should be cleanly chunked."""
    max_len = 100
    long_text = "Word " * 200
    chunks = split_message(long_text, max_length=max_len)

    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk) <= max_len

    reconstructed = "".join(chunks)
    assert reconstructed.replace(" ", "") == long_text.replace(" ", "")


def test_split_message_newlines() -> None:
    """Splitting should respect line breaks where feasible."""
    paragraph1 = "Line one of the message.\n"
    paragraph2 = "Line two of the message.\n"
    combined = paragraph1 + paragraph2
    chunks = split_message(combined, max_length=30)
    assert len(chunks) >= 2


# ==============================================================================
# 2. Environment Configuration & Security Tests
# ==============================================================================

def test_get_bot_token_missing() -> None:
    """Should raise ValueError if TELEGRAM_BOT_TOKEN is missing or placeholder."""
    with patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": ""}, clear=True):
        with pytest.raises(ValueError, match="TELEGRAM_BOT_TOKEN is not configured"):
            get_bot_token()

    with patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "your_telegram_bot_token_here"}, clear=True):
        with pytest.raises(ValueError, match="TELEGRAM_BOT_TOKEN is not configured"):
            get_bot_token()


def test_get_bot_token_valid() -> None:
    """Should return token string when properly configured."""
    fake_token = "123456789:ABCdef_secret_token"
    with patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": fake_token}):
        assert get_bot_token() == fake_token


def test_get_owner_id_parsing() -> None:
    """Should correctly parse integer chat IDs and return None for invalid ones."""
    with patch.dict(os.environ, {"TELEGRAM_OWNER_ID": "987654321"}):
        assert get_owner_id() == 987654321

    with patch.dict(os.environ, {"TELEGRAM_OWNER_ID": "your_telegram_chat_id_here"}):
        assert get_owner_id() is None

    with patch.dict(os.environ, {"TELEGRAM_OWNER_ID": ""}):
        assert get_owner_id() is None

    with patch.dict(os.environ, {"TELEGRAM_OWNER_ID": "not_a_number"}):
        assert get_owner_id() is None


# ==============================================================================
# 3. Path Validation & send_telegram Tests (Day 3-5)
# ==============================================================================

def test_is_allowed_path() -> None:
    """Files must only be allowed in workspace/ or temp_* directories."""
    assert is_allowed_path("workspace/report.pdf")
    assert is_allowed_path("temp_vision/screenshot_1.jpg")
    assert is_allowed_path("temp_audio/voice.ogg")
    assert is_allowed_path("workspace/sub/file.png")

    # Unauthorized paths
    assert not is_allowed_path("C:/Windows/system32/cmd.exe")
    assert not is_allowed_path("core/brain.py")
    assert not is_allowed_path(".env")


@patch("messaging.telegram_bot.get_owner_id", return_value=None)
def test_send_telegram_missing_owner(mock_owner: Any) -> None:
    """Should return False if TELEGRAM_OWNER_ID is not configured."""
    result = send_telegram("Hello")
    assert result is False


@patch("messaging.telegram_bot.get_owner_id", return_value=123456)
@patch("messaging.telegram_bot.create_bot")
def test_send_telegram_text_success(mock_create_bot: Any, mock_owner: Any) -> None:
    """Should successfully send text message to owner chat ID."""
    mock_bot = MagicMock()
    mock_create_bot.return_value = mock_bot

    result = send_telegram("Hello owner")
    assert result is True
    mock_bot.send_message.assert_called_once_with(chat_id=123456, text="Hello owner")


@patch("messaging.telegram_bot.get_owner_id", return_value=123456)
@patch("messaging.telegram_bot.create_bot")
def test_send_telegram_photo_extension(mock_create_bot: Any, mock_owner: Any) -> None:
    """Should send .png / .jpg as photo using bot.send_photo (Day 5)."""
    mock_bot = MagicMock()
    mock_create_bot.return_value = mock_bot

    os.makedirs("workspace", exist_ok=True)
    test_photo = os.path.join("workspace", "sample_screen.png")
    with open(test_photo, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\nfakeimage")

    try:
        result = send_telegram("Screen photo", file_path=test_photo)
        assert result is True
        assert mock_bot.send_photo.called
        assert not mock_bot.send_document.called
    finally:
        if os.path.exists(test_photo):
            os.remove(test_photo)


@patch("messaging.telegram_bot.get_owner_id", return_value=123456)
@patch("messaging.telegram_bot.create_bot")
def test_send_telegram_document_extension(mock_create_bot: Any, mock_owner: Any) -> None:
    """Non-image files like .pdf/.txt should be sent as document."""
    mock_bot = MagicMock()
    mock_create_bot.return_value = mock_bot

    os.makedirs("workspace", exist_ok=True)
    test_doc = os.path.join("workspace", "document.pdf")
    with open(test_doc, "wb") as f:
        f.write(b"%PDF-1.4 sample content")

    try:
        result = send_telegram("Here is your PDF", file_path=test_doc)
        assert result is True
        assert mock_bot.send_document.called
        assert not mock_bot.send_photo.called
    finally:
        if os.path.exists(test_doc):
            os.remove(test_doc)


@patch("messaging.telegram_bot.get_owner_id", return_value=123456)
@patch("messaging.telegram_bot.create_bot")
def test_send_telegram_disallowed_folder(mock_create_bot: Any, mock_owner: Any) -> None:
    """Should refuse files not inside workspace/ or temp_* folders."""
    mock_bot = MagicMock()
    mock_create_bot.return_value = mock_bot

    # Try sending file outside allowed folders
    result = send_telegram("Secret", file_path="requirements.txt")
    assert result is False
    assert not mock_bot.send_document.called


@patch("messaging.telegram_bot.get_owner_id", return_value=123456)
@patch("messaging.telegram_bot.create_bot")
@patch("os.path.getsize", return_value=50 * 1024 * 1024)  # 50 MB
def test_send_telegram_size_limit_45mb(mock_size: Any, mock_create_bot: Any, mock_owner: Any) -> None:
    """Should refuse files larger than 45 MB with clear error (Day 5)."""
    mock_bot = MagicMock()
    mock_create_bot.return_value = mock_bot

    os.makedirs("workspace", exist_ok=True)
    test_file = os.path.join("workspace", "large_archive.zip")
    with open(test_file, "wb") as f:
        f.write(b"fake data")

    try:
        result = send_telegram("Huge file", file_path=test_file)
        assert result is False
        assert not mock_bot.send_document.called
    finally:
        if os.path.exists(test_file):
            os.remove(test_file)


# ==============================================================================
# 4. Commands & Message Handlers Tests (Day 4 & Day 5)
# ==============================================================================

def test_start_bot_commands_registration() -> None:
    """Verify /start, /help, /status, /screenshot, and photo handlers are registered."""
    mock_bot = MagicMock()
    registered_commands = {}
    registered_types = {}

    def mock_message_handler(*args: Any, **kwargs: Any) -> Any:
        def decorator(fn: Any) -> Any:
            if "commands" in kwargs:
                for cmd in kwargs["commands"]:
                    registered_commands[cmd] = fn
            if "content_types" in kwargs:
                for ct in kwargs["content_types"]:
                    registered_types[ct] = fn
            return fn
        return decorator

    mock_bot.message_handler = mock_message_handler
    mock_bot.infinity_polling = MagicMock()

    with patch("messaging.telegram_bot.get_owner_id", return_value=111):
        start_bot(bot_instance=mock_bot)

        # Check commands
        assert "start" in registered_commands
        assert "help" in registered_commands
        assert "status" in registered_commands
        assert "screenshot" in registered_commands
        assert "photo" in registered_types

        # Test /status execution
        status_fn = registered_commands["status"]
        fake_msg = MagicMock()
        fake_msg.chat.id = 111
        status_fn(fake_msg)
        assert mock_bot.send_message.called
        call_args = mock_bot.send_message.call_args
        sent_text = call_args[1].get("text") if "text" in call_args[1] else call_args[0][1]
        assert "Jarvis is online" in sent_text


def test_screenshot_command_vision_paused() -> None:
    """When VISION_PAUSED=1, /screenshot should reply with friendly privacy notice."""
    mock_bot = MagicMock()
    registered_commands = {}

    def mock_message_handler(*args: Any, **kwargs: Any) -> Any:
        def decorator(fn: Any) -> Any:
            if "commands" in kwargs:
                for cmd in kwargs["commands"]:
                    registered_commands[cmd] = fn
            return fn
        return decorator

    mock_bot.message_handler = mock_message_handler
    mock_bot.infinity_polling = MagicMock()

    with patch("messaging.telegram_bot.get_owner_id", return_value=111), \
         patch.dict(os.environ, {"VISION_PAUSED": "1"}):
        start_bot(bot_instance=mock_bot)
        screenshot_fn = registered_commands["screenshot"]

        fake_msg = MagicMock()
        fake_msg.chat.id = 111
        screenshot_fn(fake_msg)

        assert mock_bot.send_message.called
        call_args = mock_bot.send_message.call_args
        reply = call_args[1].get("text") if "text" in call_args[1] else call_args[0][1]
        assert "paused" in reply.lower()


def test_incoming_photo_handler() -> None:
    """Incoming photos from owner should be saved to workspace/ and reply 'Saved'."""
    mock_bot = MagicMock()
    registered_types = {}

    def mock_message_handler(*args: Any, **kwargs: Any) -> Any:
        def decorator(fn: Any) -> Any:
            if "content_types" in kwargs:
                for ct in kwargs["content_types"]:
                    registered_types[ct] = fn
            return fn
        return decorator

    mock_bot.message_handler = mock_message_handler
    mock_bot.infinity_polling = MagicMock()
    mock_bot.get_file.return_value = MagicMock(file_path="photos/sample.jpg")
    mock_bot.download_file.return_value = b"image_raw_bytes"

    with patch("messaging.telegram_bot.get_owner_id", return_value=111):
        start_bot(bot_instance=mock_bot)
        photo_fn = registered_types["photo"]

        fake_msg = MagicMock()
        fake_msg.chat.id = 111
        fake_photo = MagicMock()
        fake_photo.file_id = "test_photo_id_123"
        fake_msg.photo = [fake_photo]

        photo_fn(fake_msg)
        fake_msg.reply_to.assert_not_called()  # telebot uses bot.reply_to
        mock_bot.reply_to.assert_called_once_with(fake_msg, "Saved")


# ==============================================================================
# 5. Day 4: SendTelegramTool Tests
# ==============================================================================

def test_send_telegram_tool_schema() -> None:
    """SendTelegramTool must export valid schema matching BaseTool specification."""
    tool = SendTelegramTool()
    schema = tool.get_schema()
    assert schema["name"] == "send_telegram"
    assert "parameters" in schema
    assert "text" in schema["parameters"]["properties"]
    assert "text" in schema["parameters"]["required"]


@patch("messaging.tools.send_telegram", return_value=True)
def test_send_telegram_tool_execution_success(mock_send: Any) -> None:
    """SendTelegramTool.run() should return success ToolResult on delivery."""
    tool = SendTelegramTool()
    result = tool.run(text="Meeting alert at 4 PM")
    assert result.success is True
    assert "Meeting alert" in result.message
    mock_send.assert_called_once_with("Meeting alert at 4 PM")


@patch("messaging.tools.send_telegram", return_value=False)
def test_send_telegram_tool_execution_failure(mock_send: Any) -> None:
    """SendTelegramTool.run() should return structured failure ToolResult if send fails."""
    tool = SendTelegramTool()
    result = tool.run(text="Hello")
    assert result.success is False
    assert "Failed to send" in result.message


def test_send_telegram_tool_empty_text() -> None:
    """Empty message should return friendly failure result."""
    tool = SendTelegramTool()
    result = tool.run(text="")
    assert result.success is False
    assert "empty" in result.message.lower()


def test_tool_registry_autoload_messaging_tools() -> None:
    """tools.registry should automatically load SendTelegramTool into registry."""
    from tools.registry import TOOL_REGISTRY, auto_load_module_tools

    auto_load_module_tools()
    assert "send_telegram" in TOOL_REGISTRY
    assert isinstance(TOOL_REGISTRY["send_telegram"], SendTelegramTool)


# ==============================================================================
# 6. Acceptance Tests (Day 3 & Day 4)
# ==============================================================================

def test_day3_acceptance_what_is_the_date() -> None:
    """Day 3 Acceptance test: 'What is the date today?' returns accurate date response."""
    brain = JarvisBrain()
    response = brain.chat("What is the date today?")
    assert isinstance(response, str)
    assert len(response) > 0
    assert "date" in response.lower() or "today" in response.lower()


@patch("messaging.tools.send_telegram", return_value=True)
def test_day4_acceptance_cli_send_telegram(mock_send: Any) -> None:
    """Day 4 Acceptance test: Ask Jarvis to send Telegram message via tool registry."""
    from tools.registry import execute_tool, auto_load_module_tools

    auto_load_module_tools()
    res = execute_tool("send_telegram", {"text": "hello from CLI"})
    assert res.success is True
    assert mock_send.called


# ==============================================================================
# 7. Day 6: Contacts & WhatsApp Tests
# ==============================================================================

def test_contacts_loading() -> None:
    """Contacts should load from json file with valid mapping."""
    from messaging.contacts import load_contacts

    contacts = load_contacts()
    assert isinstance(contacts, dict)
    assert len(contacts) >= 2


def test_find_contact_exact_and_fuzzy() -> None:
    """find_contact should be case-insensitive and ignore spaces."""
    from messaging.contacts import find_contact

    # Exact match
    phone1 = find_contact("Jayesh")
    assert phone1 is not None

    # Case insensitive
    phone2 = find_contact("jayesh")
    assert phone2 == phone1

    # Whitespace resilience
    phone3 = find_contact("  Jayesh  ")
    phone4 = find_contact("jay esh")
    assert phone3 == phone1
    assert phone4 == phone1

    # Unknown contact
    assert find_contact("TotallyUnknownPerson999") is None


def test_send_whatsapp_unknown_contact_refused() -> None:
    """Never send to a number not in contacts; refuse unknown contact politely."""
    from messaging.whatsapp import send_whatsapp

    res = send_whatsapp("UnknownContactX", "Hello")
    assert "not in your saved contacts" in res
    assert "was not sent" in res


def test_send_whatsapp_empty_message() -> None:
    """Reject empty message string cleanly."""
    from messaging.whatsapp import send_whatsapp

    res = send_whatsapp("Jayesh", "")
    assert "empty" in res.lower()


@patch("pywhatkit.sendwhatmsg_instantly")
def test_send_whatsapp_success(mock_sendmsg: Any) -> None:
    """Valid contact should call pywhatkit with resolved number and 15s wait."""
    from messaging.whatsapp import send_whatsapp
    from messaging.contacts import find_contact

    phone = find_contact("Jayesh")
    assert phone is not None

    res = send_whatsapp("Jayesh", "Hello Jayesh!")
    assert "successfully queued" in res
    mock_sendmsg.assert_called_once_with(
        phone_no=phone,
        message="Hello Jayesh!",
        wait_time=15,
        tab_close=True,
        close_time=3,
    )


@patch("pywhatkit.sendwhatmsg_instantly", side_effect=Exception("Browser automation failure"))
def test_send_whatsapp_never_raises(mock_sendmsg: Any) -> None:
    """send_whatsapp must never raise unhandled exceptions."""
    from messaging.whatsapp import send_whatsapp

    res = send_whatsapp("Jayesh", "Crash test")
    assert "Failed to send WhatsApp message" in res


# ==============================================================================
# 8. Day 7: Persistent Reminders Tests
# ==============================================================================

def test_parse_when_valid() -> None:
    """parse_when should accurately parse 'in N minutes' and 'HH:MM'."""
    from messaging.reminders import parse_when

    ts1, disp1 = parse_when("in 2 minutes")
    assert ts1 > 0
    assert "in 2 min" in disp1.lower()

    ts2, disp2 = parse_when("in 15 mins")
    assert ts2 > ts1

    ts3, disp3 = parse_when("23:45")
    assert ts3 > 0
    assert "23:45" in disp3


def test_parse_when_invalid() -> None:
    """parse_when should raise ValueError on invalid format."""
    from messaging.reminders import parse_when

    with pytest.raises(ValueError):
        parse_when("tomorrow morning")

    with pytest.raises(ValueError):
        parse_when("25:99")


def test_set_reminder_and_persistence() -> None:
    """set_reminder persists entries in reminders.json across calls."""
    from messaging.reminders import (
        set_reminder,
        load_reminders,
        save_reminders,
    )

    test_text = f"Unit test task {int(time.time())}"
    res = set_reminder("in 5 minutes", test_text)
    assert "Reminder set for" in res
    assert test_text in res

    # Verify reload from disk
    items = load_reminders()
    found = [r for r in items if r.get("text") == test_text]
    assert len(found) == 1

    # Clean up test entry
    cleaned = [r for r in items if r.get("text") != test_text]
    save_reminders(cleaned)


@patch("messaging.reminders.send_telegram", return_value=True)
def test_check_due_reminders_dispatch(mock_send: Any) -> None:
    """check_due_reminders should dispatch overdue items and remove them from storage."""
    from messaging.reminders import (
        check_due_reminders,
        load_reminders,
        save_reminders,
    )

    past_epoch = time.time() - 100  # 100s in past (due)
    due_text = f"Overdue alert {int(time.time())}"
    future_text = f"Future alert {int(time.time())}"

    test_records = [
        {"id": "due_1", "due_timestamp": past_epoch, "text": due_text},
        {"id": "fut_1", "due_timestamp": time.time() + 1000, "text": future_text},
    ]
    save_reminders(test_records)

    try:
        dispatched_count = check_due_reminders()
        assert dispatched_count == 1
        assert mock_send.called
        sent_arg = mock_send.call_args[0][0]
        assert due_text in sent_arg

        # Verify due item was removed and future remains
        remaining = load_reminders()
        assert any(r.get("text") == future_text for r in remaining)
        assert not any(r.get("text") == due_text for r in remaining)
    finally:
        # Clean up
        cleaned = [r for r in load_reminders() if r.get("text") not in (due_text, future_text)]
        save_reminders(cleaned)


if __name__ == "__main__":
    pytest.main(["-v", __file__])
