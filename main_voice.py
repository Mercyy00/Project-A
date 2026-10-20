"""JARVIS Desktop Voice Loop (Day 6 Deliverable).

Integrated by Pair A (Jayesh) & Pair B (Madhuri + Akanksha).
Connects: listen -> brain -> speak with Push-to-Talk, live latency measurement,
multilingual detection, and hotkey interruption.
"""

from __future__ import annotations

import datetime
import os
import sys
import time
from pathlib import Path

# Reconfigure stdout for Windows console UTF-8 Devanagari support
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Ensure project root is in sys.path
_project_root = Path(__file__).resolve().parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from core.brain import get_brain
from voice.lang import detect_language, get_personality_phrase
from voice.stt import get_transcriber
from voice.tts import get_speaker


def format_timestamp(ts: float) -> str:
    """Format Unix timestamp as HH:MM:SS.mmm."""
    dt = datetime.datetime.fromtimestamp(ts)
    return dt.strftime("%H:%M:%S") + f".{int(dt.microsecond / 1000):03d}"


def run_voice_turn(auto_listen: bool = False) -> bool:
    """Run a single conversational voice turn: listen -> brain -> speak.

    Returns:
        False if user requested exit, True otherwise.
    """
    transcriber = get_transcriber()
    brain = get_brain()
    speaker = get_speaker()

    if not auto_listen:
        print("\n" + "=" * 60)
        print(" [STATUS: IDLE] Press [ENTER] to Speak, or type 'exit' to quit:")
        user_input = input(" > ").strip().lower()
        if user_input in ("exit", "quit", "q", "थांब", "बंद कर"):
            speaker.speak("Goodbye! Have a productive day.")
            return False

    print("\n[STATUS: LISTENING] Speak now (stops automatically on 1.5s silence)...")
    try:
        # Step 1: Listen until silence
        result = transcriber.listen(max_seconds=10, silence_seconds=1.5)
        user_text = result.get("text", "").strip()
        speech_end_time = result.get("speech_end_time", time.time())

        if not user_text:
            print("[STATUS: IDLE] No speech detected.")
            return True

        # Step 2: Language detection
        detected_lang = detect_language(user_text)
        print(f"\n[USER]: \"{user_text}\" (Language: {detected_lang})")

        # Exit command detection
        if user_text.lower() in ("exit", "quit", "stop", "थांब", "बंद"):
            speaker.speak("अलविदा!", lang=detected_lang)
            return False

        # Step 3: Brain reasoning
        print("[STATUS: THINKING] Jarvis is processing response...")
        t_brain_start = time.time()
        reply_text = brain.chat(user_text)
        t_reply_ready = time.time()

        # Step 4: Measure delay from end of speech to start of reply
        delay_seconds = t_reply_ready - speech_end_time
        speech_end_formatted = format_timestamp(speech_end_time)
        reply_start_formatted = format_timestamp(t_reply_ready)

        print(
            f"\n[LATENCY METRICS] "
            f"Speech ended: {speech_end_formatted} | "
            f"Reply started: {reply_start_formatted} | "
            f"Response Latency: {delay_seconds:.3f}s"
        )

        # Step 5: Speak reply aloud
        print("[STATUS: SPEAKING]")
        speaker.speak(reply_text, lang=detected_lang)
        print("[STATUS: IDLE]")

    except KeyboardInterrupt:
        print("\nTurn interrupted by user.")
        speaker.stop()
    except Exception as exc:
        print(f"\n[ERROR]: Voice loop issue: {exc}")

    return True


def main() -> None:
    """Main voice loop entry point."""
    print("=" * 60)
    print("      PROJECT JARVIS - MULTILINGUAL VOICE ASSISTANT")
    print("       (English · Hindi / हिंदी · Marathi / मराठी)")
    print("=" * 60)
    print("Features active:")
    print("  • Speech-to-Text: faster-whisper (Base model, CPU int8)")
    print("  • Multilingual Engine: Auto language detection ('en', 'hi', 'mr')")
    print("  • Neural TTS: edge-tts (Guy, Madhur, Manohar)")
    print("  • Low-Latency Pipeline: listen -> brain -> speak")
    print("=" * 60)

    auto_mode = "--auto" in sys.argv
    running = True

    try:
        while running:
            running = run_voice_turn(auto_listen=auto_mode)
            if auto_mode:
                time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nJarvis shutting down. Goodbye!")


if __name__ == "__main__":
    main()
