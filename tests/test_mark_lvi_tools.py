"""
Unit Tests for Mark LVI Tools Integration.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from tools.registry import TOOL_REGISTRY
from tools.browser_tools import BrowserControlTool
from tools.screen_tools import CaptureScreenTool, DescribeScreenTool
from tools.desktop_tools import OrganizeDesktopTool, SetWallpaperTool, ComputerSettingsTool
from tools.dev_tools import DevAgentTool, is_package_name_valid
from tools.weather_tool import WeatherReportTool
from tools.antigravity_tools import AntigravityPromptTool


def test_tools_registered_in_registry():
    """Verify all Mark LVI tools are registered in TOOL_REGISTRY."""
    expected_tools = [
        "browser_control",
        "capture_screen",
        "describe_screen",
        "organize_desktop",
        "set_wallpaper",
        "computer_settings",
        "dev_agent",
        "weather_report",
        "antigravity_prompt"
    ]
    for tool_name in expected_tools:
        assert tool_name in TOOL_REGISTRY, f"Tool '{tool_name}' missing from TOOL_REGISTRY"
        tool = TOOL_REGISTRY[tool_name]
        schema = tool.get_schema()
        assert "name" in schema
        assert "description" in schema
        assert "parameters" in schema


def test_browser_control_tool_actions():
    """Verify BrowserControlTool handles actions gracefully."""
    tool = BrowserControlTool()
    
    with patch("webbrowser.open") as mock_open:
        res = tool.run(action="open", url="https://google.com")
        assert res.success is True
        mock_open.assert_called_once()

    with patch("webbrowser.open_new_tab") as mock_new_tab:
        res = tool.run(action="new_tab", url="https://youtube.com")
        assert res.success is True
        mock_new_tab.assert_called_once()

    with patch.object(tool, "_send_hotkey", return_value=True) as mock_hotkey:
        res = tool.run(action="close_tab")
        assert res.success is True
        mock_hotkey.assert_called_with(["ctrl", "w"])

    with patch.object(tool, "_send_hotkey", return_value=True) as mock_hotkey:
        res = tool.run(action="close_browser")
        assert res.success is True
        mock_hotkey.assert_called_with(["alt", "f4"])

    res_invalid = tool.run(action="unsupported_action_123")
    assert res_invalid.success is False


def test_organize_desktop_dry_run():
    """Verify OrganizeDesktopTool executes in dry_run mode without filesystem mutations."""
    tool = OrganizeDesktopTool()
    res = tool.run(dry_run=True)
    assert res.success is True
    assert res.data.get("dry_run") is True
    assert "Desktop organized" in res.message


def test_set_wallpaper_missing_file_rejected():
    """Verify SetWallpaperTool rejects missing files."""
    tool = SetWallpaperTool()
    res = tool.run(image_path="nonexistent_test_image_9999.png")
    assert res.success is False
    assert "does not exist" in res.message


def test_computer_settings_tool():
    """Verify ComputerSettingsTool network and resolution queries."""
    tool = ComputerSettingsTool()
    res_net = tool.run(setting="network")
    assert res_net.success is True
    assert "active_adapters" in res_net.data

    res_res = tool.run(setting="resolution")
    assert res_res.success is True
    assert "width" in res_res.data


def test_dev_agent_package_validation():
    """Verify PEP 508 package validator rejects injection attacks."""
    assert is_package_name_valid("numpy") is True
    assert is_package_name_valid("requests>=2.31") is True
    assert is_package_name_valid("torch==2.1.0") is True

    # Rejection attacks
    assert is_package_name_valid("-r requirements.txt") is False
    assert is_package_name_valid("numpy; rm -rf /") is False
    assert is_package_name_valid("package && malicious") is False
    assert is_package_name_valid("pkg | cat /etc/passwd") is False


def test_antigravity_prompt_tool(tmp_path):
    """Verify AntigravityPromptTool formulates and saves markdown directives."""
    tool = AntigravityPromptTool()
    with patch("pathlib.Path.home", return_value=tmp_path):
        res = tool.run(task="Refactor voice pipeline for zero latency", context="Audio buffer lag observed")
        assert res.success is True
        assert "prompt_file" in res.data
        prompt_path = Path(res.data["prompt_file"])
        assert prompt_path.exists()
        content = prompt_path.read_text(encoding="utf-8")
        assert "Refactor voice pipeline" in content
