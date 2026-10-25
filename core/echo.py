"""
Acoustic Echo Guard for JARVIS.
Ported from Mark LVI (core/echo.py).

Prevents the assistant from hearing its own speech output through the microphone
by tracking active speech synthesis playback windows and applying echo suppression.
"""

from __future__ import annotations

# Re-export from voice.echo for unified implementation
from voice.echo import (
    EchoGuard,
    band_energies,
    mark_speech_active,
    is_speech_active,
)

__all__ = ["EchoGuard", "band_energies", "mark_speech_active", "is_speech_active"]
