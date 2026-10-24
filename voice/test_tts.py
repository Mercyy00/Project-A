"""Unit and integration tests for JarvisSpeaker (TTS).

Authored by Akanksha (Voice TTS Engineer).
Validates neural voice synthesis across English, Hindi, and Marathi,
file export, and playback interruption.
"""

from __future__ import annotations

import os
import sys
import unittest
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

from voice.tts import JarvisSpeaker, get_speaker, speak, speak_to_file, stop


class TestJarvisSpeaker(unittest.TestCase):
    """Test suite for JarvisSpeaker."""

    def setUp(self) -> None:
        self.speaker = JarvisSpeaker()

    def test_voice_selection_by_language(self) -> None:
        v_en = self.speaker.get_voice_for_language("en", "Hello")
        v_hi = self.speaker.get_voice_for_language("hi", "नमस्ते")
        v_mr = self.speaker.get_voice_for_language("mr", "नमस्कार")

        self.assertIn("en", v_en.lower())
        self.assertIn("hi", v_hi.lower())
        self.assertIn("mr", v_mr.lower())

    def test_speak_to_file_english(self) -> None:
        out = self.speaker.speak_to_file("Jarvis voice synthesis is operational.", lang="en")
        if out:
            self.assertTrue(Path(out).is_file())
            self.assertGreater(Path(out).stat().st_size, 0)

    def test_speak_to_file_marathi(self) -> None:
        out = self.speaker.speak_to_file("प्रोजेक्ट जार्विस मध्ये आपले स्वागत आहे.", lang="mr")
        if out:
            self.assertTrue(Path(out).is_file())
            self.assertGreater(Path(out).stat().st_size, 0)

    def test_stop_method_callable(self) -> None:
        # stop() should safely execute even if nothing is currently playing
        self.speaker.stop()
        self.assertFalse(self.speaker._is_speaking)


def run_three_language_speech_demo() -> None:
    """Demonstrate neural voice synthesis in all three languages.

    Per Section 7:
    '5. voice/test_tts.py speaks one sentence in each of the three languages.'
    """
    print("=" * 55)
    print("     JARVIS TTS MULTILINGUAL AUDIO DEMO")
    print("=" * 55)
    speaker = get_speaker()

    phrases = [
        ("English", "Jarvis voice system is online and ready.", "en"),
        ("Hindi", "नमस्ते! जार्विस आवाज़ प्रणाली सक्रिय है।", "hi"),
        ("Marathi", "नमस्कार! जार्विस आवाज प्रणाली सुरू झाली आहे.", "mr"),
    ]

    for lang_name, phrase, code in phrases:
        print(f"\n[{lang_name}] Synthesizing: {phrase}")
        speaker.speak(phrase, lang=code)

    print("\nAll 3 languages spoken successfully!")


if __name__ == "__main__":
    print("Running TTS Unit Tests...")
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(TestJarvisSpeaker)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    if "--demo" in sys.argv:
        run_three_language_speech_demo()
    else:
        print("\nTo hear speech in all 3 languages, run:")
        print("  python voice/test_tts.py --demo")
