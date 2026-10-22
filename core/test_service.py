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

    @patch.object(JarvisBrain, "chat")
    async def test_handle_text_english_and_hindi(
        self, mock_chat: MagicMock
    ) -> None:
        """Verify handle_text processes English and Hindi inputs returning dict with 'text' and 'tool_steps'."""
        mock_chat.side_effect = [
            "All systems are operational, sir.",
            "नमस्ते, मैं आपकी क्या सहायता कर सकता हूँ?",
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
