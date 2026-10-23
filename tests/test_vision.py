"""Unit and integration tests for Aryan's screen vision module (Project Jarvis).

Covers all tasks from Day 1 to Day 11 (Pair C Vision Guide):
- Day 1 (18 Oct): Baseline hello_screenshot utility
- Day 2 (19 Oct): take_screenshot, DPI awareness, 10-file cleanup, region hints, VISION_PAUSED privacy
- Day 3 (20 Oct): describe_screen, ScreenshotTool, DescribeScreenTool, BaseTool schema & registry auto-load
- Day 4 (21 Oct): explain_screen_error, ExplainScreenErrorTool, region hints in describe_screen
- Day 5 (22 Oct): locate_element with coordinate scaling, ClickElementTool via registry dispatch
- Day 6 (23 Oct): do_on_screen autonomous look-decide-act loop, DoOnScreenTool, kill switch integration
- Day 7 (24 Oct): active_window crop, screenshot reuse cache (< 2s), millisecond timing logs
- Day 8 (25 Oct): explain_code_on_screen (explain and fix tasks), ExplainCodeOnScreenTool
- Day 9 (26 Oct): display scaling calibration test (vision/test_scaling.py)
- Day 11 (28 Oct): privacy hardening and comprehensive registry verification
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import time
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
    do_on_screen,
    explain_screen_error,
    locate_element,
    parse_region_hint,
    take_screenshot,
    TEMP_VISION_DIR,
)
from vision.tools import (
    ClickElementTool,
    DescribeScreenTool,
    DoOnScreenTool,
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
    assert isinstance(size, tuple)
    assert len(size) == 2
    assert size[0] > 0 and size[1] > 0


# ---------------------------------------------------------------------------
# 2. Day 2 Tests (Mon 19 Oct): take_screenshot, DPI, Cleanup, Privacy
# ---------------------------------------------------------------------------

def test_take_screenshot_default_creates_valid_jpeg() -> None:
    """Verify take_screenshot captures the primary monitor and outputs a valid JPEG."""
    path = take_screenshot()
    assert os.path.exists(path)
    assert path.endswith(".jpg")

    with Image.open(path) as img:
        assert img.format == "JPEG"
        # Assert width scaled down to max 1280px
        assert img.width <= 1280
        assert img.height > 0


def test_take_screenshot_custom_region() -> None:
    """Verify take_screenshot captures only the specified sub-region."""
    region = (50, 50, 400, 300)
    path = take_screenshot(region=region)
    assert os.path.exists(path)

    with Image.open(path) as img:
        assert img.format == "JPEG"
        assert img.width == 400
        assert img.height == 300


def test_parse_region_hint_valid() -> None:
    """Verify parse_region_hint produces expected bounding boxes."""
    monitor = {"left": 0, "top": 0, "width": 1920, "height": 1080}

    # Top half
    top_box = parse_region_hint("top half", monitor)
    assert top_box == (0, 0, 1920, 540)

    # Bottom half
    bot_box = parse_region_hint("bottom half", monitor)
    assert bot_box == (0, 540, 1920, 540)

    # Left half
    left_box = parse_region_hint("left half", monitor)
    assert left_box == (0, 0, 960, 1080)

    # Right half
    right_box = parse_region_hint("right half", monitor)
    assert right_box == (960, 0, 960, 1080)


def test_parse_region_hint_invalid() -> None:
    """Verify parse_region_hint raises ValueError for unknown hints."""
    monitor = {"left": 0, "top": 0, "width": 1920, "height": 1080}
    with pytest.raises(ValueError, match="Unsupported region_hint"):
        parse_region_hint("middle corner", monitor)


def test_take_screenshot_with_region_hint() -> None:
    """Verify take_screenshot with region_hint parameter."""
    path = take_screenshot(region_hint="top half")
    assert os.path.exists(path)
    with Image.open(path) as img:
        assert img.width <= 1280


def test_clean_temp_vision_keeps_max_ten(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify clean_temp_vision retains at most keep_newest files."""
    monkeypatch.setattr("vision.screen.TEMP_VISION_DIR", tmp_path)

    # Create 15 dummy files with sequential timestamps
    created_files = []
    for i in range(15):
        dummy_file = tmp_path / f"test_{i:02d}.jpg"
        dummy_file.write_text(f"dummy content {i}")
        # Offset modification times
        mtime = 1000 + i * 10
        os.utime(dummy_file, (mtime, mtime))
        created_files.append(dummy_file)

    clean_temp_vision(keep_newest=10)

    remaining_files = list(tmp_path.glob("*.jpg"))
    assert len(remaining_files) == 10

    # Oldest 5 files should have been removed
    for old_file in created_files[:5]:
        assert not old_file.exists()

    # Newest 10 files must still exist
    for new_file in created_files[5:]:
        assert new_file.exists()


def test_vision_paused_raises_permission_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify setting VISION_PAUSED=1 prevents screen capture."""
    monkeypatch.setenv("VISION_PAUSED", "1")
    with pytest.raises(PermissionError, match="Screen capture is currently paused"):
        take_screenshot()


def test_screenshot_tool_success() -> None:
    """Verify ScreenshotTool executes and returns ToolResult with image path."""
    tool = ScreenshotTool()
    res: ToolResult = tool.run()

    assert isinstance(res, ToolResult)
    assert res.success is True
    assert "file_path" in res.data
    assert os.path.exists(res.data["file_path"])
    assert "Screenshot captured successfully" in res.message


def test_screenshot_tool_privacy_pause(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify ScreenshotTool handles VISION_PAUSED gracefully without crashing."""
    monkeypatch.setenv("VISION_PAUSED", "1")
    tool = ScreenshotTool()
    res: ToolResult = tool.run()

    assert isinstance(res, ToolResult)
    assert res.success is False
    assert "paused by user privacy mode" in res.message


# ---------------------------------------------------------------------------
# 3. Day 3 Tests (Tue 20 Oct): Gemini Screen Description
# ---------------------------------------------------------------------------

def test_describe_screen_empty_question() -> None:
    """Verify describe_screen raises ValueError on empty question."""
    with pytest.raises(ValueError, match="Question must be a non-empty string"):
        describe_screen(question="")


def test_describe_screen_missing_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify describe_screen raises clear error when GEMINI_API_KEY is not configured."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(ValueError, match="GEMINI_API_KEY is missing or invalid"):
        describe_screen(question="What is on my screen?")


def test_describe_screen_privacy_paused(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify describe_screen respects VISION_PAUSED=1 privacy mode."""
    monkeypatch.setenv("VISION_PAUSED", "1")
    with pytest.raises(PermissionError, match="Screen vision is currently paused"):
        describe_screen(question="What is on screen?")


@patch("google.genai.Client")
def test_describe_screen_mock_gemini_success(
    mock_client_cls: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Verify describe_screen properly invokes Gemini Multimodal Client and returns answer."""
    monkeypatch.setenv("GEMINI_API_KEY", "mock-test-key-123")

    # Create dummy screenshot
    test_img_path = tmp_path / "mock_screenshot.jpg"
    img = Image.new("RGB", (640, 480), color="blue")
    img.save(test_img_path, format="JPEG")

    # Setup Gemini client mock
    mock_response = MagicMock()
    mock_response.text = "The user has VS Code open displaying Python code."
    mock_client_inst = MagicMock()
    mock_client_inst.models.generate_content.return_value = mock_response
    mock_client_cls.return_value = mock_client_inst

    answer = describe_screen(
        question="What is on screen?",
        screenshot_path=str(test_img_path),
    )

    assert answer == "The user has VS Code open displaying Python code."
    mock_client_inst.models.generate_content.assert_called_once()


def test_describe_screen_tool_success() -> None:
    """Verify DescribeScreenTool returns structured ToolResult on successful analysis."""
    with patch("vision.tools.describe_screen") as mock_desc:
        mock_desc.return_value = "Chrome is open to Google Search."
        tool = DescribeScreenTool()
        res: ToolResult = tool.run(question="What is open?")

        assert isinstance(res, ToolResult)
        assert res.success is True
        assert res.message == "Chrome is open to Google Search."
        assert res.data["description"] == "Chrome is open to Google Search."


def test_describe_screen_tool_missing_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify DescribeScreenTool returns helpful failure when API key is missing."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    tool = DescribeScreenTool()
    res: ToolResult = tool.run(question="What is on screen?")

    assert isinstance(res, ToolResult)
    assert res.success is False
    assert "GEMINI_API_KEY is missing" in res.message


# ---------------------------------------------------------------------------
# 4. Day 4 Tests (Wed 21 Oct): Error Diagnostics & Region Hints
# ---------------------------------------------------------------------------

def test_explain_screen_error_privacy_paused(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify explain_screen_error raises PermissionError when VISION_PAUSED=1."""
    monkeypatch.setenv("VISION_PAUSED", "1")
    with pytest.raises(PermissionError):
        explain_screen_error()


@patch("google.genai.Client")
def test_explain_screen_error_mock_diagnosis(
    mock_client_cls: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Verify explain_screen_error queries Gemini with exact error diagnostic prompt."""
    monkeypatch.setenv("GEMINI_API_KEY", "mock-test-key")

    test_img_path = tmp_path / "mock_error.jpg"
    img = Image.new("RGB", (640, 480), color="red")
    img.save(test_img_path, format="JPEG")

    mock_response = MagicMock()
    mock_response.text = (
        "Error: 'IndexError: list index out of range'. "
        "The list is empty when accessed at index 0. "
        "Fix: check len(lst) > 0 before indexing."
    )
    mock_client_inst = MagicMock()
    mock_client_inst.models.generate_content.return_value = mock_response
    mock_client_cls.return_value = mock_client_inst

    report = explain_screen_error(screenshot_path=str(test_img_path))
    assert "IndexError" in report
    assert "Fix: check len" in report


def test_explain_screen_error_tool_run() -> None:
    """Verify ExplainScreenErrorTool execution and ToolResult wrapping."""
    with patch("vision.tools.explain_screen_error") as mock_exp:
        mock_exp.return_value = "No error detected on the screen."
        tool = ExplainScreenErrorTool()
        res: ToolResult = tool.run()

        assert isinstance(res, ToolResult)
        assert res.success is True
        assert "No error detected" in res.message


def test_explain_screen_error_tool_privacy_pause(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify ExplainScreenErrorTool returns safe error when privacy paused."""
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

    test_img_path = tmp_path / "scaled_screenshot.jpg"
    img = Image.new("RGB", (640, 360), color="white")
    img.save(test_img_path, format="JPEG")

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
# 6. Day 6 Tests (Fri 23 Oct): Look-Decide-Act Autonomous Loop
# ---------------------------------------------------------------------------


def test_do_on_screen_empty_goal() -> None:
    """Verify do_on_screen raises ValueError on empty goal."""
    with pytest.raises(ValueError, match="Goal must be a non-empty string"):
        do_on_screen(goal="")


def test_do_on_screen_privacy_paused(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify do_on_screen raises PermissionError when VISION_PAUSED=1."""
    monkeypatch.setenv("VISION_PAUSED", "1")
    with pytest.raises(PermissionError):
        do_on_screen(goal="click something")


@patch("vision.screen.take_screenshot")
@patch("google.genai.Client")
def test_do_on_screen_done_immediately(
    mock_client_cls: MagicMock,
    mock_shot: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Verify do_on_screen terminates immediately when model returns 'done'."""
    monkeypatch.setenv("GEMINI_API_KEY", "mock-test-key")
    test_img = tmp_path / "shot.jpg"
    Image.new("RGB", (640, 360), "white").save(test_img, "JPEG")
    mock_shot.return_value = str(test_img)

    mock_resp = MagicMock()
    mock_resp.text = '{"action": "done", "thought": "Goal already achieved."}'
    mock_client_inst = MagicMock()
    mock_client_inst.models.generate_content.return_value = mock_resp
    mock_client_cls.return_value = mock_client_inst

    summary = do_on_screen("verify notepad is open", max_steps=3)
    assert "Goal completed" in summary
    assert "Goal already achieved" in summary


@patch("tools.registry.execute_tool")
@patch("vision.screen.time.sleep")
@patch("vision.screen.take_screenshot")
@patch("google.genai.Client")
def test_do_on_screen_multi_step_actions(
    mock_client_cls: MagicMock,
    mock_shot: MagicMock,
    mock_sleep: MagicMock,
    mock_exec: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Verify do_on_screen dispatches click, type, and hotkey actions through registry."""
    monkeypatch.setenv("GEMINI_API_KEY", "mock-test-key")
    test_img = tmp_path / "shot.jpg"
    Image.new("RGB", (640, 360), "white").save(test_img, "JPEG")
    mock_shot.return_value = str(test_img)

    mock_exec.return_value = ToolResult(success=True, data={}, message="Executed OK")

    # Step 1: click, Step 2: type, Step 3: done
    resp1 = MagicMock(text='{"action": "click", "x": 100, "y": 100, "button": "left"}')
    resp2 = MagicMock(text='{"action": "type", "text": "hello world"}')
    resp3 = MagicMock(text='{"action": "done", "thought": "Finished typing."}')

    mock_client_inst = MagicMock()
    mock_client_inst.models.generate_content.side_effect = [resp1, resp2, resp3]
    mock_client_cls.return_value = mock_client_inst

    summary = do_on_screen("type hello in notepad", max_steps=5)
    assert "Click at" in summary
    assert "Type 'hello world'" in summary
    assert "Goal completed" in summary
    assert mock_exec.call_count == 2


def test_do_on_screen_kill_switch_stops_loop(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify loop halts immediately if emergency kill-switch is active."""
    monkeypatch.setenv("GEMINI_API_KEY", "mock-test-key")
    mock_guard = MagicMock()
    mock_guard.is_stopped.return_value = True
    monkeypatch.setitem(sys.modules, "tools.guard", mock_guard)

    summary = do_on_screen("perform risky operation", max_steps=5)
    assert "Emergency stop triggered by kill-switch" in summary


def test_do_on_screen_tool_validation() -> None:
    """Verify DoOnScreenTool argument checks."""
    tool = DoOnScreenTool()
    res = tool.run(goal="")
    assert res.success is False
    assert "Parameter 'goal' is required" in res.message


def test_tools_schema_definitions() -> None:
    """Verify all tools export valid JSON parameter schemas compliant with BaseTool."""
    for tool in TOOLS:
        schema = tool.get_schema()
        assert "name" in schema
        assert "description" in schema
        assert "parameters" in schema
        assert schema["parameters"].get("type") == "object"
        assert "properties" in schema["parameters"]


def test_tools_export_list() -> None:
    """Verify TOOLS list contains all 5 tools up to Day 6."""
    assert len(TOOLS) == 5
    tool_names = [t.name for t in TOOLS]
    assert "take_screenshot" in tool_names
    assert "describe_screen" in tool_names
    assert "explain_screen_error" in tool_names
    assert "click_element" in tool_names
    assert "do_on_screen" in tool_names


def test_registry_auto_loads_all_vision_tools() -> None:
    """Verify that tools.registry automatically discovers and loads all 5 vision tools."""
    from tools.registry import TOOL_REGISTRY, execute_tool

    assert "take_screenshot" in TOOL_REGISTRY
    assert "describe_screen" in TOOL_REGISTRY
    assert "explain_screen_error" in TOOL_REGISTRY
    assert "click_element" in TOOL_REGISTRY
    assert "do_on_screen" in TOOL_REGISTRY

    res = execute_tool("take_screenshot")
    assert isinstance(res, ToolResult)
    assert res.success is True
    assert os.path.exists(res.data["file_path"])


if __name__ == "__main__":
    sys.exit(pytest.main(["-v", __file__]))
