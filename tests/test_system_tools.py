"""Unit tests for Jarvis Day 4 Tools: Window, Clipboard, Volume, Brightness, Lock, and Battery.

Author: Abhijit (System & Automation Engineer)
"""

import sys
import os
from unittest.mock import MagicMock, patch
import pytest

from tools.base import ToolResult
from tools.window_tools import ListWindowsTool, FocusWindowTool, MinimizeWindowTool
from tools.system_tools import (
    ClipboardReadTool,
    ClipboardWriteTool,
    SetVolumeTool,
    SetBrightnessTool,
    LockScreenTool,
    BatteryTool,
)
from tools.registry import TOOL_REGISTRY, execute_tool


class TestWindowTools:
    """Tests for Window management tools."""

    def test_list_windows_success(self):
        tool = ListWindowsTool()
        schema = tool.get_schema()
        assert schema["name"] == "list_windows"
        assert "properties" in schema["parameters"]

        result = tool.run()
        assert isinstance(result, ToolResult)
        assert result.success is True
        assert isinstance(result.data, list)

    def test_focus_window_argument_validation(self):
        tool = FocusWindowTool()
        # Empty title
        res1 = tool.run(title="")
        assert res1.success is False
        assert "non-empty string" in res1.message

        # Non-string title
        res2 = tool.run(title=None)  # type: ignore
        assert res2.success is False

    def test_focus_window_nonexistent(self):
        tool = FocusWindowTool()
        res = tool.run(title="__non_existent_window_12345_xyz__")
        assert res.success is False
        assert "No open window found" in res.message

    def test_minimize_window_argument_validation(self):
        tool = MinimizeWindowTool()
        res1 = tool.run(title="")
        assert res1.success is False

        res2 = tool.run(title="__non_existent_window_12345_xyz__")
        assert res2.success is False
        assert "No open window found" in res2.message


class TestClipboardTools:
    """Tests for Clipboard read and write tools."""

    def test_clipboard_write_and_read(self):
        write_tool = ClipboardWriteTool()
        read_tool = ClipboardReadTool()

        test_payload = "Jarvis test clipboard string 42"
        w_res = write_tool.run(text=test_payload)
        assert w_res.success is True

        r_res = read_tool.run()
        assert r_res.success is True
        assert test_payload in r_res.data["text"]

    def test_clipboard_write_invalid(self):
        tool = ClipboardWriteTool()
        res = tool.run(text=None)  # type: ignore
        assert res.success is False
        assert "must be a string" in res.message


class TestVolumeTool:
    """Tests for Master Volume control tool."""

    def test_volume_validation(self):
        tool = SetVolumeTool()
        # Out of bounds (< 0)
        res_low = tool.run(level=-5)
        assert res_low.success is False
        assert "out of bounds" in res_low.message

        # Out of bounds (> 100)
        res_high = tool.run(level=120)
        assert res_high.success is False
        assert "out of bounds" in res_high.message

        # Invalid type
        res_invalid = tool.run(level="invalid")  # type: ignore
        assert res_invalid.success is False
        assert "must be an integer" in res_invalid.message

    def test_volume_execution(self):
        tool = SetVolumeTool()
        # Test valid volume level (30% as required by Day 4 acceptance test)
        res = tool.run(level=30)
        assert isinstance(res, ToolResult)
        # On systems with audio endpoints, this succeeds
        if res.success:
            assert res.data["volume_level"] in (29, 30, 31)
            assert "30" in res.message or "set to" in res.message


class TestBrightnessTool:
    """Tests for Display Brightness control tool."""

    def test_brightness_validation(self):
        tool = SetBrightnessTool()
        res_low = tool.run(level=-1)
        assert res_low.success is False

        res_high = tool.run(level=101)
        assert res_high.success is False

        res_str = tool.run(level="invalid")  # type: ignore
        assert res_str.success is False

    def test_brightness_execution_never_raises(self):
        tool = SetBrightnessTool()
        # Even if screen doesn't support brightness control (e.g. desktop monitor without DDC/CI),
        # tool must return ToolResult and never crash!
        res = tool.run(level=50)
        assert isinstance(res, ToolResult)


class TestLockScreenTool:
    """Tests for Lock Screen tool."""

    def test_lock_screen_mocked(self):
        tool = LockScreenTool()
        with patch("ctypes.windll.user32.LockWorkStation", return_value=1) as mock_lock:
            res = tool.run()
            assert res.success is True
            assert res.data["locked"] is True
            mock_lock.assert_called_once()

    def test_lock_screen_failure(self):
        tool = LockScreenTool()
        with patch("ctypes.windll.user32.LockWorkStation", return_value=0):
            res = tool.run()
            assert res.success is False


class TestBatteryTool:
    """Tests for Battery telemetry tool."""

    def test_battery_tool_execution(self):
        tool = BatteryTool()
        res = tool.run()
        assert isinstance(res, ToolResult)
        assert res.success is True
        assert "percent" in res.data
        assert "power_plugged" in res.data


class TestRegistryIntegration:
    """Tests that all Day 4 tools are registered and executable via registry."""

    def test_all_tools_in_registry(self):
        expected_tools = [
            "list_windows",
            "focus_window",
            "minimize_window",
            "clipboard_read",
            "clipboard_write",
            "set_volume",
            "set_brightness",
            "lock_screen",
            "battery",
        ]
        for name in expected_tools:
            assert name in TOOL_REGISTRY, f"Tool '{name}' missing from TOOL_REGISTRY"

    def test_execute_tool_volume_via_registry(self):
        res = execute_tool("set_volume", {"level": 30})
        assert isinstance(res, ToolResult)
        # Should either succeed or return structured failure (no unhandled exception)

    def test_execute_tool_clipboard_via_registry(self):
        execute_tool("clipboard_write", {"text": "Integration test payload"})
        res = execute_tool("clipboard_read", {})
        assert res.success is True
        assert "Integration test payload" in res.data["text"]


if __name__ == "__main__":
    pytest.main(["-v", __file__])
