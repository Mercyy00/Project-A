"""Telegram Bot module for Project JARVIS.

Authored by: Trupti (Messaging Engineer)
Covers Days 1 to 9 requirements:
- Secure communication & owner-only authorization
- Command handlers: /start, /help, /status, /screenshot
- Long message splitting (4096-char Telegram limit)
- send_telegram() sending text, photos (.png/.jpg/.jpeg), or documents
- File safety validation (workspace/ or temp_* folders, <= 45 MB)
- Incoming photo handler saving to workspace/ and replying 'Saved'
- Day 9: Voice note handler transcribing audio and routing to Jarvis Brain (Task 14)
- Day 9: send_telegram_with_confirmation & Inline confirmation buttons (Task 22)
- JarvisBrain handler routing with error safety
"""

from __future__ import annotations

import datetime
import logging
import os
from pathlib import Path
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

# Telegram API & safety limits
TELEGRAM_MAX_MESSAGE_LENGTH = 4096
TELEGRAM_MAX_CAPTION_LENGTH = 1024
MAX_FILE_SIZE_MB = 45.0
MAX_FILE_SIZE_BYTES = int(MAX_FILE_SIZE_MB * 1024 * 1024)

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
        List[str]: Chunks each within max_length characters.
    """
    if not text:
        return [""]

    if len(text) <= max_length:
        return [text]

    chunks: List[str] = []
    remaining = text

    while len(remaining) > max_length:
        split_idx = -1
        # Try finding a natural newline boundary
        newline_idx = remaining.rfind("\n", 0, max_length)
        if newline_idx != -1 and newline_idx >= max_length // 2:
            split_idx = newline_idx + 1
        else:
            # Fall back to word boundary (space)
            space_idx = remaining.rfind(" ", 0, max_length)
            if space_idx != -1 and space_idx >= max_length // 2:
                split_idx = space_idx + 1
            else:
                # Hard character limit cut
                split_idx = max_length

        chunks.append(remaining[:split_idx].rstrip("\r\n"))
        remaining = remaining[split_idx:].lstrip("\r\n")

    if remaining:
        chunks.append(remaining)

    return chunks


def is_allowed_path(file_path: str) -> bool:
    """Validate whether the file path is within safe sandboxed directories.

    Allowed directories:
    - workspace/
    - temp_* folders (e.g. temp_vision, temp_voice)
    - safe_sandbox/

    Args:
        file_path: Relative or absolute path to check.

    Returns:
        bool: True if inside allowed folders, False otherwise.
    """
    try:
        candidate = Path(file_path).resolve()
        project_root = Path(__file__).resolve().parent.parent

        allowed_prefixes = [
            (project_root / "workspace").resolve(),
            (project_root / "safe_sandbox").resolve(),
        ]

        # Check explicit allowed roots
        for prefix in allowed_prefixes:
            try:
                candidate.relative_to(prefix)
                return True
            except ValueError:
                pass

        # Check temp_* directories under project root
        try:
            rel_to_root = candidate.relative_to(project_root)
            first_part = rel_to_root.parts[0] if rel_to_root.parts else ""
            if first_part.startswith("temp_"):
                return True
        except ValueError:
            pass

        return False

    except Exception as exc:
        logger.error("Error validating file path '%s': %s", file_path, exc)
        return False


def create_bot() -> telebot.TeleBot:
    """Instantiate and return a configured TeleBot client.

    Returns:
        telebot.TeleBot: Configured bot instance.
    """
    token = get_bot_token()
    return telebot.TeleBot(token, parse_mode=None)


def send_telegram(
    text: str,
    file_path: Optional[str] = None,
    bot_instance: Optional[telebot.TeleBot] = None,
) -> bool:
    """Deliver a text message or file attachment directly to the authorized owner.

    Args:
        text: Message string to send.
        file_path: Optional path to an attachment file.
        bot_instance: Optional injected TeleBot instance for testing.

    Returns:
        bool: True on successful delivery, False on error.
    """
    owner_id = get_owner_id()
    if owner_id is None:
        logger.warning(
            "send_telegram aborted: TELEGRAM_OWNER_ID is not configured in .env."
        )
        return False

    try:
        bot = bot_instance if bot_instance is not None else create_bot()

        # Handle file attachment dispatch if provided
        if file_path:
            clean_path = str(file_path).strip()
            if not os.path.isfile(clean_path):
                logger.error("send_telegram failed: file '%s' does not exist.", clean_path)
                return False

            if not is_allowed_path(clean_path):
                logger.error(
                    "send_telegram security violation: path '%s' is outside safe folders.",
                    clean_path,
                )
                return False

            file_size = os.path.getsize(clean_path)
            if file_size > MAX_FILE_SIZE_BYTES:
                size_mb = file_size / (1024 * 1024)
                logger.error(
                    "send_telegram refused: file '%s' is %.2f MB (limit is %.1f MB).",
                    clean_path,
                    size_mb,
                    MAX_FILE_SIZE_MB,
                )
                return False

            caption = text if text and len(text) <= TELEGRAM_MAX_CAPTION_LENGTH else None
            lower_path = clean_path.lower()
            is_photo = lower_path.endswith((".png", ".jpg", ".jpeg"))

            with open(clean_path, "rb") as media_file:
                if is_photo:
                    bot.send_photo(chat_id=owner_id, photo=media_file, caption=caption)
                else:
                    bot.send_document(chat_id=owner_id, document=media_file, caption=caption)

            # If text exceeded caption limit, send full text in subsequent message chunks
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


def send_telegram_with_confirmation(
    text: str,
    action_token: str,
    confirm_label: str = "Confirm",
    cancel_label: str = "Cancel",
    bot_instance: Optional[telebot.TeleBot] = None,
) -> bool:
    """Send a notification to the owner with interactive inline confirmation buttons.

    Args:
        text: Prompt or notification text describing the action.
        action_token: Unique action or confirmation token (e.g. from core.confirm).
        confirm_label: Text for confirmation button.
        cancel_label: Text for cancellation button.
        bot_instance: Optional injected TeleBot instance.

    Returns:
        bool: True on successful delivery, False on error.
    """
    try:
        bot = bot_instance if bot_instance is not None else create_bot()
        owner_id = get_owner_id()
        if owner_id is None:
            logger.warning("Cannot send confirmation: TELEGRAM_OWNER_ID is not set.")
            return False

        markup = telebot.types.InlineKeyboardMarkup(row_width=2)
        btn_confirm = telebot.types.InlineKeyboardButton(
            text=f"✅ {confirm_label}",
            callback_data=f"confirm:{action_token}",
        )
        btn_cancel = telebot.types.InlineKeyboardButton(
            text=f"❌ {cancel_label}",
            callback_data=f"cancel:{action_token}",
        )
        markup.add(btn_confirm, btn_cancel)

        bot.send_message(chat_id=owner_id, text=text, reply_markup=markup)
        return True
    except Exception as exc:
        logger.error("send_telegram_with_confirmation failed: %s", exc)
        return False


def start_bot(
    handler: Optional[Callable[[str], str]] = None,
    bot_instance: Optional[telebot.TeleBot] = None,
) -> None:
    """Start the Telegram bot with owner authorization, commands, photos, voice notes, and confirmations.

    Args:
        handler: Callable accepting input text and returning string response.
                 Defaults to echo handler.
        bot_instance: Optional injected TeleBot instance for testing.
    """
    effective_handler: Callable[[str], str] = handler if handler is not None else (lambda msg: msg)

    try:
        bot = bot_instance if bot_instance is not None else create_bot()
    except Exception as exc:
        logger.error("Failed to start bot: %s", exc)
        raise

    def check_owner(message: telebot.types.Message) -> bool:
        """Validate if incoming message originates from the registered owner."""
        owner_id = get_owner_id()
        chat_id = message.chat.id

        if owner_id is None:
            print(
                f"\n[JARVIS Bot] Incoming message from chat ID: {chat_id}\n"
                f"Please add TELEGRAM_OWNER_ID={chat_id} to your .env file and restart.\n"
            )
            return False

        if chat_id != owner_id:
            logger.warning("Ignored message from unauthorized chat ID: %s", chat_id)
            return False

        return True

    # -------------------------------------------------------------------------
    # Day 4: Command Handlers (/start, /help, /status)
    # -------------------------------------------------------------------------

    @bot.message_handler(commands=["start"])
    def cmd_start(message: telebot.types.Message) -> None:
        if not check_owner(message):
            return
        welcome_text = (
            "Greetings, sir. I am JARVIS, your desktop AI assistant.\n"
            "You can talk to me directly, ask me to perform tasks, or send commands.\n\n"
            "Type /help to see available commands."
        )
        for chunk in split_message(welcome_text):
            bot.send_message(message.chat.id, chunk)

    @bot.message_handler(commands=["help"])
    def cmd_help(message: telebot.types.Message) -> None:
        if not check_owner(message):
            return
        help_text = (
            "Available JARVIS Commands:\n"
            "• /start - Welcome message and orientation\n"
            "• /help - Display this command directory\n"
            "• /status - Check current system status and time\n"
            "• /screenshot - Capture laptop display and deliver it here\n\n"
            "You can also send me photos, voice notes, or normal text to converse with JarvisBrain."
        )
        for chunk in split_message(help_text):
            bot.send_message(message.chat.id, chunk)

    @bot.message_handler(commands=["status"])
    def cmd_status(message: telebot.types.Message) -> None:
        if not check_owner(message):
            return
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        status_text = f"Jarvis is online. Current time: {current_time}"
        for chunk in split_message(status_text):
            bot.send_message(message.chat.id, chunk)

    # -------------------------------------------------------------------------
    # Day 5: /screenshot Command
    # -------------------------------------------------------------------------

    @bot.message_handler(commands=["screenshot"])
    def cmd_screenshot(message: telebot.types.Message) -> None:
        if not check_owner(message):
            return

        if os.getenv("VISION_PAUSED", "0") == "1":
            bot.send_message(
                message.chat.id,
                "Screen capture is currently paused by user privacy mode (VISION_PAUSED=1).",
            )
            return

        try:
            from vision.screen import take_screenshot  # type: ignore

            screenshot_path = take_screenshot()
            success = send_telegram(text="Here is your laptop screen:", file_path=screenshot_path)
            if not success:
                bot.send_message(message.chat.id, "Failed to deliver screenshot image.")
        except ImportError:
            bot.send_message(
                message.chat.id,
                "Screen capture module (vision.screen) is not available on this system.",
            )
        except PermissionError:
            bot.send_message(
                message.chat.id,
                "Screen capture is currently paused by user privacy mode (VISION_PAUSED=1).",
            )
        except Exception as exc:
            logger.error("Screenshot error: %s", exc)
            bot.send_message(message.chat.id, f"Could not capture screenshot: {exc}")

    # -------------------------------------------------------------------------
    # Day 5: Incoming Photo Handler (Save to workspace/ and reply 'Saved')
    # -------------------------------------------------------------------------

    @bot.message_handler(content_types=["photo"])
    def on_photo_message(message: telebot.types.Message) -> None:
        if not check_owner(message):
            return

        try:
            os.makedirs("workspace", exist_ok=True)
            photo = message.photo[-1]
            file_info = bot.get_file(photo.file_id)
            downloaded = bot.download_file(file_info.file_path)

            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"received_photo_{timestamp}_{photo.file_id[-6:]}.jpg"
            target_path = os.path.join("workspace", filename)

            with open(target_path, "wb") as f:
                f.write(downloaded)

            logger.info("Saved photo from owner to %s", target_path)
            bot.reply_to(message, "Saved")
        except Exception as exc:
            logger.error("Failed to save incoming photo: %s", exc, exc_info=True)
            bot.reply_to(message, "Sorry, failed to save photo.")

    # -------------------------------------------------------------------------
    # Day 9: Incoming Voice Note / Audio Memo Handler (Task 14)
    # -------------------------------------------------------------------------

    @bot.message_handler(content_types=["voice", "audio"])
    def on_voice_message(message: telebot.types.Message) -> None:
        if not check_owner(message):
            return

        try:
            os.makedirs("workspace", exist_ok=True)
            voice_obj = getattr(message, "voice", None) or getattr(message, "audio", None)
            if not voice_obj:
                bot.reply_to(message, "Could not read audio data.")
                return

            file_info = bot.get_file(voice_obj.file_id)
            downloaded = bot.download_file(file_info.file_path)

            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            ext = ".ogg" if getattr(message, "voice", None) else ".mp3"
            voice_filename = f"received_voice_{timestamp}_{voice_obj.file_id[-6:]}{ext}"
            voice_path = os.path.join("workspace", voice_filename)

            with open(voice_path, "wb") as f:
                f.write(downloaded)

            logger.info("Saved incoming voice note to %s. Transcribing...", voice_path)

            transcribed_text = ""
            try:
                from voice.stt import transcribe_audio  # type: ignore
                transcribed_text = transcribe_audio(voice_path)
            except Exception as stt_err:
                logger.warning("STT transcription exception: %s. Using fallback note.", stt_err)
                transcribed_text = f"[Audio memo received: {voice_filename}]"

            if not transcribed_text:
                bot.reply_to(message, "Could not transcribe voice audio.")
                return

            logger.info("Voice note transcribed: '%s'", transcribed_text)
            reply = effective_handler(transcribed_text)
            reply_text = f"🎙️ Heard: {transcribed_text}\n\n🤖 {reply}"
            for chunk in split_message(reply_text):
                bot.send_message(message.chat.id, chunk)

        except Exception as exc:
            logger.error("Error processing Telegram voice note: %s", exc, exc_info=True)
            bot.reply_to(message, "Sorry, failed to process voice note.")

    # -------------------------------------------------------------------------
    # Day 9: Inline Action Confirmation Callback Handler (Task 22)
    # -------------------------------------------------------------------------

    @bot.callback_query_handler(func=lambda call: True)
    def on_callback_query(call: telebot.types.CallbackQuery) -> None:
        owner_id = get_owner_id()
        if owner_id is not None and call.from_user.id != owner_id:
            bot.answer_callback_query(call.id, text="Unauthorized", show_alert=True)
            return

        data = call.data or ""
        if data.startswith("confirm:"):
            token = data.split(":", 1)[1]
            try:
                from core.confirm import execute_confirmation
                res = execute_confirmation(token)
                msg = res.get("message", "Operation executed.")
                bot.edit_message_text(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    text=f"✅ Confirmed: {msg}",
                )
            except Exception:
                bot.edit_message_text(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    text=f"✅ Confirmed (token: {token})",
                )
            bot.answer_callback_query(call.id, text="Confirmed!")

        elif data.startswith("cancel:"):
            token = data.split(":", 1)[1]
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=f"❌ Action cancelled by user (token: {token}).",
            )
            bot.answer_callback_query(call.id, text="Cancelled")

    # -------------------------------------------------------------------------
    # Day 2-3: Incoming Text Message Handler (Jarvis Brain / Echo)
    # -------------------------------------------------------------------------

    @bot.message_handler(func=lambda msg: True, content_types=["text"])
    def on_text_message(message: telebot.types.Message) -> None:
        if not check_owner(message):
            return

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
                bot.send_message(chat_id=message.chat.id, text=chunk)

    logger.info("Starting Telegram bot infinity_polling...")
    try:
        bot.infinity_polling(timeout=10, long_polling_timeout=5)
    except Exception as exc:
        logger.error("Bot infinity_polling stopped due to error: %s", exc)


def verify_telegram_module() -> bool:
    """Run verification checks on telegram_bot functions."""
    print("Running verification checks on messaging.telegram_bot...")

    short_text = "Hello JARVIS"
    assert split_message(short_text) == [short_text], "Short message split failed"

    long_text = "A" * 5000
    chunks = split_message(long_text, max_length=1000)
    assert len(chunks) == 5, f"Expected 5 chunks, got {len(chunks)}"

    # Test allowed paths
    assert is_allowed_path("workspace/report.pdf")
    assert is_allowed_path("temp_vision/screen.jpg")
    assert not is_allowed_path("C:/Windows/system32/cmd.exe")

    print("[PASS] telegram_bot functions verified successfully!")
    return True


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--verify":
        verify_telegram_module()
    else:
        print("Starting Jarvis Telegram Bot. Press Ctrl+C to stop.")
        start_bot()
