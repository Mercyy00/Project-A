"""Text-to-Speech (TTS) module for Project JARVIS.
Ported from and powered by Mark LVI (core/tts.py & providers/tts_*.py).

Engines supported:
- EdgeTTS: Microsoft Neural TTS with native multilingual & Indian voices
- Kokoro: Offline neural TTS (<50ms latency)
- ElevenLabs: Cloud HD voice
- TTSPlayer: Non-blocking threaded audio playback via sounddevice
"""

from __future__ import annotations

import asyncio
import hashlib
import os
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Final, Optional

from voice.lang import detect_code_switching, detect_language
from voice.echo import mark_speech_active
from core.tts import (
    EdgeTTSEngine,
    ElevenLabsTTSEngine,
    KokoroTTSEngine,
    TTSPlayer,
    _compress_silence,
    _play_audio_bytes,
)

DEFAULT_VOICE_EN: Final[str] = os.getenv("TTS_VOICE_EN", "en-IN-PrabhatNeural")
DEFAULT_VOICE_HI: Final[str] = os.getenv("TTS_VOICE_HI", "hi-IN-MadhurNeural")
DEFAULT_VOICE_MR: Final[str] = os.getenv("TTS_VOICE_MR", "mr-IN-ManoharNeural")


class JarvisSpeaker:
    """Unified Text-to-Speech speaker for JARVIS backed by Mark LVI audio engines."""

    def __init__(self) -> None:
        self.temp_dir: Path = Path("temp_audio")
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self._is_speaking: bool = False
        self._lock: threading.Lock = threading.Lock()
        self._current_player: Optional[TTSPlayer] = None

    @property
    def is_speaking(self) -> bool:
        return self._is_speaking

    def get_voice_for_language(self, lang: str | None = None, text: str = "") -> str:
        if not lang and text:
            lang = detect_language(text)
        lang_norm = (lang or "en").lower().strip()
        if lang_norm.startswith("hi"):
            return DEFAULT_VOICE_HI
        if lang_norm.startswith("mr"):
            return DEFAULT_VOICE_MR
        return DEFAULT_VOICE_EN

    async def _generate_audio_edge(self, text: str, voice: str, out_path: Path) -> bool:
        import edge_tts
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(str(out_path))
        return out_path.is_file() and out_path.stat().st_size > 0

    async def speak_to_file_async(self, text: str, lang: str | None = None) -> str:
        """Synthesize speech asynchronously with MD5 caching and save to audio file (.mp3)."""
        clean_text = text.strip()
        if not clean_text:
            return ""

        voice = self.get_voice_for_language(lang, clean_text)
        cache_hash = hashlib.md5(f"{voice}::{clean_text}".encode("utf-8")).hexdigest()
        cache_path = self.temp_dir / f"tts_cache_{cache_hash}.mp3"
        if cache_path.is_file() and cache_path.stat().st_size > 0:
            return str(cache_path.resolve())

        try:
            success = await self._generate_audio_edge(clean_text, voice, cache_path)
            if success and cache_path.is_file():
                return str(cache_path.resolve())
        except Exception as exc:
            print(f"[TTS] Async speech generation failed: {exc}", file=sys.stderr)

        return ""

    def speak_to_file(self, text: str, lang: str | None = None) -> str:
        """Synthesize speech and save to an audio file (.mp3)."""
        clean_text = text.strip()
        if not clean_text:
            return ""

        voice = self.get_voice_for_language(lang, clean_text)
        cache_hash = hashlib.md5(f"{voice}::{clean_text}".encode("utf-8")).hexdigest()
        cache_path = self.temp_dir / f"tts_cache_{cache_hash}.mp3"
        if cache_path.is_file() and cache_path.stat().st_size > 0:
            return str(cache_path.resolve())

        try:
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None

            if loop and loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                    pool.submit(asyncio.run, self._generate_audio_edge(clean_text, voice, cache_path)).result()
            else:
                asyncio.run(self._generate_audio_edge(clean_text, voice, cache_path))

            if cache_path.is_file() and cache_path.stat().st_size > 0:
                return str(cache_path.resolve())
        except Exception as exc:
            print(f"[TTS] Speech synthesis to file failed: {exc}", file=sys.stderr)

        return ""

    def speak(self, text: str, lang: str | None = None) -> None:
        """Synthesize and play speech synchronously through system speakers."""
        clean_text = text.strip()
        if not clean_text:
            return

        with self._lock:
            self._is_speaking = True

        voice = self.get_voice_for_language(lang, clean_text)
        mark_speech_active(max(1.0, len(clean_text) * 0.08))

        try:
            engine = EdgeTTSEngine(voice=voice)
            engine.speak(clean_text)
        except Exception as exc:
            print(f"[TTS] Direct playback failed: {exc}", file=sys.stderr)
        finally:
            with self._lock:
                self._is_speaking = False

    def stop(self) -> None:
        """Interrupt any ongoing audio playback immediately."""
        try:
            import sounddevice as sd
            sd.stop()
        except Exception:
            pass
        with self._lock:
            self._is_speaking = False


# Global Speaker Singleton
_speaker_instance: Optional[JarvisSpeaker] = None


def get_speaker() -> JarvisSpeaker:
    global _speaker_instance
    if _speaker_instance is None:
        _speaker_instance = JarvisSpeaker()
    return _speaker_instance


def speak(text: str, lang: str | None = None) -> None:
    get_speaker().speak(text, lang=lang)


def speak_to_file(text: str, lang: str | None = None) -> str:
    return get_speaker().speak_to_file(text, lang=lang)


def stop() -> None:
    get_speaker().stop()
