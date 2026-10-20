"""Unit and integration test for core/service.py async handle_text wrapper."""

from __future__ import annotations

import asyncio
import unittest
from unittest.mock import MagicMock, patch

from core.service import get_brain, handle_text, reset_brain


class TestCoreService(unittest.IsolatedAsyncioTestCase):
    """Test suite for core/service.py async text handler."""

    def setUp(self) -> None:
        """Reset brain before each test."""
        reset_brain()

    @patch("core.brain.genai.Client")
    @patch("core.brain.load_api_key", return_value="fake-api-key")
    async def test_handle_text_english_and_hindi(
        self, mock_key: MagicMock, mock_client_cls: MagicMock
    ) -> None:
        """Verify handle_text processes English and Hindi inputs returning dict with 'text' and 'tool_steps'."""
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_chat = MagicMock()
        mock_client.chats.create.return_value = mock_chat

        # Mock responses
        res_en = MagicMock()
        res_en.text = "All systems are operational, sir."
        res_hi = MagicMock()
        res_hi.text = "नमस्ते, मैं आपकी क्या सहायता कर सकता हूँ?"

        mock_chat.send_message.side_effect = [res_en, res_hi]

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
        self.assertIn("text", result_hi)
        self.assertIn("tool_steps", result_hi)
        self.assertEqual(result_hi["source"], "ws")
        self.assertEqual(result_hi["text"], "नमस्ते, मैं आपकी क्या सहायता कर सकता हूँ?")

    async def test_handle_text_empty_input(self) -> None:
        """Verify empty input returns prompt to speak."""
        res = await handle_text("", source="telegram")
        self.assertEqual(res["source"], "telegram")
        self.assertEqual(res["tool_steps"], [])
        self.assertIn("listening", res["text"].lower())


async def run_live_test() -> None:
    """Run live sample for demonstration."""
    print("Testing core/service.py with English and Hindi messages:")
    res_en = await handle_text("Hello Jarvis, what is your status?", source="cli")
    print("\nEnglish Result:", res_en)
    res_hi = await handle_text("नमस्ते जार्विस, आप कैसे हैं?", source="ws")
    print("\nHindi Result:", res_hi)


if __name__ == "__main__":
    unittest.main()
