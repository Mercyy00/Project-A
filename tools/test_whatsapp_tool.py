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


class TestWhatsAppTool(unittest.TestCase):
    """Test suite for WhatsAppTool functionality and interface compliance."""

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

    @patch("subprocess.Popen")
    @patch("time.sleep", return_value=None)
    def test_open_whatsapp(self, mock_sleep: MagicMock, mock_popen: MagicMock) -> None:
        """Verify open action launches WhatsApp via protocol."""
        res = self.tool.run(action="open")
        self.assertIsInstance(res, ToolResult)
        self.assertTrue(res.success)
        self.assertIn("WhatsApp opened", res.message)
        mock_popen.assert_called_once()

    @patch("pyautogui.press")
    @patch("pyautogui.hotkey")
    @patch("pyperclip.copy")
    @patch("subprocess.Popen")
    @patch("time.sleep", return_value=None)
    def test_search_contact(
        self,
        mock_sleep: MagicMock,
        mock_popen: MagicMock,
        mock_copy: MagicMock,
        mock_hotkey: MagicMock,
        mock_press: MagicMock,
    ) -> None:
        """Verify searching contact activates search hotkey, enters name, and presses enter."""
        res = self.tool.run(action="search", contact="Aryan")
        self.assertIsInstance(res, ToolResult)
        self.assertTrue(res.success)
        self.assertEqual(res.data.get("contact"), "Aryan")
        self.assertEqual(WhatsAppTool._last_searched_contact, "Aryan")

        mock_copy.assert_called_with("Aryan")
        mock_hotkey.assert_any_call("ctrl", "f")
        mock_hotkey.assert_any_call("ctrl", "v")
        mock_press.assert_called_with("enter")

    def test_search_contact_empty(self) -> None:
        """Verify searching with empty contact returns graceful error."""
        res = self.tool.run(action="search", contact="")
        self.assertFalse(res.success)
        self.assertIn("Missing required parameter", res.message)

    @patch("pyautogui.press")
    @patch("pyautogui.hotkey")
    @patch("pyperclip.copy")
    @patch("subprocess.Popen")
    @patch("time.sleep", return_value=None)
    def test_send_message_after_search(
        self,
        mock_sleep: MagicMock,
        mock_popen: MagicMock,
        mock_copy: MagicMock,
        mock_hotkey: MagicMock,
        mock_press: MagicMock,
    ) -> None:
        """Verify message is typed and enter pressed in active conversation."""
        WhatsAppTool._last_searched_contact = "Jay"
        res = self.tool.run(action="send", message="Meeting at 4 PM")
        self.assertIsInstance(res, ToolResult)
        self.assertTrue(res.success)
        self.assertEqual(res.data.get("contact"), "Jay")
        self.assertEqual(res.data.get("message"), "Meeting at 4 PM")

        mock_copy.assert_called_with("Meeting at 4 PM")
        mock_press.assert_called_with("enter")

    @patch("pyautogui.press")
    @patch("pyautogui.hotkey")
    @patch("pyperclip.copy")
    @patch("subprocess.Popen")
    @patch("time.sleep", return_value=None)
    def test_send_message_with_contact_specified(
        self,
        mock_sleep: MagicMock,
        mock_popen: MagicMock,
        mock_copy: MagicMock,
        mock_hotkey: MagicMock,
        mock_press: MagicMock,
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


if __name__ == "__main__":
    unittest.main()
