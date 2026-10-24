"""
Unit tests for tools/guard.py: Emergency kill-switch and action logger.
Author: Abhijit (System & Automation Engineer)
"""

import os
import sys
import threading
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from unittest.mock import MagicMock, patch
try:
    import pytest
except ImportError:
    pytest = None  # type: ignore

from tools.guard import (
    STOP,
    start_kill_switch,
    stop_kill_switch,
    is_stopped,
    reset_stop,
    trigger_stop,
    log_action,
    _on_kill_switch_triggered,
    _get_log_file_path,
)
from tools.control_tools import TypeTextTool, PressKeysTool, ClickTool, ScrollTool


if pytest is not None:
    @pytest.fixture(autouse=True)
    def cleanup_guard_state():
        """Ensures kill switch is reset before and after every test."""
        reset_stop()
        yield
        reset_stop()
        stop_kill_switch()


# ---------------------------------------------------------------------------
# 1. Kill Switch Event Tests
# ---------------------------------------------------------------------------

def test_kill_switch_default_state() -> None:
    """Verifies kill switch is un-triggered by default."""
    reset_stop()
    assert is_stopped() is False
    assert STOP.is_set() is False


def test_kill_switch_trigger_and_reset() -> None:
    """Verifies manual triggering and resetting of emergency stop."""
    assert is_stopped() is False
    trigger_stop()
    assert is_stopped() is True
    assert STOP.is_set() is True

    reset_stop()
    assert is_stopped() is False
    assert STOP.is_set() is False


def test_kill_switch_callback() -> None:
    """Verifies the hotkey trigger callback sets the STOP event."""
    assert is_stopped() is False
    _on_kill_switch_triggered()
    assert is_stopped() is True


def test_start_and_stop_kill_switch() -> None:
    """Verifies start_kill_switch registers listener and stop_kill_switch tears it down."""
    with patch("pynput.keyboard.GlobalHotKeys") as mock_hotkeys_cls:
        mock_instance = MagicMock()
        mock_instance.is_alive.return_value = True
        mock_hotkeys_cls.return_value = mock_instance

        # First start
        res1 = start_kill_switch()
        assert res1 is True
        mock_hotkeys_cls.assert_called_once()
        mock_instance.start.assert_called_once()

        # Idempotent start
        res2 = start_kill_switch()
        assert res2 is True

        # Stop
        stop_kill_switch()
        mock_instance.stop.assert_called_once()


# ---------------------------------------------------------------------------
# 2. Action Logger & Sanitization Tests
# ---------------------------------------------------------------------------

def test_log_action_creates_log_entry(tmp_path: Path) -> None:
    """Verifies log_action writes a structured single line with timestamp."""
    log_file = tmp_path / "logs" / "actions.log"
    with patch("tools.guard._get_log_file_path", return_value=log_file):
        log_action("test_tool", {"param": "value123"}, "Operation succeeded")

        assert log_file.exists()
        content = log_file.read_text(encoding="utf-8")
        assert "TOOL: test_tool" in content
        assert "param" in content
        assert "value123" in content
        assert "RESULT: Operation succeeded" in content
        # Ensure single line
        lines = [line for line in content.splitlines() if line.strip()]
        assert len(lines) == 1


def test_log_action_redacts_api_keys_and_secrets(tmp_path: Path) -> None:
    """Verifies secrets and API keys are completely redacted from logs."""
    log_file = tmp_path / "logs" / "actions.log"
    with patch("tools.guard._get_log_file_path", return_value=log_file):
        secret_args = {
            "api_key": "AIzaSySecretApiKey1234567890abcdef",
            "gemini_api_key": "secret_gemini_key",
            "password": "SuperSecretPassword!",
            "token": "sk-1234567890abcdef1234567890",
            "normal_arg": "normal_value",
        }
        log_action("auth_tool", secret_args, "OK")

        content = log_file.read_text(encoding="utf-8")
        assert "AIzaSySecretApiKey1234567890abcdef" not in content
        assert "secret_gemini_key" not in content
        assert "SuperSecretPassword!" not in content
        assert "sk-1234567890abcdef1234567890" not in content
        assert "[REDACTED_SECRET]" in content
        assert "normal_value" in content


def test_log_action_redacts_file_contents(tmp_path: Path) -> None:
    """Verifies file contents and large code bodies are not dumped into the log."""
    log_file = tmp_path / "logs" / "actions.log"
    with patch("tools.guard._get_log_file_path", return_value=log_file):
        file_args = {
            "file_path": "secret_document.txt",
            "content": "CONFIDENTIAL: Internal company financial reports and secret records.",
            "code": "import os\nfor i in range(10):\n    print('Confidential code execution')",
        }
        log_action("write_file", file_args, "File written")

        content = log_file.read_text(encoding="utf-8")
        assert "CONFIDENTIAL: Internal company financial reports" not in content
        assert "[FILE_CONTENT:" in content
        assert "[CODE:" in content
        assert "secret_document.txt" in content


def test_log_action_handles_multiline_output(tmp_path: Path) -> None:
    """Verifies multi-line arguments and results are compacted into a single line."""
    log_file = tmp_path / "logs" / "actions.log"
    with patch("tools.guard._get_log_file_path", return_value=log_file):
        log_action(
            "multiline_tool",
            {"query": "line1\nline2\nline3"},
            "result_line_1\nresult_line_2\nresult_line_3",
        )

        content = log_file.read_text(encoding="utf-8")
        lines = [line for line in content.splitlines() if line.strip()]
        assert len(lines) == 1


# ---------------------------------------------------------------------------
# 3. Control Tools Kill Switch Enforcement Tests
# ---------------------------------------------------------------------------

def test_type_text_tool_blocked_by_kill_switch() -> None:
    """Verifies TypeTextTool aborts immediately when kill switch is active."""
    trigger_stop()
    tool = TypeTextTool()

    with patch("pyautogui.write") as mock_write, patch("pyautogui.press") as mock_press:
        res = tool.run(text="Should not be typed", press_enter=True)

        assert res.success is False
        assert "kill switch is active" in res.message.lower()
        mock_write.assert_not_called()
        mock_press.assert_not_called()


def test_press_keys_tool_blocked_by_kill_switch() -> None:
    """Verifies PressKeysTool aborts immediately when kill switch is active."""
    trigger_stop()
    tool = PressKeysTool()

    with patch("pyautogui.press") as mock_press, patch("pyautogui.hotkey") as mock_hotkey:
        res = tool.run(keys=["ctrl", "c"])

        assert res.success is False
        assert "kill switch is active" in res.message.lower()
        mock_press.assert_not_called()
        mock_hotkey.assert_not_called()


def test_click_tool_blocked_by_kill_switch() -> None:
    """Verifies ClickTool aborts immediately when kill switch is active."""
    trigger_stop()
    tool = ClickTool()

    with patch("pyautogui.click") as mock_click:
        res = tool.run(x=100, y=200)

        assert res.success is False
        assert "kill switch is active" in res.message.lower()
        mock_click.assert_not_called()


def test_scroll_tool_blocked_by_kill_switch() -> None:
    """Verifies ScrollTool aborts immediately when kill switch is active."""
    trigger_stop()
    tool = ScrollTool()

    with patch("pyautogui.scroll") as mock_scroll:
        res = tool.run(clicks=5)

        assert res.success is False
        assert "kill switch is active" in res.message.lower()
        mock_scroll.assert_not_called()


def test_press_keys_stops_mid_stream_on_kill_switch() -> None:
    """Verifies that if the kill switch triggers during repeated key presses, execution halts early."""
    reset_stop()
    tool = PressKeysTool()

    pressed: list[str] = []

    def mock_press(key: str, presses: int = 1, interval: float = 0.0) -> None:
        pressed.append(key)
        if len(pressed) == 2:
            trigger_stop()

    with patch("pyautogui.press", side_effect=mock_press):
        res = tool.run(keys="down", presses=5, interval=0.01)

        assert res.success is False
        assert "kill switch" in res.message.lower()
        assert len(pressed) == 2
        assert res.data["presses_completed"] == 2


if __name__ == "__main__":
    print("=" * 60)
    print("RUNNING DAY 6 VERIFICATION: Kill-switch hotkey & Action log")
    print("=" * 60)

    # 1. State tests
    reset_stop()
    test_kill_switch_default_state()
    test_kill_switch_trigger_and_reset()
    test_kill_switch_callback()
    print("[PASS] Kill switch event & state transitions")

    # 2. Hotkey registration
    test_start_and_stop_kill_switch()
    print("[PASS] Global hotkey registration & cleanup")

    # 3. Control tools enforcement
    test_type_text_tool_blocked_by_kill_switch()
    test_press_keys_tool_blocked_by_kill_switch()
    test_click_tool_blocked_by_kill_switch()
    test_scroll_tool_blocked_by_kill_switch()
    test_press_keys_stops_mid_stream_on_kill_switch()
    print("[PASS] Control tools kill-switch enforcement & early halting")

    # 4. Action logging & sanitization
    test_dir = Path("logs")
    log_action(
        "verify_tool",
        {
            "query": "system_status",
            "api_key": "AIzaSySecretVerificationKey12345",
            "content": "Secret payload content that must not appear in logs",
        },
        "Verification check completed successfully.",
    )
    assert (test_dir / "actions.log").exists(), "actions.log was not created!"
    log_data = (test_dir / "actions.log").read_text(encoding="utf-8")
    assert "AIzaSySecretVerificationKey12345" not in log_data, "API key leaked into logs!"
    assert "Secret payload content" not in log_data, "File content leaked into logs!"
    assert "[REDACTED_SECRET]" in log_data or "[REDACTED_KEY]" in log_data
    assert "[FILE_CONTENT:" in log_data
    print("[PASS] Action logging with API key & file content redaction")

    reset_stop()
    print("=" * 60)
    print("ALL DAY 6 ACCEPTANCE CHECKS PASSED SUCCESSFULLY!")
    print("=" * 60)

