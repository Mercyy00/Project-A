"""
Unit and integration tests for BrowserControlTool and browser intent parsing.
Author: Abhijit (System & Automation Engineer)
"""

import unittest
from unittest.mock import MagicMock, patch

from tools.browser_tools import BrowserControlTool
from tools.base import ToolResult
from ui.server import parse_browser_intent


class TestBrowserControlTool(unittest.TestCase):
    def setUp(self) -> None:
        self.tool = BrowserControlTool()

    def test_schema_validity(self) -> None:
        """Verify browser tool JSON schema contains all required actions."""
        schema = self.tool.get_schema()
        self.assertEqual(schema["name"], "browser_control")
        actions = schema["parameters"]["properties"]["action"]["enum"]
        expected_actions = [
            "open", "new_tab", "close_tab", "next_tab", "prev_tab", "switch_tab",
            "reopen_tab", "scroll_down", "scroll_up", "scroll_top", "scroll_bottom",
            "reload", "hard_reload", "back", "forward", "zoom_in", "zoom_out",
            "zoom_reset", "fullscreen", "bookmark", "history", "downloads",
            "click_link", "close_browser"
        ]
        for act in expected_actions:
            self.assertIn(act, actions, f"Action {act} missing from schema")

    @patch.object(BrowserControlTool, "_focus_browser_window", return_value=True)
    @patch.object(BrowserControlTool, "_send_hotkey", return_value=True)
    def test_tab_ahead_and_behind(self, mock_hotkey: MagicMock, mock_focus: MagicMock) -> None:
        """Verify next_tab and prev_tab dispatch appropriate hotkeys."""
        res_next = self.tool.run(action="next_tab")
        self.assertTrue(res_next.success)
        mock_hotkey.assert_called_with(["ctrl", "tab"])

        res_prev = self.tool.run(action="prev_tab")
        self.assertTrue(res_prev.success)
        mock_hotkey.assert_called_with(["ctrl", "shift", "tab"])

    @patch.object(BrowserControlTool, "_focus_browser_window", return_value=True)
    @patch.object(BrowserControlTool, "_send_hotkey", return_value=True)
    def test_switch_tab(self, mock_hotkey: MagicMock, mock_focus: MagicMock) -> None:
        """Verify switch_tab dispatches Ctrl+<number>."""
        res = self.tool.run(action="switch_tab", tab_index=3)
        self.assertTrue(res.success)
        mock_hotkey.assert_called_with(["ctrl", "3"])

    @patch.object(BrowserControlTool, "_focus_browser_window", return_value=True)
    @patch.object(BrowserControlTool, "_send_hotkey", return_value=True)
    def test_reopen_tab(self, mock_hotkey: MagicMock, mock_focus: MagicMock) -> None:
        """Verify reopen_tab dispatches Ctrl+Shift+T."""
        res = self.tool.run(action="reopen_tab")
        self.assertTrue(res.success)
        mock_hotkey.assert_called_with(["ctrl", "shift", "t"])

    @patch.object(BrowserControlTool, "_focus_browser_window", return_value=True)
    @patch.object(BrowserControlTool, "_send_hotkey", return_value=True)
    def test_reload_and_hard_reload(self, mock_hotkey: MagicMock, mock_focus: MagicMock) -> None:
        """Verify reload and hard reload dispatch correctly."""
        res1 = self.tool.run(action="reload")
        self.assertTrue(res1.success)
        mock_hotkey.assert_called_with(["f5"])

        res2 = self.tool.run(action="hard_reload")
        self.assertTrue(res2.success)
        mock_hotkey.assert_called_with(["ctrl", "f5"])

    @patch.object(BrowserControlTool, "_focus_browser_window", return_value=True)
    @patch.object(BrowserControlTool, "_send_hotkey", return_value=True)
    def test_zoom_controls(self, mock_hotkey: MagicMock, mock_focus: MagicMock) -> None:
        """Verify zoom in, out, and reset."""
        res_in = self.tool.run(action="zoom_in")
        self.assertTrue(res_in.success)
        mock_hotkey.assert_called_with(["ctrl", "+"])

        res_out = self.tool.run(action="zoom_out")
        self.assertTrue(res_out.success)
        mock_hotkey.assert_called_with(["ctrl", "-"])

        res_res = self.tool.run(action="zoom_reset")
        self.assertTrue(res_res.success)
        mock_hotkey.assert_called_with(["ctrl", "0"])

    @patch.object(BrowserControlTool, "_focus_browser_window", return_value=True)
    def test_scroll_actions(self, mock_focus: MagicMock) -> None:
        """Verify scroll actions invoke scrolling without errors."""
        with patch("tools.browser_tools.pyautogui") as mock_pag:
            res_down = self.tool.run(action="scroll_down", scroll_amount=5)
            self.assertTrue(res_down.success)
            mock_pag.scroll.assert_called_with(-600)

            res_up = self.tool.run(action="scroll_up", scroll_amount=3)
            self.assertTrue(res_up.success)
            mock_pag.scroll.assert_called_with(360)


class TestBrowserIntentParsing(unittest.TestCase):
    def test_tab_ahead_and_behind_intents(self) -> None:
        """Verify tab ahead and tab behind natural language parsing."""
        i1 = parse_browser_intent("open tab ahead of curent active tab")
        self.assertIsNotNone(i1)
        self.assertEqual(i1["action"], "next_tab")

        i2 = parse_browser_intent("tab ahead")
        self.assertIsNotNone(i2)
        self.assertEqual(i2["action"], "next_tab")

        i3 = parse_browser_intent("tab behind active tab")
        self.assertIsNotNone(i3)
        self.assertEqual(i3["action"], "prev_tab")

        i4 = parse_browser_intent("switch to previous tab")
        self.assertIsNotNone(i4)
        self.assertEqual(i4["action"], "prev_tab")

    def test_switch_tab_number_intent(self) -> None:
        """Verify switch tab to numbered tab."""
        i = parse_browser_intent("switch to tab 3")
        self.assertIsNotNone(i)
        self.assertEqual(i["action"], "switch_tab")
        self.assertEqual(i["tab_index"], 3)

    def test_reload_intent(self) -> None:
        """Verify reload tab intent."""
        i = parse_browser_intent("reload tab")
        self.assertIsNotNone(i)
        self.assertEqual(i["action"], "reload")

    def test_reopen_tab_intent(self) -> None:
        """Verify reopen closed tab intent."""
        i = parse_browser_intent("reopen closed tab")
        self.assertIsNotNone(i)
        self.assertEqual(i["action"], "reopen_tab")

    def test_scroll_browser_intent(self) -> None:
        """Verify browser scrolling intents."""
        i_down = parse_browser_intent("scroll browser down")
        self.assertIsNotNone(i_down)
        self.assertEqual(i_down["action"], "scroll_down")

        i_up = parse_browser_intent("scroll page up")
        self.assertIsNotNone(i_up)
        self.assertEqual(i_up["action"], "scroll_up")

    def test_zoom_intent(self) -> None:
        """Verify zoom in and out intents."""
        i_in = parse_browser_intent("zoom in browser")
        self.assertIsNotNone(i_in)
        self.assertEqual(i_in["action"], "zoom_in")

        i_out = parse_browser_intent("zoom out")
        self.assertIsNotNone(i_out)
        self.assertEqual(i_out["action"], "zoom_out")

    def test_meta_capabilities(self) -> None:
        """Verify capability questions return structured summary."""
        i = parse_browser_intent("can you control my complete browser")
        self.assertIsNotNone(i)
        self.assertEqual(i["action"], "capabilities")
        self.assertIn("complete browser automation", i["message"])


if __name__ == "__main__":
    unittest.main()
