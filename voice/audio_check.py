"""Day 1 Audio Check Utility for Project Jarvis (Aryan -> Madhuri & Akanksha).

Records 3 seconds of audio at 16 kHz mono from the microphone,
verifies audio input levels, and plays it back through the speakers.
Handles 'Audio device busy' errors and provides diagnostic troubleshooting.
"""
from __future__ import annotations

import sys
import time

SAMPLE_RATE = 16000  # 16 kHz mono required by Whisper
DURATION_SECONDS = 3.0


def run_audio_check() -> bool:
    """Record 3 seconds of microphone input and play back to verify hardware."""
    print("=" * 60)
    print(" Project Jarvis - Hardware Audio Verification (Day 1)")
    print("=" * 60)

    try:
        import numpy as np
        import sounddevice as sd
    except ImportError:
        print("\n[ERROR] Required packages 'sounddevice' or 'numpy' are not installed.")
        print("Please run: pip install sounddevice numpy soundfile")
        return False

    try:
        # Check available devices
        devices = sd.query_devices()
        default_in = sd.default.device[0]
        default_out = sd.default.device[1]

        in_name = devices[default_in]["name"] if default_in is not None and default_in >= 0 else "Unknown"
        out_name = devices[default_out]["name"] if default_out is not None and default_out >= 0 else "Unknown"

        print(f"Microphone: {in_name} (Device #{default_in})")
        print(f"Speaker:    {out_name} (Device #{default_out})")
        print(f"Sample Rate: {SAMPLE_RATE} Hz (Mono)")

        print(f"\n[1/2] Recording {DURATION_SECONDS:.0f} seconds from microphone...")
        print(">>> SPEAK INTO YOUR MICROPHONE NOW <<<")

        audio_data = sd.rec(
            int(DURATION_SECONDS * SAMPLE_RATE),
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype="float32",
        )
        sd.wait()

        # Check RMS volume level
        rms = float(np.sqrt(np.mean(audio_data**2)))
        print(f"Recording complete. Signal RMS volume: {rms:.4f}")

        if rms < 0.005:
            print("\n[WARNING] Recorded signal is very quiet or silent.")
            print("- Check microphone privacy settings in Windows Settings -> Privacy -> Microphone.")
            print("- Verify your microphone is not hardware-muted.")

        print("\n[2/2] Playing back recorded audio through speakers...")
        sd.play(audio_data, samplerate=SAMPLE_RATE)
        sd.wait()

        print("\n[SUCCESS] Audio hardware verification completed successfully!")
        return True

    except Exception as exc:
        err_str = str(exc).lower()
        print(f"\n[ERROR] Audio verification failed: {exc}")
        if "device busy" in err_str or "busy" in err_str:
            print("\n[TROUBLESHOOTING - Audio device busy]")
            print("1. Close any other app using the microphone (Teams, Zoom, Discord, Browser).")
            print("2. In Windows Sound Settings, ensure 'Allow applications to take exclusive control' is disabled.")
            print("3. Unplug and replug USB headset/microphone if applicable.")
        elif "no input device" in err_str:
            print("\n[TROUBLESHOOTING - No Microphone Found]")
            print("1. Plug in a microphone or headset.")
            print("2. Check Windows Settings -> Sound -> Input.")
        return False


if __name__ == "__main__":
    success = run_audio_check()
    sys.exit(0 if success else 1)
