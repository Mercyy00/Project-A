"""Text-to-Speech (TTS) module for Project JARVIS.

Authored by Akanksha (Voice TTS Engineer) with Pair B integration.
Supports high-quality multilingual neural voices (English, Hindi, Marathi)
via edge-tts, with pygame playback, hotkey stop(), and offline pyttsx3 fallback.
"""

from __future__ import annotations

import asyncio
import os
import sys
import tempfile
import time
from pathlib import Path
from typing import Final

# Ensure project root is in sys.path
_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

try:
    import edge_tts
except ImportError:
    edge_tts = None  # type: ignore

try:
    import pygame
    pygame.mixer.init()
except Exception:
    pygame = None  # type: ignore

try:
    import pyttsx3
except ImportError:
    pyttsx3 = None  # type: ignore

from voice.lang import detect_language


DEFAULT_VOICE_EN: Final[str] = os.getenv("TTS_VOICE_EN", "en-US-GuyNeural")
DEFAULT_VOICE_HI: Final[str] = os.getenv("TTS_VOICE_HI", "hi-IN-MadhurNeural")
DEFAULT_VOICE_MR: Final[str] = os.getenv("TTS_VOICE_MR", "mr-IN-ManoharNeural")

VOICE_MAP: Final[dict[str, str]] = {
    "en": DEFAULT_VOICE_EN,
    "hi": DEFAULT_VOICE_HI,
    "mr": DEFAULT_VOICE_MR,
}


class TTSError(Exception):
    """Base exception for Text-to-Speech errors."""


class JarvisSpeaker:
    """Multilingual speaker for Project JARVIS."""

    def __init__(self) -> None:
        self.voices = {
            "en": os.getenv("TTS_VOICE_EN", DEFAULT_VOICE_EN),
            "hi": os.getenv("TTS_VOICE_HI", DEFAULT_VOICE_HI),
            "mr": os.getenv("TTS_VOICE_MR", DEFAULT_VOICE_MR),
        }
        self.temp_dir = Path("temp_audio")
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self._is_speaking = False

    def get_voice_for_language(self, lang: str | None, text: str) -> str:
        """Select voice code based on specified language or auto-detected language."""
        if not lang:
            lang = detect_language(text)
        return self.voices.get(lang, self.voices["en"])

    async def _generate_audio_edge(self, text: str, voice: str, output_path: Path) -> bool:
        """Generate audio file using edge-tts asynchronously."""
        if edge_tts is None:
            return False
        try:
            communicate = edge_tts.Communicate(text, voice)
            await communicate.save(str(output_path))
            return output_path.is_file() and output_path.stat().st_size > 0
        except Exception as exc:
            print(f"Notice: edge-tts generation failed ({exc}).")
            return False

    def _speak_offline_fallback(self, text: str) -> None:
        """Fallback to pyttsx3 offline speech synthesis."""
        if pyttsx3 is None:
            print(f"[SPEECH OFFLINE]: {text}")
            return
        try:
            engine = pyttsx3.init()
            engine.setProperty("rate", 170)
            engine.say(text)
            engine.runAndWait()
        except Exception as exc:
            print(f"Offline TTS fallback error: {exc}")

    def speak_to_file(self, text: str, lang: str | None = None) -> str:
        """Synthesize speech and save to an audio file (.mp3).

        Args:
            text: Text to synthesize.
            lang: Language code ('en', 'hi', 'mr') or None for auto-detection.

        Returns:
            Absolute path string to the generated audio file.
        """
        clean_text = text.strip()
        if not clean_text:
            return ""

        voice = self.get_voice_for_language(lang, clean_text)
        file_name = f"speech_{int(time.time() * 1000)}.mp3"
        out_path = self.temp_dir / file_name

        try:
            # Run async edge-tts generation synchronously
            asyncio.run(self._generate_audio_edge(clean_text, voice, out_path))
            if out_path.is_file():
                return str(out_path.resolve())
        except Exception as exc:
            print(f"Failed to generate speech file: {exc}")

        return ""

    def speak(self, text: str, lang: str | None = None) -> None:
        """Speak text aloud using natural neural voice or offline fallback.

        Args:
            text: The text to speak.
            lang: Optional language code ('en', 'hi', 'mr'). Auto-detects if None.
        """
        clean_text = text.strip()
        if not clean_text:
            return

        print(f"\n[JARVIS SPEAKING]: {clean_text}")

        # Try edge-tts first
        audio_file = self.speak_to_file(clean_text, lang=lang)
        if audio_file and Path(audio_file).is_file():
            self._play_file(audio_file)
        else:
            # Fallback to offline engine
            self._speak_offline_fallback(clean_text)

    def _play_file(self, file_path: str) -> None:
        """Play generated MP3 using pygame mixer."""
        if pygame is None:
            self._speak_offline_fallback(file_path)
            return

        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()

            pygame.mixer.music.load(file_path)
            self._is_speaking = True
            pygame.mixer.music.play()

            # Wait while audio is playing, allowing stop() to interrupt
            while pygame.mixer.music.get_busy() and self._is_speaking:
                time.sleep(0.05)

        except Exception as exc:
            print(f"Warning: Audio playback issue: {exc}")
        finally:
            self._is_speaking = False

    def stop(self) -> None:
        """Halt speech playback immediately (e.g. on hotkey interrupt)."""
        self._is_speaking = False
        if pygame is not None and pygame.mixer.get_init():
            try:
                pygame.mixer.music.stop()
                print("\n[SPEECH STOPPED BY USER]")
            except Exception:
                pass


# Global singleton instance
_default_speaker: JarvisSpeaker | None = None


def get_speaker() -> JarvisSpeaker:
    """Return the shared JarvisSpeaker instance."""
    global _default_speaker
    if _default_speaker is None:
        _default_speaker = JarvisSpeaker()
    return _default_speaker


def speak(text: str, lang: str | None = None) -> None:
    """Module-level convenience function to speak text."""
    get_speaker().speak(text, lang)


def stop() -> None:
    """Module-level convenience function to stop playback."""
    get_speaker().stop()


def speak_to_file(text: str, lang: str | None = None) -> str:
    """Module-level convenience function to synthesize to audio file."""
    return get_speaker().speak_to_file(text, lang)
