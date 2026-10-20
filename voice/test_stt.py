"""Unit and integration tests for JARVIS Speech-to-Text and Language Detection.

Authored by Madhuri (Voice Engineer - STT).
Tests all 30 multilingual cases from tests/voice_cases.csv and validates
the Transcriber interface across English, Hindi, and Marathi.
"""

from __future__ import annotations

import csv
import io
import os
import sys
import tempfile
import unittest
import wave
from pathlib import Path

# Ensure project root is in sys.path for direct script execution
_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from unittest.mock import MagicMock, patch

import numpy as np

from voice.lang import (
    SUPPORTED_LANGUAGES,
    detect_language,
    get_language_code,
    get_supported_languages,
    is_roman_script,
)
from voice.stt import (
    AudioFileError,
    MicrophoneError,
    ModelLoadError,
    STTError,
    Transcriber,
    get_transcriber,
    listen,
    transcribe_file,
    transcribe_mic,
)


def find_voice_cases_csv() -> Path:
    """Find voice_cases.csv in standard workspace directories."""
    candidates = [
        Path(__file__).resolve().parent.parent / "tests" / "voice_cases.csv",
        Path("tests") / "voice_cases.csv",
        Path("voice_cases.csv"),
        Path(r"D:\Project A\tests\voice_cases.csv"),
        Path(r"D:\Madhuri\voice\tests\voice_cases.csv"),
    ]
    for p in candidates:
        if p.is_file():
            return p
    raise FileNotFoundError("tests/voice_cases.csv not found in candidate paths.")


class TestLanguageDetection(unittest.TestCase):
    """Test suite for language detection in voice/lang.py."""

    def test_empty_and_whitespace(self) -> None:
        self.assertEqual(detect_language(""), "en")
        self.assertEqual(detect_language("   "), "en")
        self.assertEqual(detect_language("12345 !@#$%"), "en")

    def test_roman_script_rule(self) -> None:
        """Per JARVIS specification, Roman-script text must always return 'en'."""
        self.assertEqual(detect_language("Jarvis what is the date today?"), "en")
        self.assertEqual(detect_language("Open Notepad and write a note"), "en")
        self.assertEqual(detect_language("kasa ahes mitra"), "en")
        self.assertEqual(detect_language("kya chal raha hai"), "en")

    def test_hindi_devanagari(self) -> None:
        self.assertEqual(detect_language("जार्विस आज की तारीख क्या है?"), "hi")
        self.assertEqual(detect_language("कृपया नोटपैड खोलो और लिखना शुरू करो।"), "hi")
        self.assertEqual(detect_language("आज का मौसम कैसा है मुझे बताओ।"), "hi")

    def test_marathi_devanagari(self) -> None:
        self.assertEqual(detect_language("जार्विस आजची तारीख काय आहे?"), "mr")
        self.assertEqual(detect_language("कृपया नोटपॅड उघडा आणि लिहायला सुरुवात करा."), "mr")
        self.assertEqual(detect_language("आजचे हवामान कसे आहे ते मला सांगा."), "mr")
        # Unique Marathi letter 'ळ'
        self.assertEqual(detect_language("सगळे काम व्यवस्थित झाले आहे."), "mr")

    def test_all_30_voice_cases_from_csv(self) -> None:
        """Verify all 30 test sentences from tests/voice_cases.csv."""
        csv_path = find_voice_cases_csv()
        self.assertTrue(csv_path.is_file(), f"Missing CSV: {csv_path}")

        count = 0
        with open(csv_path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                sentence_id = row["id"]
                text = row["text"]
                expected = row["expected_lang"]
                detected = detect_language(text)
                self.assertEqual(
                    detected,
                    expected,
                    f"Case #{sentence_id} failed: '{text}' -> expected {expected}, got {detected}",
                )
                count += 1

        self.assertEqual(count, 30, f"Expected exactly 30 test sentences, found {count}.")

    def test_language_helpers(self) -> None:
        self.assertEqual(get_language_code("en"), "en-US")
        self.assertEqual(get_language_code("hi"), "hi-IN")
        self.assertEqual(get_language_code("mr"), "mr-IN")
        self.assertEqual(get_language_code("marathi"), "mr-IN")
        self.assertIn("en", get_supported_languages())
        self.assertIn("hi", get_supported_languages())
        self.assertIn("mr", get_supported_languages())


class TestTranscriber(unittest.TestCase):
    """Test suite for Transcriber methods and error handling in voice/stt.py."""

    def setUp(self) -> None:
        self.transcriber = Transcriber(model_size="base", device="cpu", compute_type="int8")

    def test_configuration_defaults(self) -> None:
        self.assertEqual(self.transcriber.model_size, "base")
        self.assertEqual(self.transcriber.device, "cpu")

    def test_transcribe_file_missing_raises_error(self) -> None:
        with self.assertRaises(AudioFileError):
            self.transcriber.transcribe_file("non_existent_audio_sample_12345.wav")

    def test_transcribe_synthetic_wav_file(self) -> None:
        """Create a short 1-second synthetic 16kHz mono WAV and test transcribe_file."""
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_wav:
            wav_path = Path(temp_wav.name)

        try:
            # Generate 1 sec of 16kHz sine wave audio
            sample_rate = 16000
            t = np.linspace(0, 1.0, sample_rate, False)
            tone = (np.sin(2 * np.pi * 440 * t) * 32767).astype(np.int16)

            with wave.open(str(wav_path), "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(sample_rate)
                wf.writeframes(tone.tobytes())

            result = self.transcriber.transcribe_file(wav_path)
            self.assertIsInstance(result, dict)
            self.assertIn("text", result)
            self.assertIn("language", result)
            self.assertIn(result["language"], ["en", "hi", "mr"])
        finally:
            if wav_path.is_file():
                wav_path.unlink()

    def test_transcribe_mic_mocked(self) -> None:
        """Test transcribe_mic with mocked audio recording and transcription."""
        mock_audio = np.zeros(16000 * 4, dtype=np.float32)

        mock_seg = MagicMock()
        mock_seg.text = " Jarvis what is the date today? "

        with patch.object(self.transcriber, "record_audio", return_value=mock_audio):
            with patch.object(
                self.transcriber,
                "_ensure_model_loaded",
            ) as mock_load:
                mock_model = MagicMock()
                mock_model.transcribe.return_value = ([mock_seg], None)
                mock_load.return_value = mock_model

                text = self.transcriber.transcribe_mic(duration_seconds=4)
                self.assertEqual(text, "Jarvis what is the date today?")

    def test_listen_mocked_silence(self) -> None:
        """Test listen when no speech occurs (silence threshold not met)."""
        mock_stream = MagicMock()
        mock_stream.__enter__.return_value = mock_stream
        # Return chunks of near-zero values
        mock_stream.read.return_value = (np.zeros((1600, 1), dtype=np.float32), None)

        with patch("voice.stt.sd.InputStream", return_value=mock_stream):
            result = self.transcriber.listen(max_seconds=1, silence_seconds=0.2)
            self.assertEqual(result["text"], "")
            self.assertEqual(result["language"], "en")
            self.assertIn("speech_end_time", result)


def run_live_mic_test() -> None:
    """Live interactive speech recognition test for Day 2 / Day 3.

    Per Section 7:
    '5. voice/test_stt.py: record, then print Transcript and Language.'
    """
    print("\n" + "=" * 50)
    print("      LIVE MICROPHONE STT & LANGUAGE TEST")
    print("=" * 50)
    print("Instructions:")
    print("Speak clearly into your microphone when prompted.")
    print("Try speaking in English, Hindi, or Marathi.")
    print("Example: 'Jarvis what is the date today?'")
    print("=" * 50)

    try:
        t = get_transcriber()
        print("\nStarting 4-second recording in 2 seconds...")
        import time
        time.sleep(2)
        print(">>> SPEAK NOW! <<<")
        transcript = t.transcribe_mic(duration_seconds=4)
        lang = detect_language(transcript)

        print("\n" + "-" * 40)
        print(f"Transcript: {transcript if transcript else '[No speech detected]'}")
        print(f"Language:   {lang} ({SUPPORTED_LANGUAGES.get(lang, 'Unknown')})")
        print("-" * 40)

        if "jarvis" in transcript.lower():
            print("Acceptance test check: 'Jarvis' wake keyword detected!")

    except Exception as exc:
        print(f"\nLive test encountered an issue: {exc}")


if __name__ == "__main__":
    print("Running STT Unit Tests...")
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    test_result = runner.run(suite)

    if not test_result.wasSuccessful():
        sys.exit(1)

    # If --mic or --live passed, or user runs directly and wants to test mic
    if "--mic" in sys.argv or "--live" in sys.argv:
        run_live_mic_test()
    else:
        print("\nAll unit tests passed successfully!")
        print("To run the live microphone test, execute:")
        print("  python voice/test_stt.py --mic")
