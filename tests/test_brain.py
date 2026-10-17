"""Unit tests for Jarvis Core Brain module."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from core.brain import DEFAULT_SYSTEM_PROMPT, JarvisBrain, load_api_key


class TestJarvisBrain(unittest.TestCase):
    """Test suite for JarvisBrain initialization, conversation memory, and interfaces."""

    def setUp(self) -> None:
        """Set up mock client and responses for testing."""
        self.mock_client_patch = patch("core.brain.genai.Client")
        self.mock_client_class = self.mock_client_patch.start()
        self.mock_client = MagicMock()
        self.mock_client_class.return_value = self.mock_client

        # Mock chat session
        self.mock_chat = MagicMock()
        self.mock_client.chats.create.return_value = self.mock_chat

        # Mock API key retrieval
        self.mock_key_patch = patch("core.brain.load_api_key", return_value="fake-api-key")
        self.mock_key_patch.start()

    def tearDown(self) -> None:
        """Tear down all patches."""
        self.mock_client_patch.stop()
        self.mock_key_patch.stop()

    def test_initialization(self) -> None:
        """Verify brain initializes with default model and system prompt."""
        brain = JarvisBrain()
        self.assertEqual(brain.model_name, "gemini-2.5-flash")
        self.assertEqual(brain.system_prompt, DEFAULT_SYSTEM_PROMPT)
        self.assertEqual(len(brain.history), 0)
        self.mock_client.chats.create.assert_called_once()

    def test_chat_multi_turn_history(self) -> None:
        """Verify chat updates conversation history buffer accurately."""
        mock_response_1 = MagicMock()
        mock_response_1.text = "Hello Jay. All systems operational."
        mock_response_2 = MagicMock()
        mock_response_2.text = "Your CPU is running optimally at 14%."

        self.mock_chat.send_message.side_effect = [mock_response_1, mock_response_2]

        brain = JarvisBrain()
        reply_1 = brain.chat("Jarvis, report status.")
        self.assertEqual(reply_1, "Hello Jay. All systems operational.")

        reply_2 = brain.chat("How is my CPU doing?")
        self.assertEqual(reply_2, "Your CPU is running optimally at 14%.")

        history = brain.get_history()
        self.assertEqual(len(history), 4)
        self.assertEqual(history[0], {"role": "user", "content": "Jarvis, report status."})
        self.assertEqual(history[1], {"role": "model", "content": "Hello Jay. All systems operational."})
        self.assertEqual(history[2], {"role": "user", "content": "How is my CPU doing?"})
        self.assertEqual(history[3], {"role": "model", "content": "Your CPU is running optimally at 14%."})

    def test_process_input_interface_contract(self) -> None:
        """Verify process_input is an exact functional alias for chat."""
        mock_response = MagicMock()
        mock_response.text = "Confirmed, Jay."
        self.mock_chat.send_message.return_value = mock_response

        brain = JarvisBrain()
        reply = brain.process_input("Confirm interface compliance.")
        self.assertEqual(reply, "Confirmed, Jay.")
        self.mock_chat.send_message.assert_called_with("Confirm interface compliance.")

    def test_reset_conversation(self) -> None:
        """Verify resetting clears history and starts new chat session."""
        mock_response = MagicMock()
        mock_response.text = "Understood."
        self.mock_chat.send_message.return_value = mock_response

        brain = JarvisBrain()
        brain.chat("Remember this.")
        self.assertEqual(len(brain.get_history()), 2)

        brain.reset()
        self.assertEqual(len(brain.get_history()), 0)
        self.assertEqual(self.mock_client.chats.create.call_count, 2)

    def test_missing_api_key_raises_value_error(self) -> None:
        """Verify clean error when GEMINI_API_KEY is missing."""
        with patch.dict("os.environ", {}, clear=True), patch("dotenv.load_dotenv"):
            with self.assertRaises(ValueError) as ctx:
                load_api_key()
            self.assertIn("GEMINI_API_KEY is missing", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
