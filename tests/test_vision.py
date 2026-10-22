"""Unit and integration tests for Aryan's screen vision module (Project Jarvis).

Covers all tasks up to 22 October 2026:
- Day 1 (18 Oct): Baseline hello_screenshot utility
- Day 2 (19 Oct): take_screenshot, DPI awareness, 10-file cleanup, region hints, VISION_PAUSED privacy
- Day 3 (20 Oct): describe_screen, ScreenshotTool, DescribeScreenTool, BaseTool schema & registry auto-load
- Day 4 (21 Oct): explain_screen_error, ExplainScreenErrorTool, region hints in describe_screen
- Day 5 (22 Oct): locate_element with coordinate scaling, ClickElementTool via registry dispatch
"""
from __future__ import annotations

import json
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
from vision.hello_screenshot import capture_hello_screenshot
from vision.screen import (
    clean_temp_vision,
    describe_screen,
    explain_screen_error,
    locate_element,
    parse_region_hint,
    take_screenshot,
    TEMP_VISION_DIR,
)
from vision.tools import (
    ClickElementTool,
    DescribeScreenTool,
    ExplainScreenErrorTool,
    ScreenshotTool,
    TOOLS,
)


# ---------------------------------------------------------------------------
# 1. Day 1 Tests (Sun 18 Oct): Hello Screenshot Setup
# ---------------------------------------------------------------------------

def test_capture_hello_screenshot_creates_file() -> None:
    """Verify hello_screenshot utility captures primary monitor and saves hello.png."""
    path, size = capture_hello_screenshot()
    assert os.path.exists(path)
    assert path.endswith("hello.png")
    assert size[0] > 0 and size[1] > 0
    with Image.open(path) as img:
        assert img.format == "PNG"


# ---------------------------------------------------------------------------
# 2. Day 2 Tests (Mon 19 Oct): Screen Capture & Privacy Guardrails
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
    """Verify screen capture raises PermissionError when VISION_PAUSED=1."""
    monkeypatch.setenv("VISION_PAUSED", "1")
    with pytest.raises(PermissionError) as exc_info:
        take_screenshot()
    assert "paused by user privacy mode" in str(exc_info.value)


def test_parse_region_hint() -> None:
    """Verify region hint parser correctly computes bounding boxes."""
    mock_mon = {"left": 0, "top": 0, "width": 1920, "height": 1080}
    top_box = parse_region_hint("top half", mock_mon)
    assert top_box == (0, 0, 1920, 540)

    bot_box = parse_region_hint("bottom half", mock_mon)
    assert bot_box == (0, 540, 1920, 540)

    left_box = parse_region_hint("left half", mock_mon)
    assert left_box == (0, 0, 960, 1080)

    right_box = parse_region_hint("right half", mock_mon)
    assert right_box == (960, 0, 960, 1080)

    with pytest.raises(ValueError):
        parse_region_hint("center quarter", mock_mon)


def test_take_screenshot_with_region_hint() -> None:
    """Verify taking a screenshot with region_hint parameter."""
    path = take_screenshot(region_hint="top half")
    assert os.path.exists(path)
    assert path.endswith(".jpg")


def test_clean_temp_vision_keeps_max_ten_files(tmp_path: Path) -> None:
    """Verify clean_temp_vision purges older files when more than 10 screenshots exist."""
    # Create 15 dummy images in TEMP_VISION_DIR with distinct modification times
    created = []
    for i in range(15):
        p = TEMP_VISION_DIR / f"test_cleanup_{i:02d}.jpg"
        p.write_bytes(b"dummy image content")
        created.append(p)

    clean_temp_vision(keep_newest=10)

    remaining = [
        f for f in TEMP_VISION_DIR.iterdir()
        if f.is_file() and f.name.startswith("test_cleanup_")
    ]
    # Clean up test files
    for f in remaining:
        f.unlink(missing_ok=True)

    assert len(remaining) <= 10


# ---------------------------------------------------------------------------
# 3. Day 3 Tests (Tue 20 Oct): Gemini Screen Description & Baseline Tools
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

    test_img_path = tmp_path / "test_screenshot.jpg"
    test_img = Image.new("RGB", (100, 100), color="blue")
    test_img.save(test_img_path, format="JPEG")

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
    result: ToolResult = tool.run(region=[10, 20])

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


# ---------------------------------------------------------------------------
# 4. Day 4 Tests (Wed 21 Oct): Error Explanation & Region Hints
# ---------------------------------------------------------------------------

def test_explain_screen_error_privacy_paused(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify explain_screen_error respects VISION_PAUSED=1."""
    monkeypatch.setenv("VISION_PAUSED", "1")
    with pytest.raises(PermissionError):
        explain_screen_error()


@patch("vision.screen.describe_screen")
def test_explain_screen_error_calls_describe_with_exact_prompt(mock_describe: MagicMock) -> None:
    """Verify explain_screen_error invokes describe_screen with the standardized prompt from spec."""
    mock_describe.return_value = "Error: ZeroDivisionError: division by zero. Fix: Check denominator."
    res = explain_screen_error(screenshot_path="dummy.jpg")
    assert "ZeroDivisionError" in res

    mock_describe.assert_called_once()
    prompt_used = mock_describe.call_args.kwargs["question"]
    assert "If there is an error message on the screen, quote it exactly" in prompt_used
    assert "suggest one fix" in prompt_used


@patch("vision.tools.explain_screen_error")
def test_explain_screen_error_tool_run_success(mock_explain: MagicMock) -> None:
    """Verify ExplainScreenErrorTool returns successful ToolResult with diagnosis."""
    mock_explain.return_value = "FileNotFoundError: 'data.csv'. Fix: Create data.csv file."
    tool = ExplainScreenErrorTool()
    res: ToolResult = tool.run()

    assert isinstance(res, ToolResult)
    assert res.success is True
    assert "FileNotFoundError" in res.message
    assert res.data["error_explanation"] == mock_explain.return_value


def test_explain_screen_error_tool_privacy_paused(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify ExplainScreenErrorTool gracefully reports privacy pause."""
    monkeypatch.setenv("VISION_PAUSED", "1")
    tool = ExplainScreenErrorTool()
    res: ToolResult = tool.run()

    assert isinstance(res, ToolResult)
    assert res.success is False
    assert "paused by user privacy mode" in res.message


# ---------------------------------------------------------------------------
# 5. Day 5 Tests (Thu 22 Oct): Locate Element & Click Through Registry
# ---------------------------------------------------------------------------

def test_locate_element_empty_description() -> None:
    """Verify locate_element raises ValueError if description is empty."""
    with pytest.raises(ValueError, match="Description must be a non-empty string"):
        locate_element(description="")


def test_locate_element_privacy_paused(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify locate_element raises PermissionError when VISION_PAUSED=1."""
    monkeypatch.setenv("VISION_PAUSED", "1")
    with pytest.raises(PermissionError):
        locate_element(description="Submit button")


@patch("google.genai.Client")
def test_locate_element_scaling_success(
    mock_client_cls: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Verify locate_element scales model coordinates back to screen pixels."""
    monkeypatch.setenv("GEMINI_API_KEY", "mock-test-key")

    # Create dummy image: 640x360 px
    test_img_path = tmp_path / "scaled_screenshot.jpg"
    img = Image.new("RGB", (640, 360), color="white")
    img.save(test_img_path, format="JPEG")

    # Mock Gemini response with JSON
    mock_response = MagicMock()
    mock_response.text = '{"found": true, "x": 320, "y": 180}'
    mock_client_inst = MagicMock()
    mock_client_inst.models.generate_content.return_value = mock_response
    mock_client_cls.return_value = mock_client_inst

    # Mock mss screen resolution: 1920x1080
    mock_sct = MagicMock()
    mock_sct.monitors = [{}, {"left": 0, "top": 0, "width": 1920, "height": 1080}]
    mock_sct.__enter__.return_value = mock_sct
    mock_sct.__exit__.return_value = False
    with patch("mss.MSS", return_value=mock_sct):
        coords = locate_element("OK button", screenshot_path=str(test_img_path))

    assert coords["found"] is True
    # 320 * (1920/640) = 320 * 3 = 960
    # 180 * (1080/360) = 180 * 3 = 540
    assert coords["x"] == 960
    assert coords["y"] == 540


@patch("google.genai.Client")
def test_locate_element_not_found(
    mock_client_cls: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Verify locate_element returns found=False when element is missing."""
    monkeypatch.setenv("GEMINI_API_KEY", "mock-test-key")

    test_img_path = tmp_path / "not_found.jpg"
    img = Image.new("RGB", (300, 200), color="black")
    img.save(test_img_path, format="JPEG")

    mock_response = MagicMock()
    mock_response.text = '{"found": false, "x": 0, "y": 0}'
    mock_client_inst = MagicMock()
    mock_client_inst.models.generate_content.return_value = mock_response
    mock_client_cls.return_value = mock_client_inst

    coords = locate_element("Print button", screenshot_path=str(test_img_path))
    assert coords["found"] is False
    assert coords["x"] == 0
    assert coords["y"] == 0


@patch("vision.tools.locate_element")
@patch("tools.registry.execute_tool")
def test_click_element_tool_success(
    mock_exec_tool: MagicMock,
    mock_locate: MagicMock,
) -> None:
    """Verify ClickElementTool locates element and calls registry 'click' tool."""
    mock_locate.return_value = {"found": True, "x": 450, "y": 250}
    mock_exec_tool.return_value = ToolResult(
        success=True,
        data={"x": 450, "y": 250, "button": "left"},
        message="Successfully clicked",
    )

    tool = ClickElementTool()
    res: ToolResult = tool.run(description="File menu in Notepad")

    assert isinstance(res, ToolResult)
    assert res.success is True
    assert "File menu in Notepad" in res.message
    assert res.data["x"] == 450
    assert res.data["y"] == 250

    mock_exec_tool.assert_called_once_with(
        "click",
        {"x": 450, "y": 250, "button": "left", "clicks": 1},
    )


@patch("vision.tools.locate_element")
def test_click_element_tool_not_found(mock_locate: MagicMock) -> None:
    """Verify ClickElementTool returns structured failure when element is not found."""
    mock_locate.return_value = {"found": False, "x": 0, "y": 0}

    tool = ClickElementTool()
    res: ToolResult = tool.run(description="Nonexistent button")

    assert isinstance(res, ToolResult)
    assert res.success is False
    assert "not found" in res.message.lower()


def test_click_element_tool_empty_description() -> None:
    """Verify ClickElementTool handles empty description cleanly."""
    tool = ClickElementTool()
    res: ToolResult = tool.run(description="")

    assert isinstance(res, ToolResult)
    assert res.success is False
    assert "required" in res.message.lower()


# ---------------------------------------------------------------------------
# 6. Schemas & Registry Integration Tests
# ---------------------------------------------------------------------------

def test_tools_schema_definitions() -> None:
    """Verify all 4 tools export valid JSON schemas adhere to OpenAI/Gemini format."""
    for tool in TOOLS:
        schema = tool.get_schema()
        assert "name" in schema
        assert schema["name"] == tool.name
        assert "description" in schema
        assert "parameters" in schema
        assert schema["parameters"]["type"] == "object"


def test_tools_export_list() -> None:
    """Verify TOOLS list contains all 4 tools up to 22 October."""
    assert len(TOOLS) == 4
    tool_names = [t.name for t in TOOLS]
    assert "take_screenshot" in tool_names
    assert "describe_screen" in tool_names
    assert "explain_screen_error" in tool_names
    assert "click_element" in tool_names


def test_registry_auto_loads_all_vision_tools() -> None:
    """Verify that tools.registry automatically discovers and loads all 4 vision tools."""
    from tools.registry import TOOL_REGISTRY, execute_tool

    assert "take_screenshot" in TOOL_REGISTRY
    assert "describe_screen" in TOOL_REGISTRY
    assert "explain_screen_error" in TOOL_REGISTRY
    assert "click_element" in TOOL_REGISTRY

    # Execute screenshot tool through registry
    res = execute_tool("take_screenshot")
    assert isinstance(res, ToolResult)
    assert res.success is True
    assert os.path.exists(res.data["file_path"])


if __name__ == "__main__":
    sys.exit(pytest.main(["-v", __file__]))
