"""Microphone, WAV audio validation, and recording check utilities.

Provides checks for microphone availability, device enumeration,
16 kHz mono recording, playback verification, and WAV validation.
Gracefully handles 'Audio device busy' and missing device errors.
"""

from __future__ import annotations

import time
import wave
from pathlib import Path
from typing import Any

import numpy as np

try:
    import sounddevice as sd
except ImportError:
    sd = None  # type: ignore

try:
    import speech_recognition as sr
except ImportError:
    sr = None  # type: ignore


DEFAULT_SAMPLE_RATE: int = 16000  # 16 kHz mono per JARVIS specification
DEFAULT_CHANNELS: int = 1


def check_microphone() -> tuple[bool, str]:
    """Check whether an audio input device (microphone) is available."""
    if sd is not None:
        try:
            devices = sd.query_devices()
            input_devices = [d for d in devices if d.get("max_input_channels", 0) > 0]
            if input_devices:
                default_in = sd.default.device[0]
                dev_name = sd.query_devices(default_in)["name"] if default_in != -1 else input_devices[0]["name"]
                return True, f"Microphone is available: '{dev_name}'"
            return False, "No audio input devices found."
        except Exception as exc:
            err_msg = str(exc).lower()
            if "busy" in err_msg or "in use" in err_msg:
                return False, "Audio device busy: Another application is using the microphone."
            return False, f"Microphone unavailable: {exc}"

    if sr is not None:
        try:
            with sr.Microphone():
                return True, "Microphone is available."
        except Exception as exc:
            return False, f"Microphone unavailable: {exc}"

    return False, "Neither sounddevice nor speech_recognition is installed."


def list_microphones() -> list[dict[str, Any]]:
    """List all available audio input devices."""
    devices: list[dict[str, Any]] = []

    if sd is not None:
        try:
            all_devices = sd.query_devices()
            for idx, dev in enumerate(all_devices):
                max_in = dev.get("max_input_channels", 0)
                if max_in > 0:
                    devices.append({
                        "index": idx,
                        "name": dev.get("name", "Unknown"),
                        "channels": max_in,
                        "default_samplerate": dev.get("default_samplerate", DEFAULT_SAMPLE_RATE),
                    })
            return devices
        except Exception as exc:
            print(f"Warning: sounddevice device query failed: {exc}")

    # Fallback to pyaudio if available
    try:
        import pyaudio
        audio = pyaudio.PyAudio()
        try:
            for index in range(audio.get_device_count()):
                info = audio.get_device_info_by_index(index)
                if info.get("maxInputChannels", 0) > 0:
                    devices.append({
                        "index": index,
                        "name": info.get("name", "Unknown"),
                        "channels": info.get("maxInputChannels", 0),
                    })
        finally:
            audio.terminate()
    except Exception:
        pass

    return devices


def record_sample(
    duration_seconds: float = 3.0,
    sample_rate: int = DEFAULT_SAMPLE_RATE,
    channels: int = DEFAULT_CHANNELS,
) -> np.ndarray:
    """Record audio from the microphone at specified sample rate and channels.

    Args:
        duration_seconds: Duration to record in seconds (default 3.0).
        sample_rate: Audio sampling rate (default 16000 Hz).
        channels: Number of channels (default 1 for mono).

    Returns:
        Numpy array containing recorded float32 audio samples.

    Raises:
        RuntimeError: If sounddevice is missing or recording fails.
    """
    if sd is None:
        raise RuntimeError("sounddevice is required for recording. Please install sounddevice.")

    num_samples = int(duration_seconds * sample_rate)
    try:
        print(f"Recording {duration_seconds} seconds of audio at {sample_rate} Hz mono...")
        audio_data = sd.rec(
            num_samples,
            samplerate=sample_rate,
            channels=channels,
            dtype="float32",
            blocking=True,
        )
        return audio_data.flatten()
    except Exception as exc:
        err_msg = str(exc).lower()
        if "busy" in err_msg or "in use" in err_msg:
            raise RuntimeError(
                "Audio device busy: Microphone is held by another process or exclusive mode."
            ) from exc
        raise RuntimeError(f"Failed to record audio: {exc}") from exc


def play_sample(
    audio_data: np.ndarray,
    sample_rate: int = DEFAULT_SAMPLE_RATE,
) -> None:
    """Play audio samples back through speakers.

    Args:
        audio_data: Float32 audio samples array.
        sample_rate: Sampling rate in Hz.
    """
    if sd is None:
        raise RuntimeError("sounddevice is required for playback.")
    try:
        print("Playing back recorded audio through speakers...")
        sd.play(audio_data, samplerate=sample_rate, blocking=True)
        print("Playback finished.")
    except Exception as exc:
        print(f"Warning: Playback error: {exc}")


def test_audio_loopback(duration_seconds: float = 3.0) -> bool:
    """Run interactive audio check: records for duration and plays back.

    Per Day 1 specification:
    'run python voice/audio_check.py and speak for 3 seconds.
     Your voice plays back through your speakers.'
    """
    available, msg = check_microphone()
    print(f"Device status: {msg}")
    if not available:
        print("Microphone not ready. Skipping loopback.")
        return False

    try:
        print("\n=== Audio Loopback Test (Day 1) ===")
        print(f"Prepare to speak for {duration_seconds} seconds...")
        for count in range(3, 0, -1):
            print(f"Starting in {count}...", end="\r", flush=True)
            time.sleep(1)
        print("SPEAK NOW! [Listening...]")

        audio = record_sample(duration_seconds=duration_seconds, sample_rate=DEFAULT_SAMPLE_RATE)
        max_amplitude = float(np.max(np.abs(audio)))
        print(f"Recording complete. Peak amplitude: {max_amplitude:.4f}")

        if max_amplitude < 0.005:
            print("Notice: Very low audio signal detected. Please check mic volume or mute switch.")

        print("Now playing back through your speakers...")
        play_sample(audio, sample_rate=DEFAULT_SAMPLE_RATE)
        print("Loopback test successful!\n")
        return True
    except Exception as exc:
        print(f"Audio test failed: {exc}")
        return False


def check_wav_file(file_path: str | Path) -> dict[str, Any]:
    """Check the basic properties of a WAV file."""
    path = Path(file_path)

    if not path.is_file():
        return {
            "valid": False,
            "error": "Audio file not found.",
        }

    try:
        with wave.open(str(path), "rb") as audio:
            frames = audio.getnframes()
            sample_rate = audio.getframerate()

            if frames == 0 or sample_rate == 0:
                return {
                    "valid": False,
                    "error": "Audio file is empty or invalid.",
                }

            return {
                "valid": True,
                "duration_seconds": round(frames / sample_rate, 2),
                "sample_rate": sample_rate,
                "channels": audio.getnchannels(),
            }

    except (wave.Error, EOFError, OSError) as exc:
        return {
            "valid": False,
            "error": str(exc),
        }


if __name__ == "__main__":
    is_avail, message = check_microphone()
    print(message)

    if is_avail:
        try:
            mics = list_microphones()
            print(f"Found {len(mics)} input device(s):")
            for dev in mics:
                print(f"  [{dev['index']}] {dev['name']} ({dev['channels']} ch)")
            
            # Run loopback test
            test_audio_loopback(3.0)
        except Exception as e:
            print(f"Audio check encountered an issue: {e}")
