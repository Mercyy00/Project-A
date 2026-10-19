"""Unit and integration tests for Aryan's screen vision module (Project Jarvis).

Tests:
1. Screen capture functionality (full screen and regions) using mss.
2. Privacy pause guardrails (VISION_PAUSED=1).
3. Gemini multimodal vision screen understanding (describe_screen).
4. BaseTool compliance and structured ToolResult output for ScreenshotTool and DescribeScreenTool.
5. Automatic tool registry discovery and execution via tools.registry.
"""
from __future__ import annotations

import os
from pathlib import Path
import sys
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools.base import ToolResult
from vision.screen import describe_screen, take_screenshot
from vision.tools import DescribeScreenTool, ScreenshotTool, TOOLS


# ---------------------------------------------------------------------------
# 1. Screen Capture Tests (Day 2 - 19 Oct)
# ---------------------------------------------------------------------------

def test_take_screenshot_creates_valid_jpeg() -> None:
    """Verify primary screen capture produces a readable JPEG file on disk."""
    path = take_screenshot()
    assert os.path.exists(path), f"Screenshot file not found at: {path}"
    assert path.endswith(".jpg")
    assert os.path.getsize(path) > 0

    with Image.open(path) as img:
        assert img.format == "JPEG"
        assert img.width <= 1280  # Max width requirement from spec


def test_take_screenshot_region() -> None:
    """Verify taking a screenshot of a specific bounding box region."""
    region = (0, 0, 320, 240)
    path = take_screenshot(region=region)
    assert os.path.exists(path)
    assert path.endswith(".jpg")
    assert os.path.getsize(path) > 0

    with Image.open(path) as img:
        assert img.format == "JPEG"


def test_take_screenshot_invalid_region() -> None:
    """Verify invalid region length raises ValueError."""
    with pytest.raises(ValueError):
        take_screenshot(region=(0, 0))  # type: ignore[arg-type]


def test_take_screenshot_privacy_paused(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify that screen capture raises PermissionError when VISION_PAUSED=1."""
    monkeypatch.setenv("VISION_PAUSED", "1")
    with pytest.raises(PermissionError) as exc_info:
        take_screenshot()
    assert "paused by user privacy mode" in str(exc_info.value)


# ---------------------------------------------------------------------------
# 2. Gemini Multimodal Screen Description Tests (Day 3 - 20 Oct)
# ---------------------------------------------------------------------------

def test_describe_screen_privacy_paused(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify describe_screen raises PermissionError when VISION_PAUSED=1."""
    monkeypatch.setenv("VISION_PAUSED", "1")
    with pytest.raises(PermissionError) as exc_info:
        describe_screen(question="What is on my screen?")
    assert "paused by user privacy mode" in str(exc_info.value)


def test_describe_screen_empty_question() -> None:
    """Verify empty question raises ValueError."""
    with pytest.raises(ValueError, match="Question must be a non-empty string"):
        describe_screen(question="   ")


def test_describe_screen_missing_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify missing GEMINI_API_KEY raises ValueError."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(ValueError, match="GEMINI_API_KEY is missing or invalid"):
        describe_screen(question="Analyze screen")


def test_describe_screen_placeholder_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify placeholder API key raises ValueError."""
    monkeypatch.setenv("GEMINI_API_KEY", "your_gemini_api_key_here")
    with pytest.raises(ValueError, match="GEMINI_API_KEY is missing or invalid"):
        describe_screen(question="Analyze screen")


def test_describe_screen_missing_file_raises_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify passing a non-existent screenshot_path raises FileNotFoundError."""
    monkeypatch.setenv("GEMINI_API_KEY", "test-api-key-12345")
    with pytest.raises(FileNotFoundError):
        describe_screen(
            question="What is on screen?",
            screenshot_path="temp_vision/non_existent_image_12345.jpg",
        )


@patch("google.genai.Client")
def test_describe_screen_mocked_success(
    mock_client_cls: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Verify describe_screen sends image and question to Gemini and returns answer."""
    monkeypatch.setenv("GEMINI_API_KEY", "mock-test-key")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-2.5-flash")

    # Create dummy test image
    test_img_path = tmp_path / "test_screenshot.jpg"
    test_img = Image.new("RGB", (100, 100), color="blue")
    test_img.save(test_img_path, format="JPEG")

    # Setup mock response
    mock_response = MagicMock()
    mock_response.text = "The user has VS Code open with a Python file."
    mock_client_instance = MagicMock()
    mock_client_instance.models.generate_content.return_value = mock_response
    mock_client_cls.return_value = mock_client_instance

    result = describe_screen(
        question="What application is open?",
        screenshot_path=str(test_img_path),
    )

    assert result == "The user has VS Code open with a Python file."
    mock_client_cls.assert_called_once_with(api_key="mock-test-key")
    mock_client_instance.models.generate_content.assert_called_once()
    call_kwargs = mock_client_instance.models.generate_content.call_args.kwargs
    assert call_kwargs["model"] == "gemini-2.5-flash"
    assert len(call_kwargs["contents"]) == 2
    assert call_kwargs["contents"][1] == "What application is open?"


# ---------------------------------------------------------------------------
# 3. BaseTool & ToolResult Compliance Tests (Day 3 - 20 Oct)
# ---------------------------------------------------------------------------

def test_screenshot_tool_run_success() -> None:
    """Verify ScreenshotTool.run() returns a successful ToolResult."""
    tool = ScreenshotTool()
    result: ToolResult = tool.run()

    assert isinstance(result, ToolResult)
    assert result.success is True
    assert "file_path" in result.data
    assert os.path.exists(result.data["file_path"])
    assert "Screenshot captured successfully" in result.message


def test_screenshot_tool_run_privacy_paused(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify ScreenshotTool.run() handles privacy pause gracefully without crashing."""
    monkeypatch.setenv("VISION_PAUSED", "1")
    tool = ScreenshotTool()
    result: ToolResult = tool.run()

    assert isinstance(result, ToolResult)
    assert result.success is False
    assert "paused by user privacy mode" in result.message


def test_screenshot_tool_invalid_region() -> None:
    """Verify ScreenshotTool.run() handles invalid region parameter cleanly."""
    tool = ScreenshotTool()
    result: ToolResult = tool.run(region=[10, 20])  # Only 2 items instead of 4

    assert isinstance(result, ToolResult)
    assert result.success is False
    assert "Invalid 'region' parameter" in result.message


@patch("vision.tools.describe_screen")
def test_describe_screen_tool_run_success(mock_describe: MagicMock) -> None:
    """Verify DescribeScreenTool.run() returns successful ToolResult with AI answer."""
    mock_describe.return_value = "Notepad is open showing 'Hello World'."
    tool = DescribeScreenTool()
    result: ToolResult = tool.run(question="What is on Notepad?")

    assert isinstance(result, ToolResult)
    assert result.success is True
    assert result.message == "Notepad is open showing 'Hello World'."
    assert result.data["question"] == "What is on Notepad?"


def test_describe_screen_tool_run_empty_question() -> None:
    """Verify DescribeScreenTool.run() with empty question returns failure ToolResult."""
    tool = DescribeScreenTool()
    result: ToolResult = tool.run(question="")

    assert isinstance(result, ToolResult)
    assert result.success is False
    assert "cannot be empty" in result.message


def test_describe_screen_tool_run_privacy_paused(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify DescribeScreenTool.run() handles privacy pause safely."""
    monkeypatch.setenv("VISION_PAUSED", "1")
    tool = DescribeScreenTool()
    result: ToolResult = tool.run(question="What is on screen?")

    assert isinstance(result, ToolResult)
    assert result.success is False
    assert "paused by user privacy mode" in result.message


def test_describe_screen_tool_run_missing_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify DescribeScreenTool.run() handles missing API key without raising uncaught exception."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    tool = DescribeScreenTool()
    result: ToolResult = tool.run(question="What is on screen?")

    assert isinstance(result, ToolResult)
    assert result.success is False
    assert "GEMINI_API_KEY is missing or invalid" in result.message


def test_tools_schema_definitions() -> None:
    """Verify ScreenshotTool and DescribeScreenTool schemas adhere to OpenAI/Gemini format."""
    s_tool = ScreenshotTool()
    s_schema = s_tool.get_schema()
    assert s_schema["name"] == "take_screenshot"
    assert "parameters" in s_schema
    assert "region" in s_schema["parameters"]["properties"]

    d_tool = DescribeScreenTool()
    d_schema = d_tool.get_schema()
    assert d_schema["name"] == "describe_screen"
    assert "parameters" in d_schema
    assert "question" in d_schema["parameters"]["properties"]
    assert "question" in d_schema["parameters"]["required"]


def test_tools_export_list() -> None:
    """Verify TOOLS list contains both ScreenshotTool and DescribeScreenTool."""
    assert len(TOOLS) == 2
    tool_names = [t.name for t in TOOLS]
    assert "take_screenshot" in tool_names
    assert "describe_screen" in tool_names


# ---------------------------------------------------------------------------
# 4. Registry Auto-Load Integration Test
# ---------------------------------------------------------------------------

def test_registry_auto_loads_vision_tools() -> None:
    """Verify that tools.registry automatically discovers and loads vision.tools.TOOLS."""
    from tools.registry import TOOL_REGISTRY, execute_tool

    assert "take_screenshot" in TOOL_REGISTRY
    assert "describe_screen" in TOOL_REGISTRY

    # Execute screenshot tool through registry
    res = execute_tool("take_screenshot")
    assert isinstance(res, ToolResult)
    assert res.success is True
    assert os.path.exists(res.data["file_path"])


if __name__ == "__main__":
    sys.exit(pytest.main(["-v", __file__]))

