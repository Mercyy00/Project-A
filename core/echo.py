"""
Acoustic Echo Guard for JARVIS.

Ported from Mark LVI's core/echo.py.
Prevents the assistant from hearing its own speech output through the microphone
by tracking active speech synthesis playback windows and applying echo suppression.
"""

from __future__ import annotations

import time
import threading
from typing import Optional

_lock = threading.Lock()
_speaking_until: float = 0.0
_echo_tail_margin: float = 0.35  # seconds after speech ends where room echo persists


def mark_speech_active(duration_seconds: float) -> None:
    """Notifies the echo guard that audio playback has started for a given duration."""
    global _speaking_until
    with _lock:
        now = time.time()
        _speaking_until = max(_speaking_until, now + duration_seconds + _echo_tail_margin)


def is_assistant_speaking() -> bool:
    """Returns True if the assistant is currently outputting speech or within the echo tail window."""
    with _lock:
        return time.time() < _speaking_until


def clear_speech_state() -> None:
    """Manually resets the speech active state (e.g. on user interruption)."""
    global _speaking_until
    with _lock:
        _speaking_until = 0.0
