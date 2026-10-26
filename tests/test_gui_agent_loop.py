"""
Unit and Integration Tests for Look-Decide-Act GUI Agent (Task 20).
Verifies autonomous screen perception loop, multimodal action determination,
guardrail enforcement (destructive command filter, emergency stop, privacy mode),
and GuiAgentTool execution.
"""

from pathlib import Path
import pytest
from unittest.mock import MagicMock, patch
from PIL import Image

from vision.loop import GuiAgent, GuiAgentTool
from tools.base import ToolResult


class TestGuiAgentGuardrails:
    """Test guardrails against destructive commands and safety stops."""

    def test_destructive_command_detection(self):
        agent = GuiAgent()
        assert agent._is_destructive_text("rmdir /s /q C:\\Windows") is True
        assert agent._is_destructive_text("format d:") is True
        assert agent._is_destructive_text("del /s /q *.*") is True
        assert agent._is_destructive_text("rm -rf /") is True
        assert agent._is_destructive_text("diskpart") is True

        # Safe commands should not trigger
        assert agent._is_destructive_text("git status") is False
        assert agent._is_destructive_text("echo Hello World") is False
        assert agent._is_destructive_text("python -m pytest") is False

    def test_privacy_pause_enforcement(self, monkeypatch):
        monkeypatch.setenv("VISION_PAUSED", "1")
        agent = GuiAgent()
        with pytest.raises(PermissionError, match="privacy mode"):
            agent.run(goal="Check my inbox")

    def test_emergency_kill_switch_halts_loop(self, tmp_path):
        dummy_img = tmp_path / "dummy.png"
        Image.new("RGB", (100, 100), color="blue").save(dummy_img)

        agent = GuiAgent(max_steps=5)
        # Mock emergency stop triggered
        with patch.object(agent, "_check_emergency_kill_switch", return_value=True):
            outcome = agent.run(goal="Click start button")
            assert outcome["completed"] is False
            assert "Emergency stop" in outcome["summary"]
            assert len(outcome["steps"]) == 1
            assert outcome["steps"][0]["action"] == "abort"


class TestGuiAgentLoopExecution:
    """Test full multi-turn look-decide-act loop with mock visual decisions."""

    @pytest.fixture
    def dummy_screenshot(self, tmp_path):
        img_path = tmp_path / "mock_screen.png"
        Image.new("RGB", (1920, 1080), color="white").save(img_path)
        return img_path

    def test_look_decide_act_success_flow(self, dummy_screenshot):
        agent = GuiAgent(max_steps=5, pause_between_steps=0.01)

        mock_capture = (dummy_screenshot, 0, 0, 1920, 1080)
        decisions = [
            {"action": "click", "x": 500, "y": 300, "button": "left", "thought": "Click search input box"},
            {"action": "type", "text": "Project JARVIS", "thought": "Enter search query"},
            {"action": "done", "thought": "Search query entered and results visible"}
        ]

        with patch.object(agent, "capture_screen", return_value=mock_capture), \
             patch.object(agent, "decide_next_action", side_effect=decisions), \
             patch("tools.registry.execute_tool", return_value=ToolResult(success=True, message="Action OK")):

            outcome = agent.run(goal="Search for Project JARVIS")
            assert outcome["completed"] is True
            assert outcome["total_steps"] == 3
            assert outcome["steps"][0]["action"] == "click"
            assert outcome["steps"][1]["action"] == "type"
            assert outcome["steps"][2]["action"] == "done"

    def test_destructive_type_is_blocked_in_loop(self, dummy_screenshot):
        agent = GuiAgent(max_steps=5, pause_between_steps=0.01)

        mock_capture = (dummy_screenshot, 0, 0, 1920, 1080)
        hazardous_decision = {
            "action": "type",
            "text": "rmdir /s /q C:\\",
            "thought": "Clean up files"
        }

        with patch.object(agent, "capture_screen", return_value=mock_capture), \
             patch.object(agent, "decide_next_action", return_value=hazardous_decision), \
             patch("tools.registry.execute_tool") as mock_exec:

            outcome = agent.run(goal="Clean up temp folder")
            assert outcome["completed"] is False
            assert "Blocked hazardous destructive command" in outcome["summary"]
            # Verify destructive text was NEVER dispatched to execute_tool
            mock_exec.assert_not_called()


class TestGuiAgentTool:
    """Test GuiAgentTool BaseTool wrapper."""

    def test_tool_schema_and_execution(self, tmp_path):
        tool = GuiAgentTool()
        schema = tool.get_schema()
        assert schema["name"] == "gui_agent"
        assert "goal" in schema["parameters"]["required"]

        dummy_screen = tmp_path / "screen.png"
        Image.new("RGB", (100, 100), color="black").save(dummy_screen)

        mock_capture = (dummy_screen, 0, 0, 100, 100)
        done_decision = {"action": "done", "thought": "Already done"}

        with patch.object(GuiAgent, "capture_screen", return_value=mock_capture), \
             patch.object(GuiAgent, "decide_next_action", return_value=done_decision):
            res = tool.run(goal="Inspect screen state", max_steps=2)
            assert res.success is True
            assert "Goal completed" in res.message or "done" in res.message.lower()
