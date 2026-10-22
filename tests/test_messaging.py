"""Comprehensive unit and integration test suite for JARVIS Messaging.

Authored by: Trupti (Messaging Engineer)
Covers Day 1, Day 2, and Day 3 deliverables:
- Environment variable loading and token protection
- Message splitting for Telegram's 4096-character limit
- Owner-only authorization filtering
- Exception resilience (never crashing the bot)
- send_telegram() text and document delivery
- Handler execution and error handling
- JarvisBrain connection and acceptance tests
"""

from __future__ import annotations

import os
import sys
import tempfile
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
    send_telegram,
    split_message,
    start_bot,
)
from messaging.test_bot_brain import JarvisBrain


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
    long_text = "Word " * 200  # 1000 characters
    chunks = split_message(long_text, max_length=max_len)

    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk) <= max_len

    # All characters preserved
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
    # Valid numeric ID
    with patch.dict(os.environ, {"TELEGRAM_OWNER_ID": "987654321"}):
        assert get_owner_id() == 987654321

    # Placeholder string
    with patch.dict(os.environ, {"TELEGRAM_OWNER_ID": "your_telegram_chat_id_here"}):
        assert get_owner_id() is None

    # Empty string
    with patch.dict(os.environ, {"TELEGRAM_OWNER_ID": ""}):
        assert get_owner_id() is None

    # Invalid non-numeric string
    with patch.dict(os.environ, {"TELEGRAM_OWNER_ID": "not_a_number"}):
        assert get_owner_id() is None


# ==============================================================================
# 3. send_telegram Tests
# ==============================================================================

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
def test_send_telegram_document_success(mock_create_bot: Any, mock_owner: Any) -> None:
    """Should send document when existing file_path is provided."""
    mock_bot = MagicMock()
    mock_create_bot.return_value = mock_bot

    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp_file:
        tmp_file.write(b"Document content for JARVIS")
        tmp_path = tmp_file.name

    try:
        result = send_telegram("Here is your file", file_path=tmp_path)
        assert result is True
        assert mock_bot.send_document.called
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


@patch("messaging.telegram_bot.get_owner_id", return_value=123456)
@patch("messaging.telegram_bot.create_bot")
def test_send_telegram_nonexistent_file(mock_create_bot: Any, mock_owner: Any) -> None:
    """Should return False if specified file does not exist."""
    result = send_telegram("Missing", file_path="workspace/non_existent_file.pdf")
    assert result is False


@patch("messaging.telegram_bot.get_owner_id", return_value=123456)
@patch("messaging.telegram_bot.create_bot")
def test_send_telegram_never_raises(mock_create_bot: Any, mock_owner: Any) -> None:
    """Should catch all exceptions, log error, and return False."""
    mock_bot = MagicMock()
    mock_bot.send_message.side_effect = Exception("Telegram API Network Error")
    mock_create_bot.return_value = mock_bot

    result = send_telegram("This will fail safely")
    assert result is False


# ==============================================================================
# 4. start_bot & Authorization Tests
# ==============================================================================

def test_start_bot_owner_message_echo() -> None:
    """Owner message should be echoed back when default echo handler is used."""
    mock_bot = MagicMock()
    registered_handlers: List[Any] = []

    def mock_message_handler(*args: Any, **kwargs: Any) -> Any:
        def decorator(fn: Any) -> Any:
            registered_handlers.append(fn)
            return fn
        return decorator

    mock_bot.message_handler = mock_message_handler
    mock_bot.infinity_polling = MagicMock()

    with patch("messaging.telegram_bot.get_owner_id", return_value=111):
        start_bot(bot_instance=mock_bot)
        assert len(registered_handlers) == 1
        handler_fn = registered_handlers[0]

        # Simulate message from authorized owner
        fake_msg = MagicMock()
        fake_msg.chat.id = 111
        fake_msg.text = "Repeat after me"

        handler_fn(fake_msg)
        mock_bot.send_message.assert_called_once_with(chat_id=111, text="Repeat after me")


def test_start_bot_unauthorized_user_ignored() -> None:
    """Messages from non-owner must be silently ignored (no replies)."""
    mock_bot = MagicMock()
    registered_handlers: List[Any] = []

    def mock_message_handler(*args: Any, **kwargs: Any) -> Any:
        def decorator(fn: Any) -> Any:
            registered_handlers.append(fn)
            return fn
        return decorator

    mock_bot.message_handler = mock_message_handler
    mock_bot.infinity_polling = MagicMock()

    with patch("messaging.telegram_bot.get_owner_id", return_value=111):
        start_bot(bot_instance=mock_bot)
        handler_fn = registered_handlers[0]

        # Message from stranger
        stranger_msg = MagicMock()
        stranger_msg.chat.id = 999  # Not 111
        stranger_msg.text = "I am a stranger"

        handler_fn(stranger_msg)
        mock_bot.send_message.assert_not_called()


def test_start_bot_handler_exception_handling() -> None:
    """Exceptions raised in handler should catch and reply 'Sorry, something went wrong.'"""
    mock_bot = MagicMock()
    registered_handlers: List[Any] = []

    def mock_message_handler(*args: Any, **kwargs: Any) -> Any:
        def decorator(fn: Any) -> Any:
            registered_handlers.append(fn)
            return fn
        return decorator

    mock_bot.message_handler = mock_message_handler
    mock_bot.infinity_polling = MagicMock()

    def faulty_handler(text: str) -> str:
        raise RuntimeError("Brain calculation failed")

    with patch("messaging.telegram_bot.get_owner_id", return_value=111):
        start_bot(handler=faulty_handler, bot_instance=mock_bot)
        handler_fn = registered_handlers[0]

        fake_msg = MagicMock()
        fake_msg.chat.id = 111
        fake_msg.text = "Calculate something"

        handler_fn(fake_msg)
        mock_bot.send_message.assert_called_once_with(
            chat_id=111, text="Sorry, something went wrong."
        )


# ==============================================================================
# 5. Day 3 Acceptance Test: JarvisBrain Query
# ==============================================================================

def test_day3_acceptance_what_is_the_date() -> None:
    """Acceptance test: 'What is the date today?' sent to JarvisBrain returns answer."""
    brain = JarvisBrain()
    response = brain.chat("What is the date today?")
    assert isinstance(response, str)
    assert len(response) > 0
    assert "date" in response.lower() or "today" in response.lower()


if __name__ == "__main__":
    pytest.main(["-v", __file__])
