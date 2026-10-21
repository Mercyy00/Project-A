"""Telegram Bot module for Project JARVIS.

Authored by: Trupti (Messaging Engineer)
Handles secure Telegram communication, owner-only authorization,
message routing to Jarvis handler, long message chunking, and file delivery.
"""

from __future__ import annotations

import logging
import os
import sys
from typing import Callable, List, Optional

import dotenv
import telebot

# Configure module-level logger
logger = logging.getLogger("messaging.telegram_bot")
if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter("[%(asctime)s] [%(levelname)s] [messaging]: %(message)s")
    )
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

# Telegram API constants
TELEGRAM_MAX_MESSAGE_LENGTH = 4096
TELEGRAM_MAX_CAPTION_LENGTH = 1024

_ENV_LOADED = False


def load_env_config(force_reload: bool = False) -> None:
    """Load environment variables from .env file safely."""
    global _ENV_LOADED
    if not _ENV_LOADED or force_reload:
        try:
            dotenv.load_dotenv(override=False)
            _ENV_LOADED = True
        except Exception as exc:
            logger.error("Failed to load .env configuration: %s", exc)


def get_bot_token() -> str:
    """Retrieve the Telegram bot token from environment variables.

    Returns:
        str: The bot token string.

    Raises:
        ValueError: If TELEGRAM_BOT_TOKEN is missing or empty.
    """
    load_env_config()
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not token or token == "your_telegram_bot_token_here":
        raise ValueError(
            "TELEGRAM_BOT_TOKEN is not configured in .env. "
            "Please create your bot with @BotFather and add the token to .env."
        )
    return token


def get_owner_id() -> Optional[int]:
    """Retrieve and parse the authorized owner's Telegram Chat ID.

    Returns:
        Optional[int]: The numeric chat ID if valid, otherwise None.
    """
    load_env_config()
    raw_id = os.getenv("TELEGRAM_OWNER_ID", "").strip()
    if not raw_id or raw_id == "your_telegram_chat_id_here":
        return None
    try:
        return int(raw_id)
    except ValueError:
        logger.warning("Invalid TELEGRAM_OWNER_ID in .env: must be an integer.")
        return None


def split_message(text: str, max_length: int = TELEGRAM_MAX_MESSAGE_LENGTH) -> List[str]:
    """Split a long message string into chunks within Telegram length limits.

    Splits gracefully at line breaks or word boundaries where possible.

    Args:
        text: The message string to split.
        max_length: Maximum allowed characters per chunk (default 4096).

    Returns:
        List[str]: Chunks each having length <= max_length.
    """
    if not text:
        return [""]
    if len(text) <= max_length:
        return [text]

    chunks: List[str] = []
    remaining = text

    while len(remaining) > max_length:
        # Search for safe split point near max_length
        split_index = -1

        # Prefer newline boundary
        newline_idx = remaining.rfind("\n", 0, max_length)
        if newline_idx != -1 and newline_idx >= max_length // 2:
            split_index = newline_idx + 1

        # Fallback to space boundary
        if split_index == -1:
            space_idx = remaining.rfind(" ", 0, max_length)
            if space_idx != -1 and space_idx >= max_length // 2:
                split_index = space_idx + 1

        # Hard split if no suitable whitespace found
        if split_index == -1:
            split_index = max_length

        chunk = remaining[:split_index].rstrip("\r\n")
        if chunk:
            chunks.append(chunk)
        remaining = remaining[split_index:].lstrip("\r\n")

    if remaining:
        chunks.append(remaining)

    return chunks


def create_bot(token: Optional[str] = None) -> telebot.TeleBot:
    """Create and initialize a TeleBot instance safely.

    Args:
        token: Optional explicit token; if omitted, retrieved from .env.

    Returns:
        telebot.TeleBot: Configured bot instance.
    """
    bot_token = token or get_bot_token()
    return telebot.TeleBot(token=bot_token, parse_mode=None)


def send_telegram(text: str, file_path: Optional[str] = None) -> bool:
    """Send a text message or a document to the owner on Telegram.

    Adheres strictly to the specification:
    - Sends to TELEGRAM_OWNER_ID (text, or document if file_path is given and exists).
    - Never raises an unhandled exception; returns False and logs on failure.
    - Never logs or prints secrets.

    Args:
        text: The text message or document caption.
        file_path: Optional path to a local document file to send.

    Returns:
        bool: True if sent successfully, False otherwise.
    """
    try:
        owner_id = get_owner_id()
        if owner_id is None:
            logger.error(
                "send_telegram failed: TELEGRAM_OWNER_ID is not set in .env. "
                "Cannot determine recipient."
            )
            return False

        try:
            bot = create_bot()
        except Exception as exc:
            logger.error("send_telegram failed to initialize bot: %s", exc)
            return False

        # If a file_path is provided
        if file_path is not None:
            if not os.path.isfile(file_path):
                logger.error("send_telegram failed: file '%s' does not exist.", file_path)
                return False

            with open(file_path, "rb") as document_file:
                # Handle caption limit
                caption = text if text and len(text) <= TELEGRAM_MAX_CAPTION_LENGTH else None
                bot.send_document(chat_id=owner_id, document=document_file, caption=caption)

            # If text exceeds caption limit, send text in subsequent message
            if text and len(text) > TELEGRAM_MAX_CAPTION_LENGTH:
                for chunk in split_message(text):
                    if chunk:
                        bot.send_message(chat_id=owner_id, text=chunk)
            return True

        # Pure text message delivery
        chunks = split_message(text)
        for chunk in chunks:
            if chunk:
                bot.send_message(chat_id=owner_id, text=chunk)
        return True

    except Exception as exc:
        logger.error("send_telegram encountered an error: %s", exc)
        return False


def start_bot(
    handler: Optional[Callable[[str], str]] = None,
    bot_instance: Optional[telebot.TeleBot] = None,
) -> None:
    """Start the Telegram bot with owner authorization and message handler.

    Specification:
    1. Text messages from owner call handler(text) and returned answer is sent back
       (sending long answers in several messages).
    2. Runs handler in polling thread, catches exceptions, replies 'Sorry, something went wrong.'
    3. Ignores every message whose chat id is not TELEGRAM_OWNER_ID.
    4. If TELEGRAM_OWNER_ID is not set yet, prints chat id of first incoming message,
       tells user to add it to .env, and does NOT reply.
    5. Network errors handled without crashing using infinity_polling.

    Args:
        handler: Callable accepting input text and returning string response.
                 Defaults to echo handler (repeats user text).
        bot_instance: Optional injected TeleBot instance (used for testing).
    """
    effective_handler: Callable[[str], str] = handler if handler is not None else (lambda msg: msg)

    try:
        bot = bot_instance if bot_instance is not None else create_bot()
    except Exception as exc:
        logger.error("Failed to start bot: %s", exc)
        raise

    @bot.message_handler(func=lambda msg: True, content_types=["text"])
    def on_text_message(message: telebot.types.Message) -> None:
        try:
            owner_id = get_owner_id()
            chat_id = message.chat.id

            # Case: TELEGRAM_OWNER_ID is not set yet
            if owner_id is None:
                print(
                    f"\n[JARVIS Bot] Incoming message from chat ID: {chat_id}\n"
                    f"Please add TELEGRAM_OWNER_ID={chat_id} to your .env file and restart.\n"
                )
                return  # Do not reply to unauthorized/unknown user

            # Case: Message from anyone other than the owner
            if chat_id != owner_id:
                logger.warning("Ignored message from unauthorized chat ID: %s", chat_id)
                return  # Silently ignore

            # Case: Authorized owner message
            incoming_text = message.text or ""
            logger.info("Received message from owner (length: %d)", len(incoming_text))

            try:
                response = effective_handler(incoming_text)
            except Exception as err:
                logger.error("Exception during handler execution: %s", err, exc_info=True)
                response = "Sorry, something went wrong."

            if response is None:
                response = ""

            chunks = split_message(response)
            for chunk in chunks:
                if chunk:
                    bot.send_message(chat_id=chat_id, text=chunk)

        except Exception as exc:
            logger.error("Error processing message: %s", exc, exc_info=True)

    logger.info("Starting Telegram bot infinity_polling...")
    try:
        bot.infinity_polling(timeout=10, long_polling_timeout=5)
    except Exception as exc:
        logger.error("Bot infinity_polling stopped due to error: %s", exc)


def verify_telegram_module() -> bool:
    """Run verification checks on telegram_bot functions.

    Returns:
        bool: True if internal checks pass.
    """
    print("Running verification checks on messaging.telegram_bot...")

    # 1. Test split_message
    short_text = "Hello JARVIS"
    assert split_message(short_text) == [short_text], "Short message split failed"

    long_text = "A" * 5000
    chunks = split_message(long_text, max_length=1000)
    assert len(chunks) == 5, f"Expected 5 chunks, got {len(chunks)}"
    assert all(len(c) <= 1000 for c in chunks), "Chunk exceeded max_length"
    assert "".join(chunks) == long_text, "Chunk reconstruction mismatch"

    # 2. Test environment validation
    try:
        token = get_bot_token()
        print(f"TELEGRAM_BOT_TOKEN is present (length: {len(token)}).")
    except ValueError as val_err:
        print(f"Notice: {val_err}")

    owner_id = get_owner_id()
    if owner_id:
        print(f"TELEGRAM_OWNER_ID is configured: {owner_id}")
    else:
        print("Notice: TELEGRAM_OWNER_ID is not configured yet in .env.")

    print("Verification checks passed successfully!")
    return True


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--verify":
        verify_telegram_module()
    else:
        print("Starting Echo Bot. Press Ctrl+C to stop.")
        start_bot()
