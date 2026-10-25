"""Unit tests for GeminiLiveEngine in voice/gemini_live.py."""

from __future__ import annotations

import asyncio
import os
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

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
    def test_build_config_biases_transcription_for_indian_english_and_jarvis(self) -> None:
        """Verify Live transcription favors the user's locale and assistant name."""
        engine = GeminiLiveEngine(api_key="fake_test_key_live", enable_tools=False)

        cfg = engine._build_config()

        self.assertEqual(cfg.input_audio_transcription.language_codes, ["en-IN"])
        self.assertIn("JARVIS", cfg.input_audio_transcription.custom_vocabulary)

    @patch.dict(os.environ, {"GEMINI_API_KEY": "fake_test_key_live"})
    def test_live_turn_detection_waits_through_natural_pauses(self) -> None:
        """Live VAD should wait for a complete spoken turn before replying."""
        engine = GeminiLiveEngine(api_key="fake_test_key_live", enable_tools=False)

        cfg = engine._build_config()

        activity = cfg.realtime_input_config.automatic_activity_detection
        self.assertFalse(activity.disabled)
        self.assertEqual(activity.silence_duration_ms, 750)
        self.assertEqual(activity.end_of_speech_sensitivity, types.EndSensitivity.END_SENSITIVITY_LOW)

    @patch.dict(os.environ, {"GEMINI_API_KEY": "fake_test_key_live"})
    def test_purge_output_buffer(self) -> None:
        """Verify _purge_output_buffer clears audio queue immediately on barge-in."""
        engine = GeminiLiveEngine(api_key="fake_test_key_live")
        engine._audio_out_queue.put_nowait(b"audio_bytes_1")
        engine._audio_out_queue.put_nowait(b"audio_bytes_2")
        self.assertFalse(engine._audio_out_queue.empty())

        engine._purge_output_buffer()
        self.assertTrue(engine._audio_out_queue.empty())

    @patch.dict(os.environ, {"GEMINI_API_KEY": "fake_test_key_live"})
    def test_mute_state_and_drain(self) -> None:
        """Verify set_muted drains buffered mic audio and notifies listeners."""
        events: list[dict[str, str]] = []
        engine = GeminiLiveEngine(api_key="fake_test_key_live", event_callback=events.append)
        self.assertFalse(engine.is_muted)

        # Buffer some simulated mic bytes
        engine._mic_queue.put_nowait(b"pcm_bytes_waiting")
        self.assertFalse(engine._mic_queue.empty())

        # Mute
        engine.set_muted(True)
        self.assertTrue(engine.is_muted)
        self.assertTrue(engine._mic_queue.empty())  # Queue should be completely drained
        self.assertEqual(events[-1]["status"], "muted")

        # Unmute
        engine.set_muted(False)
        self.assertFalse(engine.is_muted)
        self.assertEqual(events[-1]["status"], "connected")

    def test_missing_api_key_raises(self) -> None:
        """Verify initializing without an API key raises ValueError."""
        with patch.dict(os.environ, {"GEMINI_API_KEY": ""}):
            with self.assertRaises(ValueError):
                GeminiLiveEngine(api_key="")

    def test_live_connect_setup_has_a_deadline(self) -> None:
        """A stalled WebSocket handshake must not leave the HUD connecting forever."""
        class HangingConnection:
            closed = False

            async def __aenter__(self):
                await asyncio.Event().wait()

            async def __aexit__(self, *_args):
                self.closed = True
                return False

        async def attempt() -> None:
            async with engine._open_live_session("test-model", types.LiveConnectConfig()):
                self.fail("A never-ending connection must time out before yielding.")

        engine = GeminiLiveEngine(api_key="fake_test_key_live", enable_tools=False)
        connection = HangingConnection()
        engine.client.aio.live.connect = MagicMock(return_value=connection)

        with patch("voice.gemini_live.LIVE_CONNECT_TIMEOUT_SECONDS", 0.01):
            with self.assertRaises(TimeoutError):
                asyncio.run(attempt())

        self.assertTrue(connection.closed)

    def test_all_live_models_failing_emits_hud_error(self) -> None:
        """The HUD gets a visible error after connection attempts time out."""
        class HangingConnection:
            async def __aenter__(self):
                await asyncio.Event().wait()

            async def __aexit__(self, *_args):
                return False

        events: list[dict[str, str]] = []
        engine = GeminiLiveEngine(
            api_key="fake_test_key_live",
            enable_tools=False,
            event_callback=events.append,
        )
        engine.client.aio.live.connect = MagicMock(return_value=HangingConnection())
        engine._audio_input_worker = AsyncMock()
        engine._audio_output_worker = AsyncMock()

        with patch("voice.gemini_live.DEFAULT_LIVE_MODELS", ("test-model",)), \
             patch("voice.gemini_live.LIVE_CONNECT_TIMEOUT_SECONDS", 0.01):
            asyncio.run(engine.run())

        error_events = [event for event in events if event.get("status") == "error"]
        self.assertEqual(len(error_events), 1)
        self.assertIn("Timed out connecting", error_events[0]["message"])


if __name__ == "__main__":
    unittest.main()
