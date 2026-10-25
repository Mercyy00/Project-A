"""Focused tests for deterministic browser routing."""

from __future__ import annotations

from unittest.mock import patch

from tools.browser_tools import BrowserControlTool


def test_search_uses_requested_browser() -> None:
    """A browser-specific search launches that browser with the encoded search URL."""
    tool = BrowserControlTool()
    with patch.object(tool, "_launch_specific_browser", return_value=True) as launch:
        result = tool.run(action="search", query="Modern Warfare four", browser="chrome")

    assert result.success is True
    assert result.data["browser"] == "chrome"
    launch.assert_called_once_with(
        "chrome",
        "https://www.google.com/search?q=Modern+Warfare+four",
    )


def test_search_reports_missing_requested_browser() -> None:
    """Browser-specific searches report a failure instead of silently switching browsers."""
    tool = BrowserControlTool()
    with patch.object(tool, "_launch_specific_browser", return_value=False):
        result = tool.run(action="search", query="LinkedIn", browser="chrome")

    assert result.success is False
    assert "could not find or launch chrome" in result.message.lower()
