"""Speech-to-Text (STT) module for Project JARVIS.
Ported from and powered by Mark LVI (core/stt.py & providers/stt_whisper.py).

Features:
- Offline transcription via faster-whisper with greedy decoding (beam_size=1)
- condition_on_previous_text=False (eliminates hallucinations and language bleeding)
- VAD silence filtering (min_silence_duration_ms=300)
- Streaming Vosk STT support
- Direct numpy array transcription (zero ffmpeg / disk dependency)
- Backward-compatible Transcriber interface for server & tests
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Final, Optional

import numpy as np

# Suppress Hugging Face symlink warnings on Windows
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

try:
    from faster_whisper import WhisperModel
except ImportError:
    WhisperModel = None  # type: ignore

try:
    import sounddevice as sd
except ImportError:
    sd = None  # type: ignore

try:
    import soundfile as sf
except ImportError:
    sf = None  # type: ignore

from voice.lang import detect_language

DEFAULT_SAMPLE_RATE: Final[int] = 16000
DEFAULT_SILENCE_SECONDS: Final[float] = float(os.getenv("SILENCE_SECONDS", "1.2"))
DEFAULT_MAX_SECONDS: Final[int] = 15
DEFAULT_MIC_DURATION: Final[int] = 4

WHISPER_INITIAL_PROMPT: Final[str] = (
    "Jarvis, J.A.R.V.I.S., Hindi, Marathi, namaste, open, search, notepad, date, time"
)


class STTError(Exception):
    """Base exception for Speech-to-Text operations."""


class MicrophoneError(STTError):
    """Raised when the microphone is unavailable, busy, or fails to record."""


class ModelLoadError(STTError):
    """Raised when loading or downloading the Whisper model fails."""


class AudioFileError(STTError):
    """Raised when an audio file cannot be found or read."""


class WhisperSTT:
    """Offline transcription using faster-whisper (Mark LVI core engine)."""

    def __init__(self, model_name: str = "base", language: str | None = None):
        print(f"[STT] Loading Whisper '{model_name}'…")
        if WhisperModel is None:
            raise ModelLoadError("faster-whisper is not installed. Run 'pip install faster-whisper'.")

        try:
            import torch
            device = "cuda" if torch.cuda.is_available() else "cpu"
            compute = "float16" if device == "cuda" else "int8"
        except Exception:
            device, compute = "cpu", "int8"

        try:
            self._model = WhisperModel(model_name, device=device, compute_type=compute)
        except Exception as _first_err:
            _e = str(_first_err).lower()
            _offline_keywords = (
                "offline", "not found", "cache", "localentry",
                "does not exist", "outgoing", "local_files_only",
            )
            if any(k in _e for k in _offline_keywords):
                print(f"[STT] Whisper '{model_name}' not in local cache — downloading…")
                os.environ.pop("HF_HUB_OFFLINE", None)
                os.environ.pop("TRANSFORMERS_OFFLINE", None)
                os.environ.pop("HF_DATASETS_OFFLINE", None)
                try:
                    self._model = WhisperModel(model_name, device=device, compute_type=compute)
                except Exception as _dl_err:
                    raise ModelLoadError(
                        f"Whisper '{model_name}' model download failed: {_dl_err}"
                    ) from _dl_err
            else:
                try:
                    self._model = WhisperModel(model_name, device=device, compute_type="default")
                except Exception as fallback_err:
                    raise ModelLoadError(f"Whisper load failed: {fallback_err}") from fallback_err

        self._language = None if (not language or language.strip().lower() == "auto") else language.strip().lower()
        print(f"[STT] Whisper '{model_name}' ready ({device})")

    def transcribe(self, audio: np.ndarray, language: str | None = None) -> str:
        """Transcribe a float32 mono 16 kHz numpy array. Returns transcript string."""
        lang = language or self._language
        try:
            segments, _ = self._model.transcribe(
                audio,
                language=lang,
                beam_size=1,                       # greedy — 2-3x faster
                best_of=1,
                condition_on_previous_text=False,  # no hallucinations
                vad_filter=True,
                vad_parameters={"min_silence_duration_ms": 300},
                initial_prompt=WHISPER_INITIAL_PROMPT,
            )
            return " ".join(s.text for s in segments).strip()
        except Exception as e:
            print(f"[STT] Transcription error: {e}")
            raise STTError(str(e)) from e


class VoskSTT:
    """Streaming transcription using Vosk (Mark LVI core engine)."""

    def __init__(self, model_path: str | None = None, language: str = "en-us"):
        from vosk import Model, KaldiRecognizer
        print("[STT] Loading Vosk model…")
        if model_path:
            model = Model(model_path)
        else:
            lang = language.strip().lower() if language and language.strip().lower() != "auto" else "en-us"
            model = Model(lang=lang)
        self._rec = KaldiRecognizer(model, 16000)
        print("[STT] Vosk ready.")

    def process_chunk(self, audio_bytes: bytes) -> tuple[str, bool]:
        """Feed raw int16 LE PCM bytes. Returns (text, is_final)."""
        if self._rec.AcceptWaveform(audio_bytes):
            result = json.loads(self._rec.Result())
            return result.get("text", ""), True
        partial = json.loads(self._rec.PartialResult())
        return partial.get("partial", ""), False


class Transcriber:
    """Unified Transcriber adapter wrapping WhisperSTT for Project JARVIS."""

    def __init__(
        self,
        model_size: str | None = None,
        device: str | None = None,
        compute_type: str | None = None,
    ) -> None:
        self.model_size: str = model_size or os.getenv("WHISPER_MODEL", "base")
        self.device: str = device or os.getenv("WHISPER_DEVICE", "cpu")
        self.compute_type: str = compute_type or os.getenv("WHISPER_COMPUTE_TYPE", "int8")
        self._model: Any = None
        self._engine: Optional[WhisperSTT] = None

    def _ensure_model_loaded(self) -> Any:
        if self._model is not None:
            return self._model
        if self._engine is None:
            self._engine = WhisperSTT(model_name=self.model_size)
        self._model = self._engine._model
        return self._model

    def record_audio(
        self,
        duration_seconds: float,
        sample_rate: int = DEFAULT_SAMPLE_RATE,
    ) -> np.ndarray:
        if sd is None:
            raise MicrophoneError("sounddevice package is missing. Install sounddevice.")
        num_samples = int(duration_seconds * sample_rate)
        try:
            audio = sd.rec(
                num_samples,
                samplerate=sample_rate,
                channels=1,
                dtype="float32",
                blocking=True,
            )
            return audio.flatten()
        except Exception as exc:
            err_msg = str(exc).lower()
            if "busy" in err_msg or "in use" in err_msg:
                raise MicrophoneError(
                    "Audio device busy: Another application is using the microphone."
                ) from exc
            raise MicrophoneError(f"Microphone recording failed: {exc}") from exc

    def transcribe_mic(self, duration_seconds: int = DEFAULT_MIC_DURATION) -> str:
        audio = self.record_audio(duration_seconds=float(duration_seconds))
        model = self._ensure_model_loaded()
        try:
            segments, _ = model.transcribe(
                audio,
                beam_size=1,
                best_of=1,
                condition_on_previous_text=False,
                vad_filter=True,
                initial_prompt=WHISPER_INITIAL_PROMPT,
            )
            return " ".join(seg.text.strip() for seg in segments).strip()
        except Exception as exc:
            raise STTError(f"Transcription failed: {exc}") from exc

    def transcribe_file(self, path: str | Path, language: str | None = None) -> dict[str, str]:
        file_path = Path(path)
        if not file_path.is_file():
            raise AudioFileError(f"Audio file not found: {file_path}")

        model = self._ensure_model_loaded()
        try:
            segments, info = model.transcribe(
                str(file_path),
                language=language,
                beam_size=1,
                best_of=1,
                condition_on_previous_text=False,
                vad_filter=True,
                vad_parameters={"min_silence_duration_ms": 300},
                initial_prompt=WHISPER_INITIAL_PROMPT,
            )
            text = " ".join(s.text for s in segments).strip()
            det_lang = language or getattr(info, "language", "en")
            return {"text": text, "language": det_lang}
        except Exception as e:
            raise STTError(f"File transcription failed: {e}") from e

    def listen(
        self,
        max_seconds: int | float = DEFAULT_MAX_SECONDS,
        silence_seconds: float = DEFAULT_SILENCE_SECONDS,
        timeout: float | None = None,
    ) -> dict[str, str]:
        if sd is None:
            raise MicrophoneError("sounddevice is not available.")

        chunk_duration = 0.1
        chunk_samples = int(DEFAULT_SAMPLE_RATE * chunk_duration)
        max_chunks = int(max_seconds / chunk_duration)
        silence_chunks = int(silence_seconds / chunk_duration)

        recorded_chunks: list[np.ndarray] = []
        silence_count = 0
        speech_started = False
        silence_threshold = 0.015

        try:
            with sd.InputStream(samplerate=DEFAULT_SAMPLE_RATE, channels=1, dtype="float32") as stream:
                for _ in range(max_chunks):
                    chunk, _ = stream.read(chunk_samples)
                    chunk_flat = chunk.flatten()
                    recorded_chunks.append(chunk_flat)
                    energy = float(np.max(np.abs(chunk_flat)))

                    if energy > silence_threshold:
                        speech_started = True
                        silence_count = 0
                    elif speech_started:
                        silence_count += 1
                        if silence_count >= silence_chunks:
                            break
        except Exception as exc:
            raise MicrophoneError(f"Streaming listen failed: {exc}") from exc

        if not recorded_chunks:
            return {"text": "", "language": "en", "speech_end_time": time.time()}

        full_audio = np.concatenate(recorded_chunks)
        if not speech_started and np.max(np.abs(full_audio)) < silence_threshold:
            return {"text": "", "language": "en", "speech_end_time": time.time()}

        model = self._ensure_model_loaded()
        try:
            segments, info = model.transcribe(
                full_audio,
                beam_size=1,
                best_of=1,
                condition_on_previous_text=False,
                vad_filter=True,
                initial_prompt=WHISPER_INITIAL_PROMPT,
            )
            text = " ".join(seg.text.strip() for seg in segments).strip()
            det_lang = getattr(info, "language", "en") if info else "en"
            return {"text": text, "language": det_lang, "speech_end_time": time.time()}
        except Exception as exc:
            raise STTError(f"Listen transcription failed: {exc}") from exc


# Global Transcriber Singleton
_transcriber_instance: Optional[Transcriber] = None


def get_transcriber() -> Transcriber:
    global _transcriber_instance
    if _transcriber_instance is None:
        _transcriber_instance = Transcriber()
    return _transcriber_instance


def transcribe_mic(duration_seconds: int = DEFAULT_MIC_DURATION) -> str:
    return get_transcriber().transcribe_mic(duration_seconds=duration_seconds)


def transcribe_file(path: str | Path, language: str | None = None) -> dict[str, str]:
    return get_transcriber().transcribe_file(path, language=language)


def listen(
    max_seconds: int | float = DEFAULT_MAX_SECONDS,
    silence_seconds: float = DEFAULT_SILENCE_SECONDS,
) -> dict[str, str]:
    return get_transcriber().listen(max_seconds=max_seconds, silence_seconds=silence_seconds)
