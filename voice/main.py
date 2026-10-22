"""JARVIS Voice Module Entry Point (AI Assignment 3).

Greets with 'Welcome to AI Assignment 3', listens with adaptive VAD
that stops automatically on 5 seconds of silence, and speaks without overlapping.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

# Ensure project root is in sys.path
_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from core.brain import get_brain
from voice.lang import detect_language
from voice.stt import get_transcriber
from voice.tts import get_speaker


def speak(text: str, lang: str | None = None) -> None:
    """Speak text aloud using neural Indian voice with overlap prevention."""
    get_speaker().speak(text, lang)


def listen(silence_seconds: float = 5.0) -> str:
    """Listen from microphone stopping automatically after silence_seconds."""
    transcriber = get_transcriber()
    result = transcriber.listen(max_seconds=15, silence_seconds=silence_seconds)
    return result.get("text", "").strip()


def run_assignment_voice() -> None:
    """Execute the AI Assignment 3 voice interaction flow."""
    print("=" * 60)
    print("        JARVIS - AI ASSIGNMENT 3 VOICE MODULE")
    print("=" * 60)

    # 1. Greet with required message
    speak("Welcome to AI Assignment 3")

    # Ensure speaker finished and clear room reverberation
    time.sleep(0.3)

    # 2. Listen stopping automatically on 5 seconds of silence
    user_speech = listen(silence_seconds=5.0)

    if not user_speech:
        print("\n[AI]: No speech detected.")
        speak("No speech was detected.")
        return

    detected_lang = detect_language(user_speech)
    print(f"\nYou: {user_speech} (Detected: {detected_lang})")

    # 3. Brain generates intelligent reply
    brain = get_brain()
    reply = brain.chat(user_speech)

    # 4. Speak response
    speak(reply, lang=detected_lang)


if __name__ == "__main__":
    run_assignment_voice()
