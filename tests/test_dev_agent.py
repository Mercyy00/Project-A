"""
Unit tests for Autonomous Development Agent and VS Code Automation.
Author: Abhijit (System & Automation Engineer)
"""

import os
import shutil
import tempfile
import unittest
from pathlib import Path

from tools.dev_tools import DevAgentTool, find_vscode_executable
from ui.server import parse_dev_agent_intent


class TestDevAgentTool(unittest.TestCase):
    """Verifies DevAgentTool operations, scaffolding, syntax checking, and diagnostics."""

    def setUp(self) -> None:
        self.tool = DevAgentTool()
        self.test_dir = tempfile.mkdtemp(prefix="test_jarvis_dev_")

    def tearDown(self) -> None:
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_schema_validity(self) -> None:
        """Verify tool schema has required fields and action enums."""
        schema = self.tool.get_schema()
        self.assertEqual(schema["name"], "dev_agent")
        actions = schema["parameters"]["properties"]["action"]["enum"]
        self.assertIn("open_vscode", actions)
        self.assertIn("create_file", actions)
        self.assertIn("scaffold_project", actions)
        self.assertIn("run_project", actions)
        self.assertIn("check_syntax", actions)
        self.assertIn("diagnose_error", actions)

    def test_create_file_templates(self) -> None:
        """Verify automatic creation of HTML, CSS, JS, and Python files with proper syntax."""
        # 1. HTML
        html_file = os.path.join(self.test_dir, "index.html")
        res_html = self.tool.run(action="create_file", target=html_file)
        self.assertTrue(res_html.success)
        self.assertTrue(os.path.exists(html_file))
        content = Path(html_file).read_text(encoding="utf-8")
        self.assertIn("<!DOCTYPE html>", content)
        self.assertIn("<link rel=\"stylesheet\" href=\"style.css\">", content)

        # 2. CSS
        css_file = os.path.join(self.test_dir, "style.css")
        res_css = self.tool.run(action="create_file", target=css_file)
        self.assertTrue(res_css.success)
        self.assertTrue(os.path.exists(css_file))
        css_content = Path(css_file).read_text(encoding="utf-8")
        self.assertIn("box-sizing: border-box;", css_content)

        # 3. Python
        py_file = os.path.join(self.test_dir, "app.py")
        res_py = self.tool.run(action="create_file", target=py_file)
        self.assertTrue(res_py.success)
        self.assertTrue(os.path.exists(py_file))

    def test_scaffold_web_project(self) -> None:
        """Verify full web project scaffolding from scratch."""
        project_dir = os.path.join(self.test_dir, "portfolio_site")
        res = self.tool.run(
            action="scaffold_project",
            target=project_dir,
            project_type="web",
            project_name="My Portfolio",
        )
        self.assertTrue(res.success)
        self.assertTrue(os.path.exists(os.path.join(project_dir, "index.html")))
        self.assertTrue(os.path.exists(os.path.join(project_dir, "style.css")))
        self.assertTrue(os.path.exists(os.path.join(project_dir, "app.js")))
        self.assertTrue(os.path.exists(os.path.join(project_dir, "README.md")))

    def test_check_syntax(self) -> None:
        """Verify syntax checking for valid and invalid code."""
        # Valid Python
        py_valid = os.path.join(self.test_dir, "valid.py")
        Path(py_valid).write_text("def hello(): return 42\n", encoding="utf-8")
        res_val = self.tool.run(action="check_syntax", target=py_valid)
        self.assertTrue(res_val.success)

        # Invalid Python
        py_invalid = os.path.join(self.test_dir, "invalid.py")
        Path(py_invalid).write_text("def broken(: print('oops')\n", encoding="utf-8")
        res_inval = self.tool.run(action="check_syntax", target=py_invalid)
        self.assertFalse(res_inval.success)
        self.assertIn("SyntaxError", res_inval.message)

    def test_diagnose_error(self) -> None:
        """Verify error analysis and remediation suggestions."""
        traceback_str = (
            "Traceback (most recent call last):\n"
            "  File 'main.py', line 2, in <module>\n"
            "    import flask\n"
            "ModuleNotFoundError: No module named 'flask'\n"
        )
        res = self.tool.run(action="diagnose_error", error_text=traceback_str)
        self.assertTrue(res.success)
        self.assertIn("pip install flask", res.message)

    def test_find_vscode_executable(self) -> None:
        """Verify VS Code finder resolves code binary or command."""
        exe = find_vscode_executable()
        self.assertIsNotNone(exe)


class TestDevAgentIntentParsing(unittest.TestCase):
    """Verifies intent recognition for coding, scaffolding, and VS Code commands."""

    def test_open_vscode_intent(self) -> None:
        """Verify opening specific folder in VS Code."""
        i1 = parse_dev_agent_intent("open folder my-portfolio in vs code")
        self.assertIsNotNone(i1)
        self.assertEqual(i1["action"], "open_vscode")
        self.assertEqual(i1["target"], "my-portfolio")

        i2 = parse_dev_agent_intent("open vs code in D:\\engineers\\Project-A")
        self.assertIsNotNone(i2)
        self.assertEqual(i2["action"], "open_vscode")
        self.assertEqual(i2["target"], "D:\\engineers\\Project-A")

    def test_scaffold_project_intent(self) -> None:
        """Verify project generation intent."""
        i_scaffold = parse_dev_agent_intent("create a website for me in portfolio-app")
        self.assertIsNotNone(i_scaffold)
        self.assertEqual(i_scaffold["action"], "scaffold_project")
        self.assertEqual(i_scaffold["target"], "portfolio-app")
        self.assertEqual(i_scaffold["project_type"], "web")

    def test_create_file_intent(self) -> None:
        """Verify file creation intent."""
        i_file = parse_dev_agent_intent("create file index.html in my-web-app")
        self.assertIsNotNone(i_file)
        self.assertEqual(i_file["action"], "create_file")
        self.assertIn("index.html", i_file["target"])

    def test_meta_capabilities(self) -> None:
        """Verify questions about coding agent return capabilities."""
        i_cap = parse_dev_agent_intent("can you completely code for me")
        self.assertIsNotNone(i_cap)
        self.assertEqual(i_cap["action"], "capabilities")
        self.assertIn("Visual Studio Code", i_cap["message"])


if __name__ == "__main__":
    unittest.main()
