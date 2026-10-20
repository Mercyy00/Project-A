"""
Unit tests for OS and GUI control tools (pyautogui automation).
Author: Abhijit (System & Automation Engineer)
"""

from unittest.mock import MagicMock, patch
import pytest
import pyautogui

from tools.control_tools import (
    TypeTextTool,
    PressKeysTool,
    ClickTool,
    ScrollTool,
    CONTROL_TOOLS,
)
from tools.registry import execute_tool, TOOL_REGISTRY


# ---------------------------------------------------------------------------
# 1. TypeTextTool Tests
# ---------------------------------------------------------------------------

def test_type_text_tool_schema() -> None:
    """Verifies TypeTextTool schema defines required parameters."""
    tool = TypeTextTool()
    schema = tool.get_schema()
    assert schema["name"] == "type_text"
    assert "text" in schema["parameters"]["properties"]
    assert "text" in schema["parameters"]["required"]


def test_type_text_tool_success() -> None:
    """Verifies text typing with and without enter press."""
    tool = TypeTextTool()

    with patch.object(pyautogui, "write") as mock_write, patch.object(pyautogui, "press") as mock_press:
        res = tool.run(text="Hello Jarvis", interval=0.02, press_enter=True)

        assert res.success is True
        assert res.data["chars_typed"] == len("Hello Jarvis")
        assert res.data["pressed_enter"] is True
        mock_write.assert_called_once_with("Hello Jarvis", interval=0.02)
        mock_press.assert_called_once_with("enter")


def test_type_text_tool_invalid_argument() -> None:
    """Verifies non-string text is rejected."""
    tool = TypeTextTool()
    res = tool.run(text=12345)  # type: ignore[arg-type]
    assert res.success is False
    assert "must be a string" in res.message


def test_type_text_tool_failsafe() -> None:
    """Verifies fail-safe exception is gracefully caught."""
    tool = TypeTextTool()
    with patch.object(pyautogui, "write", side_effect=pyautogui.FailSafeException):
        res = tool.run(text="aborted")
        assert res.success is False
        assert "fail-safe corner triggered" in res.message.lower()


# ---------------------------------------------------------------------------
# 2. PressKeysTool Tests
# ---------------------------------------------------------------------------

def test_press_keys_tool_schema() -> None:
    """Verifies PressKeysTool schema structure."""
    tool = PressKeysTool()
    schema = tool.get_schema()
    assert schema["name"] == "press_keys"
    assert "keys" in schema["parameters"]["properties"]


def test_press_single_key() -> None:
    """Verifies pressing an individual key (e.g. 'enter')."""
    tool = PressKeysTool()

    with patch.object(pyautogui, "press") as mock_press:
        res = tool.run(keys="enter")
        assert res.success is True
        assert res.data["keys"] == ["enter"]
        mock_press.assert_called_once_with("enter", presses=1, interval=0.1)


def test_press_hotkey_list() -> None:
    """Verifies pressing a hotkey combination via list (e.g. ['ctrl', 'c'])."""
    tool = PressKeysTool()

    with patch.object(pyautogui, "hotkey") as mock_hotkey:
        res = tool.run(keys=["ctrl", "c"])
        assert res.success is True
        assert res.data["keys"] == ["ctrl", "c"]
        mock_hotkey.assert_called_once_with("ctrl", "c")


def test_press_hotkey_string_split() -> None:
    """Verifies '+'-delimited shortcut string parsing (e.g. 'ctrl+shift+esc')."""
    tool = PressKeysTool()

    with patch.object(pyautogui, "hotkey") as mock_hotkey:
        res = tool.run(keys="ctrl+shift+esc")
        assert res.success is True
        assert res.data["keys"] == ["ctrl", "shift", "esc"]
        mock_hotkey.assert_called_once_with("ctrl", "shift", "esc")


def test_press_keys_empty_or_missing() -> None:
    """Verifies empty key input is rejected."""
    tool = PressKeysTool()
    res1 = tool.run(keys="")
    assert res1.success is False
    res2 = tool.run()
    assert res2.success is False


def test_press_keys_failsafe() -> None:
    """Verifies fail-safe handling in press_keys."""
    tool = PressKeysTool()
    with patch.object(pyautogui, "press", side_effect=pyautogui.FailSafeException):
        res = tool.run(keys="esc")
        assert res.success is False
        assert "fail-safe corner triggered" in res.message.lower()


# ---------------------------------------------------------------------------
# 3. ClickTool Tests
# ---------------------------------------------------------------------------

def test_click_tool_schema() -> None:
    """Verifies ClickTool schema definition."""
    tool = ClickTool()
    schema = tool.get_schema()
    assert schema["name"] == "click"
    assert "x" in schema["parameters"]["properties"]
    assert "y" in schema["parameters"]["properties"]
    assert "button" in schema["parameters"]["properties"]


def test_click_at_coordinates() -> None:
    """Verifies clicking at explicit (x, y) coordinates."""
    tool = ClickTool()

    with patch.object(pyautogui, "click") as mock_click:
        res = tool.run(x=500, y=300, clicks=2, button="left")
        assert res.success is True
        assert res.data["x"] == 500
        assert res.data["y"] == 300
        assert res.data["clicks"] == 2
        mock_click.assert_called_once_with(x=500, y=300, clicks=2, interval=0.1, button="left")


def test_click_at_current_position() -> None:
    """Verifies clicking at current cursor position when coordinates are omitted."""
    tool = ClickTool()
    mock_pos = MagicMock(x=250, y=180)

    with patch.object(pyautogui, "position", return_value=mock_pos), \
         patch.object(pyautogui, "click") as mock_click:
        res = tool.run(button="right")
        assert res.success is True
        assert res.data["x"] == 250
        assert res.data["y"] == 180
        assert res.data["button"] == "right"
        mock_click.assert_called_once_with(clicks=1, interval=0.1, button="right")


def test_click_invalid_inputs() -> None:
    """Verifies invalid button and negative coordinates are rejected."""
    tool = ClickTool()
    res_btn = tool.run(button="invalid_button")
    assert res_btn.success is False
    assert "Invalid mouse button" in res_btn.message

    res_neg = tool.run(x=-10, y=20)
    assert res_neg.success is False
    assert "cannot be negative" in res_neg.message


def test_click_failsafe() -> None:
    """Verifies fail-safe handling in click."""
    tool = ClickTool()
    with patch.object(pyautogui, "click", side_effect=pyautogui.FailSafeException):
        res = tool.run(x=10, y=10)
        assert res.success is False
        assert "fail-safe corner triggered" in res.message.lower()


# ---------------------------------------------------------------------------
# 4. ScrollTool Tests
# ---------------------------------------------------------------------------

def test_scroll_tool_schema() -> None:
    """Verifies ScrollTool schema."""
    tool = ScrollTool()
    schema = tool.get_schema()
    assert schema["name"] == "scroll"
    assert "clicks" in schema["parameters"]["properties"]


def test_scroll_up_and_down() -> None:
    """Verifies scrolling up and down with amount."""
    tool = ScrollTool()

    with patch.object(pyautogui, "scroll") as mock_scroll:
        # Scroll up
        res_up = tool.run(clicks=5)
        assert res_up.success is True
        assert res_up.data["direction"] == "up"
        mock_scroll.assert_called_with(5)

        # Scroll down with coordinates
        res_down = tool.run(clicks=-3, x=400, y=500)
        assert res_down.success is True
        assert res_down.data["direction"] == "down"
        mock_scroll.assert_called_with(-3, x=400, y=500)


def test_scroll_zero_or_invalid() -> None:
    """Verifies zero scroll amount is rejected."""
    tool = ScrollTool()
    res = tool.run(clicks=0)
    assert res.success is False
    assert "non-zero integer" in res.message


# ---------------------------------------------------------------------------
# 5. Registry Integration Tests
# ---------------------------------------------------------------------------

def test_control_tools_registered_in_registry() -> None:
    """Verifies all control tools are registered in TOOL_REGISTRY."""
    assert "type_text" in TOOL_REGISTRY
    assert "press_keys" in TOOL_REGISTRY
    assert "click" in TOOL_REGISTRY
    assert "scroll" in TOOL_REGISTRY


def test_execute_tool_dispatches_control_tools() -> None:
    """Verifies execute_tool successfully dispatches to control tools."""
    with patch.object(pyautogui, "write"):
        res = execute_tool("type_text", {"text": "Dispatch test"})
        assert res.success is True

    with patch.object(pyautogui, "press"):
        res = execute_tool("press_keys", {"keys": "enter"})
        assert res.success is True

    with patch.object(pyautogui, "click"):
        res = execute_tool("click", {"x": 50, "y": 50})
        assert res.success is True

    with patch.object(pyautogui, "scroll"):
        res = execute_tool("scroll", {"clicks": 2})
        assert res.success is True
