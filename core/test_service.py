"""Unit and integration test for core/service.py async handle_text wrapper."""

from __future__ import annotations

import asyncio
import unittest
from unittest.mock import MagicMock, patch

from core.brain import JarvisBrain
from core.service import get_brain, handle_text, reset_brain


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


if __name__ == "__main__":
    unittest.main()
