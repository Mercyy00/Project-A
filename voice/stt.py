"""Speech-to-Text (STT) module using faster-whisper for Project JARVIS.

Authored by Madhuri (Voice Engineer - STT).
Supports English, Hindi, and Marathi transcription from microphone
and audio files with automatic language detection.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Final

# Ensure project root is in sys.path
_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

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


DEFAULT_SAMPLE_RATE: Final[int] = 16000  # 16 kHz mono standard
DEFAULT_SILENCE_SECONDS: Final[float] = 1.5
DEFAULT_MAX_SECONDS: Final[int] = 10
DEFAULT_MIC_DURATION: Final[int] = 4


class STTError(Exception):
    """Base exception for Speech-to-Text operations."""


class MicrophoneError(STTError):
    """Raised when the microphone is unavailable, busy, or fails to record."""


class ModelLoadError(STTError):
    """Raised when loading or downloading the Whisper model fails."""


class AudioFileError(STTError):
    """Raised when an audio file cannot be found or read."""


class Transcriber:
    """Manages Whisper model loading, audio recording, and transcription."""

    def __init__(
        self,
        model_size: str | None = None,
        device: str | None = None,
        compute_type: str | None = None,
    ) -> None:
        """Initialize the Transcriber with model configuration.

        Args:
            model_size: Whisper model size ('tiny', 'base', 'small', etc.).
                        Defaults to WHISPER_MODEL env var or 'base'.
            device: Computing device ('cpu', 'cuda'). Defaults to WHISPER_DEVICE or 'cpu'.
            compute_type: Quantization type ('int8', 'float32', 'default').
                          Defaults to WHISPER_COMPUTE_TYPE or 'int8'.
        """
        self.model_size: str = model_size or os.getenv("WHISPER_MODEL", "base")
        self.device: str = device or os.getenv("WHISPER_DEVICE", "cpu")
        self.compute_type: str = compute_type or os.getenv("WHISPER_COMPUTE_TYPE", "int8")
        self._model: Any = None

    def _ensure_model_loaded(self) -> Any:
        """Load the faster-whisper model lazily with robust error handling."""
        if self._model is not None:
            return self._model

        if WhisperModel is None:
            raise ModelLoadError(
                "faster-whisper is not installed. Run 'pip install faster-whisper'."
            )

        print(
            f"Loading Whisper model '{self.model_size}' "
            f"(device={self.device}, compute_type={self.compute_type})..."
        )
        try:
            self._model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type,
            )
        except Exception as exc:
            # If int8 is not supported by CPU, fallback gracefully to 'default' or 'float32'
            if self.compute_type == "int8":
                print(f"Warning: compute_type='int8' failed ({exc}). Retrying with 'default'...")
                try:
                    self.compute_type = "default"
                    self._model = WhisperModel(
                        self.model_size,
                        device=self.device,
                        compute_type="default",
                    )
                    return self._model
                except Exception as fallback_exc:
                    raise ModelLoadError(
                        f"Failed to load Whisper model '{self.model_size}': {fallback_exc}. "
                        "Check your internet connection if downloading for the first time."
                    ) from fallback_exc

            raise ModelLoadError(
                f"Failed to load Whisper model '{self.model_size}': {exc}. "
                "Check your internet connection if downloading for the first time."
            ) from exc

        return self._model

    def record_audio(
        self,
        duration_seconds: float,
        sample_rate: int = DEFAULT_SAMPLE_RATE,
    ) -> np.ndarray:
        """Record audio from the microphone for a given duration.

        Args:
            duration_seconds: Duration in seconds to record.
            sample_rate: Sampling frequency in Hz (default 16000).

        Returns:
            Numpy float32 1D array of audio samples.

        Raises:
            MicrophoneError: If recording fails or microphone is busy.
        """
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
                    "Audio device busy: Another application is using the microphone. "
                    "Close other apps using the mic and try again."
                ) from exc
            raise MicrophoneError(f"Microphone recording failed: {exc}") from exc

    def transcribe_mic(self, duration_seconds: int = DEFAULT_MIC_DURATION) -> str:
        """Record from the default microphone and return the transcribed text.

        Args:
            duration_seconds: Duration to listen in seconds (default 4).

        Returns:
            Transcribed text string.
        """
        print(f"Listening for {duration_seconds} seconds...")
        audio = self.record_audio(duration_seconds=float(duration_seconds))
        
        # Check if audio has minimal energy
        if np.max(np.abs(audio)) < 0.005:
            print("Notice: Very low audio detected.")

        model = self._ensure_model_loaded()
        try:
            segments, _ = model.transcribe(
                audio,
                beam_size=5,
                vad_filter=True,
            )
            text = " ".join(seg.text.strip() for seg in segments).strip()
            return text
        except Exception as exc:
            raise STTError(f"Transcription failed: {exc}") from exc

    def _convert_ogg_if_needed(self, file_path: Path) -> Path:
        """Ensure .ogg or unsupported audio files can be read.

        If external ffmpeg is available and file is .ogg, convert to .wav as fallback.
        Otherwise, returns original path (faster-whisper/PyAV natively reads .ogg).
        """
        if file_path.suffix.lower() == ".ogg" and shutil.which("ffmpeg"):
            temp_wav = Path(tempfile.gettempdir()) / f"{file_path.stem}_converted_{int(time.time())}.wav"
            cmd = [
                "ffmpeg", "-y", "-i", str(file_path),
                "-ar", str(DEFAULT_SAMPLE_RATE),
                "-ac", "1",
                str(temp_wav),
            ]
            try:
                subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
                if temp_wav.is_file():
                    return temp_wav
            except Exception:
                pass
        return file_path

    def transcribe_file(self, path: str | Path) -> dict[str, str]:
        """Convert a local audio file into text and detected language.

        Supports WAV, MP3, OGG, M4A, FLAC, and other standard formats.

        Args:
            path: Path to the audio file.

        Returns:
            Dictionary: {'text': str, 'language': str} where language is 'en', 'hi', or 'mr'.

        Raises:
            AudioFileError: If file does not exist or cannot be read.
            STTError: If transcription fails.
        """
        file_path = Path(path)
        if not file_path.is_file():
            raise AudioFileError(f"Audio file not found: {file_path}")

        target_path = self._convert_ogg_if_needed(file_path)
        model = self._ensure_model_loaded()

        # Attempt decoding: read via soundfile if possible, else path
        try:
            if sf is not None and target_path.suffix.lower() in (".wav", ".flac", ".ogg"):
                try:
                    audio_data, file_sr = sf.read(str(target_path), dtype="float32")
                    if audio_data.ndim > 1:
                        audio_data = np.mean(audio_data, axis=1)
                    if file_sr == DEFAULT_SAMPLE_RATE:
                        segments, info = model.transcribe(audio_data, beam_size=5, vad_filter=True)
                    else:
                        segments, info = model.transcribe(str(target_path), beam_size=5, vad_filter=True)
                except Exception:
                    segments, info = model.transcribe(str(target_path), beam_size=5, vad_filter=True)
            else:
                segments, info = model.transcribe(str(target_path), beam_size=5, vad_filter=True)

            text = " ".join(seg.text.strip() for seg in segments).strip()

            # Determine language using voice.lang detect_language
            detected_lang = detect_language(text)

            # If text is empty, map whisper's own detected language if supported
            if not text and info and hasattr(info, "language"):
                w_lang = getattr(info, "language", "en")
                detected_lang = w_lang if w_lang in ("en", "hi", "mr") else "en"

            return {
                "text": text,
                "language": detected_lang,
            }
        except Exception as exc:
            raise STTError(f"Failed to transcribe file '{file_path}': {exc}") from exc
        finally:
            if target_path != file_path and target_path.exists():
                try:
                    target_path.unlink()
                except OSError:
                    pass

    def listen(
        self,
        max_seconds: int = DEFAULT_MAX_SECONDS,
        silence_seconds: float = DEFAULT_SILENCE_SECONDS,
        sample_rate: int = DEFAULT_SAMPLE_RATE,
        silence_threshold: float = 0.015,
    ) -> dict[str, str]:
        """Record audio from microphone at 16000 Hz mono until silence, then transcribe.

        Records in chunks until approx `silence_seconds` of quiet are detected
        after speech has begun, or until `max_seconds` elapses.

        Args:
            max_seconds: Maximum total recording time (default 10s).
            silence_seconds: Stop recording after this many seconds of silence (default 1.5s).
            sample_rate: Recording sample rate (default 16000 Hz).
            silence_threshold: RMS amplitude threshold below which audio is silence.

        Returns:
            Dictionary: {'text': str, 'language': str}.
        """
        if sd is None:
            raise MicrophoneError("sounddevice is required. Run 'pip install sounddevice'.")

        chunk_duration = 0.1  # 100ms per block
        chunk_samples = int(sample_rate * chunk_duration)
        max_chunks = int(max_seconds / chunk_duration)
        silence_chunks_required = int(silence_seconds / chunk_duration)

        recorded_chunks: list[np.ndarray] = []
        speech_started = False
        silence_chunk_count = 0

        print(f"Listening (max {max_seconds}s, stopping after {silence_seconds}s silence)...")

        try:
            with sd.InputStream(
                samplerate=sample_rate,
                channels=1,
                dtype="float32",
                blocksize=chunk_samples,
            ) as stream:
                for _ in range(max_chunks):
                    data, _ = stream.read(chunk_samples)
                    data_flat = data.flatten()
                    recorded_chunks.append(data_flat)

                    rms = float(np.sqrt(np.mean(data_flat ** 2)))

                    if rms > silence_threshold:
                        speech_started = True
                        silence_chunk_count = 0
                    else:
                        if speech_started:
                            silence_chunk_count += 1
                            if silence_chunk_count >= silence_chunks_required:
                                break

        except Exception as exc:
            err_msg = str(exc).lower()
            if "busy" in err_msg or "in use" in err_msg:
                raise MicrophoneError(
                    "Audio device busy: Microphone is locked by another process."
                ) from exc
            raise MicrophoneError(f"Error while listening from mic: {exc}") from exc

        if not recorded_chunks:
            return {"text": "", "language": "en"}

        full_audio = np.concatenate(recorded_chunks)

        # If speech was never detected above threshold
        if not speech_started and np.max(np.abs(full_audio)) < silence_threshold:
            return {"text": "", "language": "en", "speech_end_time": time.time()}

        speech_end_time = time.time()
        model = self._ensure_model_loaded()
        try:
            segments, info = model.transcribe(
                full_audio,
                beam_size=5,
                vad_filter=True,
            )
            text = " ".join(seg.text.strip() for seg in segments).strip()
            detected_lang = detect_language(text)
            if not text and info and hasattr(info, "language"):
                w_lang = getattr(info, "language", "en")
                detected_lang = w_lang if w_lang in ("en", "hi", "mr") else "en"

            return {
                "text": text,
                "language": detected_lang,
                "speech_end_time": speech_end_time,
            }
        except Exception as exc:
            raise STTError(f"Listen transcription failed: {exc}") from exc


# Global singleton instance for easy module-level calls
_default_transcriber: Transcriber | None = None


def get_transcriber() -> Transcriber:
    """Return the shared default Transcriber instance."""
    global _default_transcriber
    if _default_transcriber is None:
        _default_transcriber = Transcriber()
    return _default_transcriber


def transcribe_mic(duration_seconds: int = DEFAULT_MIC_DURATION) -> str:
    """Record from mic for duration_seconds and return transcribed text."""
    return get_transcriber().transcribe_mic(duration_seconds=duration_seconds)


def transcribe_file(path: str | Path) -> dict[str, str]:
    """Transcribe an audio file and return {'text': str, 'language': str}."""
    return get_transcriber().transcribe_file(path)


def listen(
    max_seconds: int = DEFAULT_MAX_SECONDS,
    silence_seconds: float = DEFAULT_SILENCE_SECONDS,
) -> dict[str, str]:
    """Listen from mic until silence and return {'text': str, 'language': str}."""
    return get_transcriber().listen(
        max_seconds=max_seconds,
        silence_seconds=silence_seconds,
    )


if __name__ == "__main__":
    import sys

    print("=== JARVIS Speech-to-Text Test CLI (Madhuri) ===")
    t = Transcriber()

    if len(sys.argv) > 1 and sys.argv[1] == "--file":
        if len(sys.argv) > 2:
            res = t.transcribe_file(sys.argv[2])
            print(f"Transcript: {res['text']}")
            print(f"Language:   {res['language']}")
        else:
            print("Please provide a file path: python voice/stt.py --file <path>")
    else:
        try:
            print("Press Enter to record 4 seconds of speech, or type 'listen' for silence-based recording:")
            user_choice = input().strip().lower()
            if user_choice == "listen":
                res = t.listen(max_seconds=10, silence_seconds=1.5)
                print(f"\nTranscript: {res['text']}")
                print(f"Language:   {res['language']}")
            else:
                text_out = t.transcribe_mic(duration_seconds=4)
                detected = detect_language(text_out)
                print(f"\nTranscript: {text_out}")
                print(f"Language:   {detected}")
        except KeyboardInterrupt:
            print("\nStopped.")
        except Exception as error:
            print(f"Error: {error}")
