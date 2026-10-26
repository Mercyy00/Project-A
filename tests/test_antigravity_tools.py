"""
Unit tests for Google Antigravity Desktop Agent and Automation.
Author: Abhijit (System & Automation Engineer)
"""

import os
import unittest
from pathlib import Path

from tools.antigravity_tools import AntigravityControlTool, AntigravityPromptTool
from ui.server import parse_antigravity_intent


class TestAntigravityControlTool(unittest.TestCase):
    """Verifies Antigravity tool schema, prompt building, and directives."""

    def setUp(self) -> None:
        self.tool = AntigravityControlTool()

    def test_schema_validity(self) -> None:
        """Verify schema properties and action enums."""
        schema = self.tool.get_schema()
        self.assertEqual(schema["name"], "antigravity_control")
        actions = schema["parameters"]["properties"]["action"]["enum"]
        self.assertIn("launch", actions)
        self.assertIn("open_folder", actions)
        self.assertIn("new_chat", actions)
        self.assertIn("send_prompt", actions)
        self.assertIn("choose_model", actions)

    def test_backward_compatibility_alias(self) -> None:
        """Verify AntigravityPromptTool is an alias of AntigravityControlTool."""
        self.assertEqual(AntigravityPromptTool, AntigravityControlTool)

    def test_write_prompt_formatting(self) -> None:
        """Verify directive structure with model and effort headers."""
        res = self.tool.run(
            action="write_prompt",
            task="Build a full stack modern app",
            model="Gemini 3.8 Flash",
            effort="High",
            attachment="src/index.ts",
        )
        self.assertTrue(res.success)
        prompt_file = res.data.get("prompt_file")
        self.assertIsNotNone(prompt_file)
        self.assertTrue(os.path.exists(prompt_file))
        content = Path(prompt_file).read_text(encoding="utf-8")
        self.assertIn("Model Selection: Gemini 3.8 Flash (High Effort)", content)
        self.assertIn("@src/index.ts", content)


class TestAntigravityIntentParsing(unittest.TestCase):
    """Verifies intent recognition for Antigravity desktop automation."""

    def test_launch_intent(self) -> None:
        """Verify launching Antigravity."""
        i_launch = parse_antigravity_intent("open antigravity")
        self.assertIsNotNone(i_launch)
        self.assertEqual(i_launch["action"], "launch")

    def test_open_folder_intent(self) -> None:
        """Verify opening specific folder in Antigravity."""
        i_folder = parse_antigravity_intent("open folder Project - A in antigravity")
        self.assertIsNotNone(i_folder)
        self.assertEqual(i_folder["action"], "open_folder")
        self.assertEqual(i_folder["folder_path"], "Project - A")

    def test_new_chat_intent(self) -> None:
        """Verify new chat intent."""
        i_chat = parse_antigravity_intent("open new chat in antigravity")
        self.assertIsNotNone(i_chat)
        self.assertEqual(i_chat["action"], "new_chat")

    def test_send_prompt_intent(self) -> None:
        """Verify sending prompt to Antigravity."""
        i_send = parse_antigravity_intent("write prompt in antigravity create a modern portfolio")
        self.assertIsNotNone(i_send)
        self.assertEqual(i_send["action"], "send_prompt")
        self.assertIn("portfolio", i_send["prompt"])
        self.assertEqual(i_send["model"], "Gemini 3.8 Flash")
        self.assertEqual(i_send["effort"], "High")

    def test_meta_capabilities(self) -> None:
        """Verify capability inquiry returns structured explanation."""
        i_cap = parse_antigravity_intent("automate antigravity")
        self.assertIsNotNone(i_cap)
        self.assertEqual(i_cap["action"], "capabilities")
        self.assertIn("Google Antigravity", i_cap["message"])


if __name__ == "__main__":
    unittest.main()
