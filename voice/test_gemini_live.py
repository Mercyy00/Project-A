"""Unit tests for GeminiLiveEngine in voice/gemini_live.py."""

from __future__ import annotations

import os
import unittest
from unittest.mock import MagicMock, patch

from google.genai import types
from voice.gemini_live import (
    DEFAULT_LIVE_VOICE,
    GeminiLiveEngine,
    SEND_SAMPLE_RATE,
    RECEIVE_SAMPLE_RATE,
)


class TestGeminiLiveEngine(unittest.TestCase):
    """Test suite for GeminiLiveEngine."""

    @patch.dict(os.environ, {"GEMINI_API_KEY": "fake_test_key_live"})
    def test_engine_initialization(self) -> None:
        """Verify default voice is Mark-grade 'Charon' and audio sample rates are configured."""
        engine = GeminiLiveEngine(api_key="fake_test_key_live")
        self.assertEqual(engine.voice_name, "Charon")
        self.assertEqual(SEND_SAMPLE_RATE, 16000)
        self.assertEqual(RECEIVE_SAMPLE_RATE, 24000)

    @patch.dict(os.environ, {"GEMINI_API_KEY": "fake_test_key_live"})
    def test_build_config_structure(self) -> None:
        """Verify LiveConnectConfig payload includes AUDIO modality and Charon voice."""
        engine = GeminiLiveEngine(api_key="fake_test_key_live", enable_tools=False)
        cfg = engine._build_config()
        self.assertIsInstance(cfg, types.LiveConnectConfig)
        self.assertEqual(cfg.response_modalities, ["AUDIO"])
        self.assertEqual(
            cfg.speech_config.voice_config.prebuilt_voice_config.voice_name,
            "Charon",
        )

    @patch.dict(os.environ, {"GEMINI_API_KEY": "fake_test_key_live"})
    def test_purge_output_buffer(self) -> None:
        """Verify _purge_output_buffer clears audio queue immediately on barge-in."""
        engine = GeminiLiveEngine(api_key="fake_test_key_live")
        engine._audio_out_queue.put_nowait(b"audio_bytes_1")
        engine._audio_out_queue.put_nowait(b"audio_bytes_2")
        self.assertFalse(engine._audio_out_queue.empty())

        engine._purge_output_buffer()
        self.assertTrue(engine._audio_out_queue.empty())

    def test_missing_api_key_raises(self) -> None:
        """Verify initializing without an API key raises ValueError."""
        with patch.dict(os.environ, {"GEMINI_API_KEY": ""}):
            with self.assertRaises(ValueError):
                GeminiLiveEngine(api_key="")


if __name__ == "__main__":
    unittest.main()
