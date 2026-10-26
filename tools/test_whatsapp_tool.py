"""
Unit test suite for WhatsApp Automation Tool.
Author: Abhijit (System & Automation Engineer)
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# Ensure project root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tools.base import ToolResult
from tools.whatsapp_tool import WhatsAppTool
from tools.registry import TOOL_REGISTRY, execute_tool
from ui.server import parse_whatsapp_intent


class TestWhatsAppTool(unittest.TestCase):
    """Test suite for WhatsAppTool functionality, interface compliance, and zero-phantom guarantees."""

    def setUp(self) -> None:
        self.tool = WhatsAppTool()
        WhatsAppTool._last_searched_contact = None

    def test_tool_contract_and_schema(self) -> None:
        """Verify WhatsAppTool conforms to BaseTool specifications."""
        self.assertEqual(self.tool.name, "whatsapp_control")
        self.assertTrue(bool(self.tool.description))
        schema = self.tool.get_schema()
        self.assertEqual(schema["name"], "whatsapp_control")
        self.assertIn("action", schema["parameters"]["properties"])
        self.assertIn("contact", schema["parameters"]["properties"])
        self.assertIn("message", schema["parameters"]["properties"])

    def test_registry_integration(self) -> None:
        """Verify WhatsAppTool is registered in TOOL_REGISTRY."""
        self.assertIn("whatsapp_control", TOOL_REGISTRY)
        self.assertIn("whatsapp", TOOL_REGISTRY)
        self.assertIsInstance(TOOL_REGISTRY["whatsapp_control"], WhatsAppTool)

    @patch("pyautogui.press")
    @patch("pyautogui.write")
    @patch("time.sleep", return_value=None)
    def test_open_via_windows_search(
        self,
        mock_sleep: MagicMock,
        mock_write: MagicMock,
        mock_press: MagicMock,
    ) -> None:
        """Verify Windows Search mechanism presses Win, writes 'WhatsApp', and presses Enter."""
        with patch("tools.whatsapp_tool._ensure_input_desktop", return_value=None):
            opened = WhatsAppTool._open_via_windows_search()
            self.assertTrue(opened)
            mock_press.assert_any_call("win")
            mock_write.assert_called_with("WhatsApp", interval=0.03)
            mock_press.assert_any_call("enter")

    @patch.object(WhatsAppTool, "_focus_whatsapp_window", return_value=True)
    def test_open_whatsapp_success(self, mock_focus: MagicMock) -> None:
        """Verify open action succeeds when WhatsApp window is confirmed open."""
        res = self.tool.run(action="open")
        self.assertIsInstance(res, ToolResult)
        self.assertTrue(res.success)
        self.assertIn("WhatsApp opened and brought to focus", res.message)
        mock_focus.assert_called_once()

    @patch.object(WhatsAppTool, "_focus_whatsapp_window", return_value=False)
    def test_open_whatsapp_failure_zero_phantom(self, mock_focus: MagicMock) -> None:
        """Verify open action reports honest failure when WhatsApp cannot be opened."""
        res = self.tool.run(action="open")
        self.assertIsInstance(res, ToolResult)
        self.assertFalse(res.success)
        self.assertIn("could not be opened", res.message)
        self.assertEqual(res.data.get("error"), "window_not_found")

    @patch.object(WhatsAppTool, "_focus_whatsapp_window", return_value=True)
    @patch("pyautogui.press")
    @patch("pyautogui.hotkey")
    @patch("pyperclip.copy")
    @patch("time.sleep", return_value=None)
    def test_search_contact_success(
        self,
        mock_sleep: MagicMock,
        mock_copy: MagicMock,
        mock_hotkey: MagicMock,
        mock_press: MagicMock,
        mock_focus: MagicMock,
    ) -> None:
        """Verify searching contact activates search hotkey, enters name, and presses enter when WhatsApp is focused."""
        res = self.tool.run(action="search", contact="Aryan")
        self.assertIsInstance(res, ToolResult)
        self.assertTrue(res.success)
        self.assertEqual(res.data.get("contact"), "Aryan")
        self.assertEqual(WhatsAppTool._last_searched_contact, "Aryan")

        mock_focus.assert_called_once()
        mock_copy.assert_called_with("Aryan")
        mock_hotkey.assert_any_call("ctrl", "f")
        mock_hotkey.assert_any_call("ctrl", "v")
        mock_press.assert_called_with("enter")

    @patch.object(WhatsAppTool, "_focus_whatsapp_window", return_value=False)
    @patch("pyautogui.press")
    @patch("pyautogui.hotkey")
    def test_search_contact_failure_when_not_open(
        self,
        mock_hotkey: MagicMock,
        mock_press: MagicMock,
        mock_focus: MagicMock,
    ) -> None:
        """Verify searching contact fails safely with no phantom keystrokes if WhatsApp is not open."""
        res = self.tool.run(action="search", contact="Aryan")
        self.assertIsInstance(res, ToolResult)
        self.assertFalse(res.success)
        self.assertIn("WhatsApp is not open", res.message)
        # Ensure zero phantom key presses occurred
        mock_hotkey.assert_not_called()
        mock_press.assert_not_called()

    def test_search_contact_empty(self) -> None:
        """Verify searching with empty contact returns graceful error."""
        res = self.tool.run(action="search", contact="")
        self.assertFalse(res.success)
        self.assertIn("Missing required parameter", res.message)

    @patch.object(WhatsAppTool, "_focus_whatsapp_window", return_value=True)
    @patch("pyautogui.press")
    @patch("pyautogui.hotkey")
    @patch("pyperclip.copy")
    @patch("time.sleep", return_value=None)
    def test_send_message_after_search(
        self,
        mock_sleep: MagicMock,
        mock_copy: MagicMock,
        mock_hotkey: MagicMock,
        mock_press: MagicMock,
        mock_focus: MagicMock,
    ) -> None:
        """Verify message is typed and enter pressed in active conversation when WhatsApp is open."""
        WhatsAppTool._last_searched_contact = "Jay"
        res = self.tool.run(action="send", message="Meeting at 4 PM")
        self.assertIsInstance(res, ToolResult)
        self.assertTrue(res.success)
        self.assertEqual(res.data.get("contact"), "Jay")
        self.assertEqual(res.data.get("message"), "Meeting at 4 PM")

        mock_copy.assert_called_with("Meeting at 4 PM")
        mock_press.assert_called_with("enter")

    @patch.object(WhatsAppTool, "_focus_whatsapp_window", return_value=False)
    @patch("pyautogui.press")
    @patch("pyautogui.hotkey")
    @patch("pyperclip.copy")
    def test_send_message_failure_when_not_open(
        self,
        mock_copy: MagicMock,
        mock_hotkey: MagicMock,
        mock_press: MagicMock,
        mock_focus: MagicMock,
    ) -> None:
        """Verify sending message fails safely with zero phantom typing if WhatsApp is not open."""
        WhatsAppTool._last_searched_contact = "Jay"
        res = self.tool.run(action="send", message="Meeting at 4 PM")
        self.assertIsInstance(res, ToolResult)
        self.assertFalse(res.success)
        self.assertIn("WhatsApp is not open", res.message)
        mock_copy.assert_not_called()
        mock_press.assert_not_called()

    @patch.object(WhatsAppTool, "_focus_whatsapp_window", return_value=True)
    @patch("pyautogui.press")
    @patch("pyautogui.hotkey")
    @patch("pyperclip.copy")
    @patch("time.sleep", return_value=None)
    def test_send_message_with_contact_specified(
        self,
        mock_sleep: MagicMock,
        mock_copy: MagicMock,
        mock_hotkey: MagicMock,
        mock_press: MagicMock,
        mock_focus: MagicMock,
    ) -> None:
        """Verify specifying contact in send action searches contact first then sends."""
        res = self.tool.run(action="send", contact="Rohit", message="Hey Rohit")
        self.assertIsInstance(res, ToolResult)
        self.assertTrue(res.success)
        self.assertEqual(res.data.get("contact"), "Rohit")
        self.assertEqual(res.data.get("message"), "Hey Rohit")

    def test_send_message_empty(self) -> None:
        """Verify sending empty message returns graceful error."""
        res = self.tool.run(action="send", message="")
        self.assertFalse(res.success)
        self.assertIn("Missing required parameter", res.message)

    def test_unknown_action(self) -> None:
        """Verify invalid action returns structured error without raising exception."""
        res = self.tool.run(action="invalid_action")
        self.assertFalse(res.success)
        self.assertIn("Unknown WhatsApp action", res.message)

    def test_parse_whatsapp_intent_open(self) -> None:
        """Verify parse_whatsapp_intent recognizes all open command variations."""
        for phrase in ("open whatsapp", "launch whatsapp", "start whatsapp", "whatsapp khol", "whatsapp"):
            intent = parse_whatsapp_intent(phrase)
            self.assertIsNotNone(intent, f"Failed for {phrase}")
            self.assertEqual(intent.get("action"), "open")

    def test_parse_whatsapp_intent_search(self) -> None:
        """Verify parse_whatsapp_intent recognizes contact search queries."""
        intent = parse_whatsapp_intent("search Aryan in whatsapp")
        self.assertIsNotNone(intent)
        self.assertEqual(intent.get("action"), "search")
        self.assertEqual(intent.get("contact"), "aryan")

    def test_parse_whatsapp_intent_send(self) -> None:
        """Verify parse_whatsapp_intent recognizes send message commands."""
        intent = parse_whatsapp_intent("send message to Aryan: hello how are you")
        self.assertIsNotNone(intent)
        self.assertEqual(intent.get("action"), "send")
        self.assertEqual(intent.get("contact"), "Aryan")
        self.assertEqual(intent.get("message"), "hello how are you")


if __name__ == "__main__":
    unittest.main()
