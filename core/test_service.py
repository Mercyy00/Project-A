"""Unit and integration test for core/service.py async handle_text wrapper."""

from __future__ import annotations

import asyncio
import unittest
from unittest.mock import MagicMock, patch

from core.brain import JarvisBrain
from core.service import get_brain, handle_text, handle_text_stream, reset_brain


class TestCoreService(unittest.IsolatedAsyncioTestCase):
    """Test suite for core/service.py async text handler."""

    def setUp(self) -> None:
        """Reset brain before each test."""
        reset_brain()

    def test_tool_discovery_count(self) -> None:
        """Verify that all 29 tools are discovered and registered in the brain."""
        brain = get_brain()
        self.assertGreaterEqual(len(brain.tools), 29)
        tool_names = [t.__name__ for t in brain.tools]
        self.assertIn("set_volume", tool_names)
        self.assertIn("set_brightness", tool_names)
        self.assertIn("lock_screen", tool_names)
        self.assertIn("battery", tool_names)
        self.assertIn("list_windows", tool_names)
        self.assertIn("focus_window", tool_names)
        self.assertIn("minimize_window", tool_names)

    @patch.object(JarvisBrain, "chat")
    async def test_handle_text_multilingual(
        self, mock_chat: MagicMock
    ) -> None:
        """Verify handle_text processes English, Hindi, and Marathi inputs."""
        mock_chat.side_effect = [
            "All systems are operational, sir.",
            "नमस्ते, मैं आपकी क्या सहायता कर सकता हूँ?",
            "नमस्कार, मी तयार आहे.",
        ]

        # 1. English directive
        result_en = await handle_text("Jarvis, report system status", source="cli")
        self.assertIsInstance(result_en, dict)
        self.assertIn("text", result_en)
        self.assertIn("tool_steps", result_en)
        self.assertEqual(result_en["source"], "cli")
        self.assertEqual(result_en["text"], "All systems are operational, sir.")

        # 2. Hindi directive
        result_hi = await handle_text("जार्विस, आज का मौसम कैसा है?", source="ws")
        self.assertIsInstance(result_hi, dict)
        self.assertEqual(result_hi["source"], "ws")
        self.assertEqual(result_hi["text"], "नमस्ते, मैं आपकी क्या सहायता कर सकता हूँ?")

        # 3. Marathi directive
        result_mr = await handle_text("जार्विस, काय चालू आहे?", source="voice")
        self.assertIsInstance(result_mr, dict)
        self.assertEqual(result_mr["source"], "voice")
        self.assertEqual(result_mr["text"], "नमस्कार, मी तयार आहे.")

    @patch.object(JarvisBrain, "chat")
    async def test_handle_text_with_tool_steps(
        self, mock_chat: MagicMock
    ) -> None:
        """Verify handle_text faithfully records tool steps executed during turn."""
        brain = get_brain()

        def fake_chat(text: str, mode: str = "normal") -> str:
            brain.last_tool_steps = ["open_app({'app_name': 'calc'})"]
            return "Calculator opened, sir."

        mock_chat.side_effect = fake_chat

        result = await handle_text("open calculator", source="cli")
        self.assertEqual(result["text"], "Calculator opened, sir.")
        self.assertEqual(result["tool_steps"], ["open_app({'app_name': 'calc'})"])

    async def test_handle_text_empty_input(self) -> None:
        """Verify empty input returns prompt to speak."""
        res = await handle_text("", source="telegram")
        self.assertEqual(res["source"], "telegram")
        self.assertEqual(res["tool_steps"], [])
        self.assertIn("listening", res["text"].lower())

    def test_chat_stream_shortcuts(self) -> None:
        """Verify chat_stream handles fast shortcuts without remote API latency."""
        brain = get_brain()
        # Time shortcut
        time_chunks = list(brain.chat_stream("what time is it"))
        self.assertEqual(len(time_chunks), 1)
        self.assertIn("current time", time_chunks[0].lower())

        # Combat mode shortcut
        combat_chunks = list(brain.chat_stream("engage combat mode"))
        self.assertEqual(len(combat_chunks), 1)
        self.assertIn("combat protocol engaged", combat_chunks[0].lower())

    @patch.object(JarvisBrain, "chat_stream")
    async def test_handle_text_stream_events(
        self, mock_chat_stream: MagicMock
    ) -> None:
        """Verify handle_text_stream yields chunk events followed by completion event."""
        def fake_stream(text: str, mode: str = "normal"):
            yield "All "
            yield "systems "
            yield "nominal, "
            yield "sir."

        mock_chat_stream.side_effect = fake_stream

        events = []
        async for event in handle_text_stream("report status", source="ws"):
            events.append(event)

        # 4 chunks + 1 done event = 5 events
        self.assertEqual(len(events), 5)
        self.assertEqual(events[0], {"type": "chunk", "text": "All "})
        self.assertEqual(events[1], {"type": "chunk", "text": "systems "})
        self.assertEqual(events[2], {"type": "chunk", "text": "nominal, "})
        self.assertEqual(events[3], {"type": "chunk", "text": "sir."})

        done_event = events[4]
        self.assertEqual(done_event["type"], "done")
        self.assertEqual(done_event["text"], "All systems nominal, sir.")
        self.assertEqual(done_event["tool_steps"], [])
        self.assertEqual(done_event["source"], "ws")

    @patch.object(JarvisBrain, "chat_stream")
    async def test_handle_text_stream_with_tool_steps(
        self, mock_chat_stream: MagicMock
    ) -> None:
        """Verify handle_text_stream captures tool steps upon completion."""
        brain = get_brain()

        def fake_stream(text: str, mode: str = "normal"):
            brain.last_tool_steps = ["set_volume({'level': 75})"]
            yield "Volume adjusted to 75%, sir."

        mock_chat_stream.side_effect = fake_stream

        events = []
        async for event in handle_text_stream("set volume to 75", source="cli"):
            events.append(event)

        self.assertEqual(len(events), 2)
        self.assertEqual(events[0]["type"], "chunk")
        self.assertEqual(events[0]["text"], "Volume adjusted to 75%, sir.")

        done_event = events[1]
        self.assertEqual(done_event["type"], "done")
        self.assertEqual(done_event["text"], "Volume adjusted to 75%, sir.")
        self.assertEqual(done_event["tool_steps"], ["set_volume({'level': 75})"])
        self.assertEqual(done_event["source"], "cli")

    async def test_handle_text_stream_empty_input(self) -> None:
        """Verify handle_text_stream returns prompt on empty input."""
        events = []
        async for event in handle_text_stream("", source="voice"):
            events.append(event)

        self.assertEqual(len(events), 2)
        self.assertEqual(events[0]["type"], "chunk")
        self.assertIn("listening", events[0]["text"].lower())
        self.assertEqual(events[1]["type"], "done")
        self.assertEqual(events[1]["source"], "voice")

    @patch("time.sleep", return_value=None)
    @patch("groq.Groq")
    def test_groq_backoff_retry(
        self, mock_groq_cls: MagicMock, mock_sleep: MagicMock
    ) -> None:
        """Verify exponential backoff retry on transient 429 errors in Groq engine."""
        brain = get_brain()
        brain.groq_api_key = "fake_key"
        brain.llm_provider = "groq"

        mock_client = MagicMock()
        mock_groq_cls.return_value = mock_client

        # Simulate 1st call fails with 429, 2nd call succeeds
        class FakeChunk:
            def __init__(self, content):
                delta = MagicMock()
                delta.content = content
                delta.tool_calls = None
                choice = MagicMock()
                choice.delta = delta
                self.choices = [choice]

        def fake_stream():
            yield FakeChunk("Directive ")
            yield FakeChunk("acknowledged, ")
            yield FakeChunk("sir.")

        # Simulate attempt 0 fails for model with 429, then attempt 1 succeeds
        mock_client.chat.completions.create.side_effect = [
            Exception("Error code: 429 - Rate limit reached"),
            fake_stream(),
        ]

        chunks = list(brain._chat_stream_with_groq("test directive"))
        full_res = "".join(chunks)

        self.assertEqual(full_res, "Directive acknowledged, sir.")
        self.assertEqual(mock_client.chat.completions.create.call_count, 2)
        self.assertEqual(mock_sleep.call_count, 1)


if __name__ == "__main__":
    unittest.main()
