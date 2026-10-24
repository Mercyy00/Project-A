"""
Safety Guard and Kill-Switch Engine for Project Jarvis.
Provides a global emergency stop hotkey (Ctrl+Alt+Q) via pynput and
structured action auditing into logs/actions.log with sensitive data sanitization.

Author: Abhijit (System & Automation Engineer)
"""

import json
import logging
import os
import re
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

# Global emergency stop event
STOP: threading.Event = threading.Event()

# Active global hotkey listener instance and lock
_listener: Optional[Any] = None
_listener_lock: threading.Lock = threading.Lock()

# Guard logger
logger = logging.getLogger("jarvis.guard")

# Regex for common API key patterns (Google AI Studio, OpenAI, GitHub, Slack, etc.)
_SENSITIVE_KEY_PATTERN = re.compile(
    r"(AIza[0-9A-Za-z\-_]{35}|sk-[a-zA-Z0-9_\-]{20,}|ghp_[a-zA-Z0-9]{36}|xox[baprs]-[a-zA-Z0-9]{10,})",
    re.IGNORECASE,
)

# Field names that contain secrets or credentials
_SENSITIVE_FIELD_NAMES = {
    "api_key",
    "apikey",
    "access_token",
    "auth_token",
    "token",
    "password",
    "secret",
    "gemini_api_key",
    "groq_api_key",
    "telegram_token",
    "bot_token",
    "private_key",
    "credentials",
}

# Field names that contain full file contents or large code payloads
_CONTENT_FIELD_NAMES = {
    "content",
    "file_content",
    "file_contents",
    "file_data",
    "body",
    "data_payload",
}


def _on_kill_switch_triggered() -> None:
    """Internal callback executed when the global Ctrl+Alt+Q hotkey is pressed."""
    try:
        STOP.set()
        logger.critical(
            "[KILL SWITCH] Emergency stop triggered via Ctrl+Alt+Q hotkey! Automation halted."
        )
    except Exception as exc:
        logger.error(f"[KILL SWITCH] Error handling hotkey callback: {exc}")


def start_kill_switch() -> bool:
    """Registers a global hotkey (Ctrl+Alt+Q) with pynput that sets the threading.Event STOP.

    Returns:
        bool: True if listener is active/started successfully, False otherwise.
    """
    global _listener
    try:
        with _listener_lock:
            if _listener is not None:
                is_alive = getattr(_listener, "is_alive", lambda: False)()
                if is_alive:
                    return True

            from pynput import keyboard

            hotkeys = {
                "<ctrl>+<alt>+q": _on_kill_switch_triggered,
                "<ctrl>+<alt>+Q": _on_kill_switch_triggered,
            }

            _listener = keyboard.GlobalHotKeys(hotkeys)
            _listener.daemon = True
            _listener.start()
            logger.info("Global kill-switch listener started. Press Ctrl+Alt+Q to stop automation.")
            return True
    except Exception as exc:
        logger.error(f"Failed to start kill switch hotkey listener: {exc}")
        return False


def stop_kill_switch() -> None:
    """Stops the global kill switch hotkey listener thread if currently running."""
    global _listener
    try:
        with _listener_lock:
            if _listener is not None:
                try:
                    _listener.stop()
                except Exception:
                    pass
                _listener = None
    except Exception as exc:
        logger.error(f"Failed to stop kill switch listener: {exc}")


def is_stopped() -> bool:
    """Checks whether the emergency kill switch has been triggered.

    Returns:
        bool: True if the STOP event is set, False otherwise.
    """
    try:
        return STOP.is_set()
    except Exception:
        return False


def reset_stop() -> None:
    """Resets the STOP event, allowing automation actions to resume."""
    try:
        STOP.clear()
        logger.info("[KILL SWITCH] STOP event cleared. Automation resumed.")
    except Exception as exc:
        logger.error(f"Failed to reset STOP event: {exc}")


def trigger_stop() -> None:
    """Manually triggers the STOP event programmatically (for testing or emergency hooks)."""
    try:
        STOP.set()
        logger.warning("[KILL SWITCH] STOP event manually triggered.")
    except Exception as exc:
        logger.error(f"Failed to trigger STOP event: {exc}")


def _sanitize_argument(key: str, val: Any) -> Any:
    """Sanitizes an individual argument to remove secrets and file content."""
    try:
        k_lower = str(key).lower()

        # Check for secret / credential keys
        if any(secret_kw in k_lower for secret_kw in _SENSITIVE_FIELD_NAMES):
            return "[REDACTED_SECRET]"

        # Check for file content / large payload fields
        if any(c_kw == k_lower for c_kw in _CONTENT_FIELD_NAMES):
            if isinstance(val, str):
                return f"[FILE_CONTENT: {len(val)} chars redacted]"
            return "[FILE_CONTENT_REDACTED]"

        # Check for code payload
        if k_lower == "code" and isinstance(val, str):
            first_line = val.strip().split("\n")[0][:40]
            return f"[CODE: {len(val)} chars - '{first_line}...']"

        # Recursively sanitize nested structures
        if isinstance(val, dict):
            return {str(k): _sanitize_argument(str(k), v) for k, v in val.items()}
        elif isinstance(val, (list, tuple)):
            return [_sanitize_argument(key, item) for item in val]
        elif isinstance(val, str):
            # Check string value for known API key patterns
            if _SENSITIVE_KEY_PATTERN.search(val):
                return _SENSITIVE_KEY_PATTERN.sub("[REDACTED_KEY]", val)
            # Truncate unusually large string arguments (e.g. inline file bodies > 300 chars)
            if len(val) > 300:
                return f"{val[:100]}... [total {len(val)} chars]"
            return val

        return val
    except Exception:
        return "[UNSANITIZED_ARG_ERROR]"


def _sanitize_args(args: Any) -> Any:
    """Sanitizes arguments object before logging."""
    try:
        if isinstance(args, dict):
            return {str(k): _sanitize_argument(str(k), v) for k, v in args.items()}
        elif isinstance(args, (list, tuple)):
            return [_sanitize_argument("item", item) for item in args]
        elif isinstance(args, str):
            return _sanitize_argument("arg", args)
        return args
    except Exception:
        return "[ARGS_SANITIZATION_FAILED]"


def _get_log_file_path() -> Path:
    """Returns the absolute path to logs/actions.log, creating the logs/ directory if necessary."""
    try:
        repo_root = Path(__file__).resolve().parent.parent
        log_dir = repo_root / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        return log_dir / "actions.log"
    except Exception:
        fallback_dir = Path("logs")
        fallback_dir.mkdir(parents=True, exist_ok=True)
        return fallback_dir / "actions.log"


def log_action(tool_name: str, args: Any, result_summary: Any) -> None:
    """Appends one line with timestamp to logs/actions.log.

    Guarantees:
    - Never logs API keys, passwords, or secrets.
    - Never logs raw file contents or massive code payloads.
    - Ensures each log entry is written on exactly ONE line.
    - Creates the logs/ directory automatically.
    - Never raises an unhandled exception.

    Args:
        tool_name: The name of the tool executed (e.g. 'type_text', 'click').
        args: Dictionary or representation of input arguments.
        result_summary: Summary of execution outcome or error message.
    """
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sanitized_args = _sanitize_args(args)

        # Format args as a compact single-line JSON or string
        try:
            args_str = json.dumps(sanitized_args, ensure_ascii=False)
        except Exception:
            args_str = str(sanitized_args)

        # Clean newlines from args and result summary to ensure exactly one line per log
        clean_args = args_str.replace("\r", " ").replace("\n", " ").strip()
        clean_result = str(result_summary).replace("\r", " ").replace("\n", " ").strip()

        log_line = f"[{timestamp}] TOOL: {tool_name} | ARGS: {clean_args} | RESULT: {clean_result}\n"

        log_file = _get_log_file_path()
        log_file.parent.mkdir(parents=True, exist_ok=True)
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(log_line)

    except Exception as exc:
        logger.error(f"Failed to write action log: {exc}")
