"""Unit tests for Jarvis Day 4 Tools: Window, Clipboard, Volume, Brightness, Lock, and Battery.

Author: Abhijit (System & Automation Engineer)
"""

import sys
import os
from unittest.mock import MagicMock, patch
import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from tools.base import ToolResult
from tools.window_tools import ListWindowsTool, FocusWindowTool, MinimizeWindowTool
from tools.system_tools import (
    OpenAppTool,
    OpenWebsiteTool,
    OpenSettingsPageTool,
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


class TestOpenAppToolAllowlist:
    """Tests for Day 7 OpenAppTool allowlist, case-insensitivity, and friendly errors."""

    def test_allowlist_contains_day7_required_apps(self):
        tool = OpenAppTool()
        required_allowlist = [
            "chrome",
            "edge",
            "notepad",
            "calc",
            "code",
            "explorer",
            "spotify",
            "whatsapp",
            "settings",
        ]
        for app in required_allowlist:
            assert app in tool.ALLOWLIST, f"Required app '{app}' missing from OpenAppTool.ALLOWLIST"
            assert app in tool.APP_MAPPING or app in tool.APP_PROTOCOLS, f"Required app '{app}' missing executable or protocol mapping"

    def test_case_insensitive_and_alias_lookup(self):
        tool = OpenAppTool()
        with patch("subprocess.Popen") as mock_popen, patch("os.path.exists", return_value=True):
            mock_proc = MagicMock()
            mock_proc.pid = 1234
            mock_popen.return_value = mock_proc

            # Uppercase CHROME
            res_upper = tool.run(app_name="CHROME")
            assert res_upper.success is True
            assert res_upper.data["app_name"] == "chrome"

            # Mixed case Edge
            res_edge = tool.run(app_name="Microsoft Edge")
            assert res_edge.success is True
            assert res_edge.data["app_name"] == "edge"

    def test_unknown_app_friendly_error(self):
        tool = OpenAppTool()
        res = tool.run(app_name="nonexistent_application_xyz")
        assert res.success is False
        assert res.data is None
        # Must be friendly and informative
        assert "Unknown application shortcut" in res.message
        assert "allowlist" in res.message or "Supported applications" in res.message
        for sample_app in ["chrome", "notepad", "calc"]:
            assert sample_app in res.message

    def test_invalid_app_name_arguments(self):
        tool = OpenAppTool()
        res_empty = tool.run(app_name="")
        assert res_empty.success is False
        assert "non-empty string" in res_empty.message

        res_none = tool.run(app_name=None)  # type: ignore
        assert res_none.success is False

    @patch("subprocess.Popen")
    @patch("os.path.exists", return_value=True)
    def test_chrome_opens_successfully(self, mock_exists, mock_popen):
        tool = OpenAppTool()
        mock_proc = MagicMock()
        mock_proc.pid = 9876
        mock_popen.return_value = mock_proc

        res = tool.run(app_name="chrome")
        assert res.success is True
        assert res.data["app_name"] == "chrome"
        assert res.data["pid"] == 9876
        mock_popen.assert_called_once()

    def test_dynamic_app_discovery_indexes_system(self):
        """Verify dynamic app indexer discovers and indexes installed applications on Windows."""
        tool = OpenAppTool()
        apps = tool._get_installed_apps()
        assert isinstance(apps, dict)
        if os.name == "nt":
            assert len(apps) > 5

    @patch("os.startfile")
    def test_dynamic_app_launch_start_menu_shortcut(self, mock_startfile):
        """Verify dynamic launch of any installed application via Start Menu shortcut (.lnk)."""
        tool = OpenAppTool()
        fake_app_info = {
            "type": "lnk",
            "path": r"C:\ProgramData\Microsoft\Windows\Start Menu\Programs\Figma.lnk",
            "name": "Figma"
        }
        with patch.object(OpenAppTool, "_find_installed_app", return_value=fake_app_info):
            res = tool.run(app_name="Figma")
            assert res.success is True
            assert "Figma" in res.message
            assert res.data["shortcut_path"] == fake_app_info["path"]
            mock_startfile.assert_called_once_with(fake_app_info["path"])

    @patch("subprocess.Popen")
    def test_dynamic_app_launch_uwp_store_package(self, mock_popen):
        """Verify dynamic launch of Windows Store / UWP application via shell:AppsFolder."""
        tool = OpenAppTool()
        fake_app_info = {
            "type": "appx",
            "appid": "OpenAI.Codex_2p2nqsd0c76g0!App",
            "name": "ChatGPT"
        }
        mock_proc = MagicMock()
        mock_proc.pid = 5566
        mock_popen.return_value = mock_proc

        with patch.object(OpenAppTool, "_find_installed_app", return_value=fake_app_info):
            res = tool.run(app_name="ChatGPT")
            assert res.success is True
            assert "ChatGPT" in res.message
            assert res.data["pid"] == 5566
            mock_popen.assert_called_once_with(["explorer.exe", "shell:AppsFolder\\OpenAI.Codex_2p2nqsd0c76g0!App"])


class TestOpenWebsiteTool:
    """Tests for Day 7 OpenWebsiteTool HTTP/HTTPS enforcement and URL opening."""

    @patch("webbrowser.open", return_value=True)
    def test_open_website_url_parameter_https(self, mock_browser):
        tool = OpenWebsiteTool()
        res = tool.run(url="https://www.google.com")
        assert res.success is True
        assert res.data["url"] == "https://www.google.com"
        mock_browser.assert_called_once_with("https://www.google.com")

    @patch("webbrowser.open", return_value=True)
    def test_open_website_url_parameter_http(self, mock_browser):
        tool = OpenWebsiteTool()
        res = tool.run(url="http://example.com")
        assert res.success is True
        assert res.data["url"] == "http://example.com"
        mock_browser.assert_called_once_with("http://example.com")

    @patch("webbrowser.open", return_value=True)
    def test_open_website_shortcuts(self, mock_browser):
        tool = OpenWebsiteTool()
        res = tool.run(url="youtube")
        assert res.success is True
        assert res.data["url"] == "https://www.youtube.com"
        mock_browser.assert_called_once_with("https://www.youtube.com")

    @patch("webbrowser.open")
    def test_reject_unsupported_url_schemes(self, mock_browser):
        tool = OpenWebsiteTool()
        for bad_scheme in ["ftp://files.example.com", "file:///C:/test.txt", "javascript:void(0)"]:
            res = tool.run(url=bad_scheme)
            assert res.success is False
            assert "Invalid URL scheme" in res.message
            mock_browser.assert_not_called()

    def test_invalid_or_empty_url(self):
        tool = OpenWebsiteTool()
        for invalid in ["", "   ", None]:
            res = tool.run(url=invalid)  # type: ignore
            assert res.success is False
            assert "must be a non-empty string" in res.message


class TestOpenSettingsPageTool:
    """Tests for Day 7 OpenSettingsPageTool ms-settings: protocol launching."""

    def test_schema_validity(self):
        tool = OpenSettingsPageTool()
        schema = tool.get_schema()
        assert schema["name"] == "open_settings_page"
        assert "page" in schema["parameters"]["properties"]
        assert schema["parameters"]["required"] == ["page"]

    @patch("os.startfile", return_value=None)
    def test_supported_settings_pages(self, mock_startfile):
        tool = OpenSettingsPageTool()
        expected_pages = ["display", "sound", "bluetooth", "wifi"]
        for page in expected_pages:
            mock_startfile.reset_mock()
            res = tool.run(page=page)
            assert res.success is True
            assert res.data["page"] in (page, "network-wifi")
            assert res.data["uri"].startswith("ms-settings:")
            mock_startfile.assert_called_once_with(res.data["uri"])

    @patch("os.startfile", return_value=None)
    def test_settings_page_case_insensitive(self, mock_startfile):
        tool = OpenSettingsPageTool()
        res = tool.run(page="DISPLAY")
        assert res.success is True
        assert res.data["uri"] == "ms-settings:display"
        mock_startfile.assert_called_once_with("ms-settings:display")

    @patch("os.startfile", return_value=None)
    def test_direct_ms_settings_uri(self, mock_startfile):
        tool = OpenSettingsPageTool()
        res = tool.run(page="ms-settings:bluetooth")
        assert res.success is True
        assert res.data["uri"] == "ms-settings:bluetooth"
        mock_startfile.assert_called_once_with("ms-settings:bluetooth")

    def test_unknown_settings_page(self):
        tool = OpenSettingsPageTool()
        res = tool.run(page="unknown_subpage_123")
        assert res.success is False
        assert "Unknown settings page" in res.message
        assert "display" in res.message

    def test_empty_or_invalid_page(self):
        tool = OpenSettingsPageTool()
        for invalid in ["", "  ", None]:
            res = tool.run(page=invalid)  # type: ignore
            assert res.success is False
            assert "page must be a non-empty string" in res.message


class TestRegistryIntegration:
    """Tests that all tools are registered and executable via registry."""

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
            "open_app",
            "open_website",
            "open_settings_page",
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

    def test_execute_tool_unknown_app_friendly_error_via_registry(self):
        res = execute_tool("open_app", {"app_name": "unknown_app_xyz_999"})
        assert res.success is False
        assert "Unknown application shortcut" in res.message
        assert "allowlist" in res.message or "Supported applications" in res.message

    @patch("webbrowser.open", return_value=True)
    def test_execute_tool_open_website_via_registry(self, mock_browser):
        res = execute_tool("open_website", {"url": "https://www.google.com"})
        assert res.success is True
        mock_browser.assert_called_once_with("https://www.google.com")

    @patch("os.startfile", return_value=None)
    def test_execute_tool_open_settings_page_via_registry(self, mock_startfile):
        res = execute_tool("open_settings_page", {"page": "display"})
        assert res.success is True
        mock_startfile.assert_called_once_with("ms-settings:display")


if __name__ == "__main__":
    pytest.main(["-v", __file__])
