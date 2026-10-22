"""Text-to-Speech (TTS) module for Project JARVIS.

Authored by Akanksha (Voice TTS Engineer) with Pair B integration.
Calibrated for native Indian voices to prevent American phonetic mangling:
  - Indian English: en-IN-PrabhatNeural (or en-IN-NeerjaNeural)
  - Hindi: hi-IN-MadhurNeural (or hi-IN-SwaraNeural)
  - Marathi: mr-IN-ManoharNeural (or mr-IN-AarohiNeural)
Features SSML cadence normalization, strict overlap prevention,
and seamless pygame playback with offline fallback.
"""

from __future__ import annotations

import asyncio
import os
import sys
import tempfile
import threading
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
    if not pygame.mixer.get_init():
        pygame.mixer.init()
except Exception:
    pygame = None  # type: ignore

try:
    import pyttsx3
except ImportError:
    pyttsx3 = None  # type: ignore

from voice.lang import detect_code_switching, detect_language


# B2.1: Enforce native Microsoft Edge Neural Indian voices (No American phonetics)
DEFAULT_VOICE_EN: Final[str] = os.getenv("TTS_VOICE_EN", "en-IN-PrabhatNeural")
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
    """Multilingual speaker for Project JARVIS with overlap prevention."""

    def __init__(self) -> None:
        self.voices = {
            "en": os.getenv("TTS_VOICE_EN", DEFAULT_VOICE_EN),
            "hi": os.getenv("TTS_VOICE_HI", DEFAULT_VOICE_HI),
            "mr": os.getenv("TTS_VOICE_MR", DEFAULT_VOICE_MR),
        }
        self.temp_dir = Path("temp_audio")
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self._is_speaking = False
        self._lock = threading.Lock()

    @property
    def is_speaking(self) -> bool:
        """Return True if speech audio is currently playing."""
        return self._is_speaking

    def get_voice_for_language(self, lang: str | None, text: str) -> str:
        """Select appropriate neural Indian voice code based on script & dialect.

        B2.1 & B2.2: Routes Indian English / Hinglish to en-IN-PrabhatNeural,
        Devanagari Hindi to hi-IN-MadhurNeural, Devanagari Marathi to mr-IN-ManoharNeural.
        """
        dialect_info = detect_code_switching(text)

        # If user explicitly asked for a language
        if lang in self.voices:
            return self.voices[lang]

        # Automatic script-aware routing
        if dialect_info["dialect"] == "devanagari_mr":
            return self.voices.get("mr", DEFAULT_VOICE_MR)
        if dialect_info["dialect"] == "devanagari_hi":
            return self.voices.get("hi", DEFAULT_VOICE_HI)

        # For English, Hinglish, and Marathish in Roman script:
        # en-IN-PrabhatNeural natively pronounces Indian vocabulary without American phonetic mangling
        return self.voices.get("en", DEFAULT_VOICE_EN)

    def _format_ssml_text(self, text: str) -> str:
        """Format text with natural pacing to avoid robotic cadence."""
        clean = text.strip()
        # Edge-tts supports direct text or SSML. Using clean punctuation ensures natural cadence.
        if not clean.endswith((".", "!", "?", "।")):
            clean += "."
        return clean

    async def _generate_audio_edge(self, text: str, voice: str, output_path: Path) -> bool:
        """Generate audio file using edge-tts asynchronously with rate tuning."""
        if edge_tts is None:
            return False
        try:
            formatted_text = self._format_ssml_text(text)
            # rate='+0%' and pitch='+0Hz' for standard natural human cadence
            communicate = edge_tts.Communicate(formatted_text, voice, rate="+0%", pitch="+0Hz")
            await communicate.save(str(output_path))
            return output_path.is_file() and output_path.stat().st_size > 0
        except Exception as exc:
            print(f"Notice: edge-tts generation error ({exc}).")
            return False

    def _speak_offline_fallback(self, text: str) -> None:
        """Fallback to pyttsx3 offline speech synthesis."""
        if pyttsx3 is None:
            print(f"[SPEECH OFFLINE]: {text}")
            return
        try:
            self._is_speaking = True
            engine = pyttsx3.init()
            engine.setProperty("rate", 165)
            engine.say(text)
            engine.runAndWait()
        except Exception as exc:
            print(f"Offline TTS fallback error: {exc}")
        finally:
            self._is_speaking = False

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
            asyncio.run(self._generate_audio_edge(clean_text, voice, out_path))
            if out_path.is_file():
                return str(out_path.resolve())
        except Exception as exc:
            print(f"Failed to generate speech file: {exc}")

        return ""

    def speak(self, text: str, lang: str | None = None) -> None:
        """Speak text aloud with strict overlap prevention.

        Haults any currently playing speech before initiating new playback,
        and blocks until playback has finished completely.

        Args:
            text: The text to speak.
            lang: Optional language code ('en', 'hi', 'mr').
        """
        clean_text = text.strip()
        if not clean_text:
            return

        with self._lock:
            # Overlap prevention: Stop any active audio immediately
            self.stop()

            print(f"\n[JARVIS SPEAKING]: {clean_text}")

            audio_file = self.speak_to_file(clean_text, lang=lang)
            if audio_file and Path(audio_file).is_file():
                self._play_file(audio_file)
            else:
                self._speak_offline_fallback(clean_text)

    def _play_file(self, file_path: str) -> None:
        """Play generated MP3 using pygame mixer with complete blocking."""
        if pygame is None:
            self._speak_offline_fallback(file_path)
            return

        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()

            pygame.mixer.music.load(file_path)
            self._is_speaking = True
            pygame.mixer.music.play()

            # Strictly wait while audio is playing (prevents audio overlapping)
            while pygame.mixer.music.get_busy() and self._is_speaking:
                time.sleep(0.04)

        except Exception as exc:
            print(f"Warning: Audio playback issue: {exc}")
        finally:
            if pygame is not None and pygame.mixer.get_init():
                try:
                    pygame.mixer.music.unload()
                except Exception:
                    pass
            self._is_speaking = False
            # Guard interval: wait 0.3s after sound finishes to prevent mic recording speaker echo
            time.sleep(0.3)

    def stop(self) -> None:
        """Halt speech playback immediately and reset state."""
        self._is_speaking = False
        if pygame is not None and pygame.mixer.get_init():
            try:
                if pygame.mixer.music.get_busy():
                    pygame.mixer.music.stop()
                    pygame.mixer.music.unload()
                    print("\n[SPEECH STOPPED]")
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
