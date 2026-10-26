"""Tests for JARVIS Autonomous Developer Agent and Self-Repair Loop.

Module: tests.test_autonomous_dev
Verifies:
- Autonomous self-correction loop: run script -> capture traceback -> diagnose -> patch -> verify.
- LLM code authoring and custom file creation with purpose.
- Bespoke project scaffolding with user descriptions.
"""

from __future__ import annotations

import os
from pathlib import Path
import sys
from typing import Any

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools.dev_tools import DevAgentTool, _generate_code_with_llm
from tools.base import ToolResult


def test_dev_agent_create_file_with_purpose(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify DevAgentTool creates file with custom LLM content when purpose is provided."""
    tool = DevAgentTool()
    file_path = str(tmp_path / "calculator.py")

    # When LLM is mocked
    monkeypatch.setattr(
        "tools.dev_tools._generate_code_with_llm",
        lambda filename, purpose: "def add(a: int, b: int) -> int:\n    \"\"\"Add two integers.\"\"\"\n    return a + b\n",
    )

    result = tool.run(
        action="create_file",
        target=file_path,
        purpose="Create an integer addition module",
    )
    assert result.success is True
    assert os.path.exists(file_path)
    content = Path(file_path).read_text(encoding="utf-8")
    assert "def add(a: int, b: int)" in content


def test_dev_agent_scaffold_project_with_description(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify scaffolding a project with custom description generates tailored files."""
    tool = DevAgentTool()
    proj_dir = str(tmp_path / "analytics_app")

    monkeypatch.setattr(
        "tools.dev_tools._generate_code_with_llm",
        lambda filename, purpose: f"# Tailored {filename} for {purpose}\n",
    )

    result = tool.run(
        action="scaffold_project",
        target=proj_dir,
        project_type="web",
        project_name="Analytics Dashboard",
        description="A dark-mode analytics portal with live websocket graphs",
    )
    assert result.success is True
    assert os.path.exists(os.path.join(proj_dir, "index.html"))
    assert os.path.exists(os.path.join(proj_dir, "style.css"))
    assert os.path.exists(os.path.join(proj_dir, "app.js"))


def test_run_and_repair_clean_script(tmp_path: Path) -> None:
    """Verify run_and_repair succeeds immediately when script is already error-free."""
    tool = DevAgentTool()
    script_path = str(tmp_path / "clean_script.py")
    Path(script_path).write_text("print('Hello from clean script')\n", encoding="utf-8")

    result = tool.run(
        action="run_and_repair",
        target=script_path,
        max_attempts=3,
    )
    assert result.success is True
    assert "0 errors on first attempt" in result.message
    assert result.data["attempts"] == 1


def test_run_and_repair_auto_heals_missing_module(tmp_path: Path) -> None:
    """Verify run_and_repair detects ModuleNotFoundError, patches the code, and succeeds."""
    tool = DevAgentTool()
    script_path = str(tmp_path / "broken_module.py")

    # Script imports a non-existent package and prints a value
    broken_code = (
        "import nonexistent_package_12345\n"
        "print('Execution completed with patched package')\n"
    )
    Path(script_path).write_text(broken_code, encoding="utf-8")

    result = tool.run(
        action="run_and_repair",
        target=script_path,
        max_attempts=3,
    )
    assert result.success is True
    assert result.data["attempts"] >= 2
    assert any("Injected mock fallback" in f for f in result.data["fixes_applied"])
    # Verify file was healed
    healed_code = Path(script_path).read_text(encoding="utf-8")
    assert "sys.modules['nonexistent_package_12345']" in healed_code


def test_run_and_repair_auto_heals_zero_division(tmp_path: Path) -> None:
    """Verify run_and_repair heals ZeroDivisionError."""
    tool = DevAgentTool()
    script_path = str(tmp_path / "broken_math.py")

    broken_code = (
        "x = 100 / 0\n"
        "print(f'Result: {x}')\n"
    )
    Path(script_path).write_text(broken_code, encoding="utf-8")

    result = tool.run(
        action="run_and_repair",
        target=script_path,
        max_attempts=3,
    )
    assert result.success is True
    assert any("ZeroDivisionError" in f for f in result.data["fixes_applied"])


def test_run_and_repair_persistent_error_reports_failure(tmp_path: Path) -> None:
    """Verify run_and_repair gracefully handles persistent unfixable errors without crashing."""
    tool = DevAgentTool()
    script_path = str(tmp_path / "unfixable.py")

    # Deliberately raise a custom exception that is not in simple heuristics
    Path(script_path).write_text("raise RuntimeError('Fatal custom hardware fault')\n", encoding="utf-8")

    result = tool.run(
        action="run_and_repair",
        target=script_path,
        max_attempts=2,
    )
    assert result.success is False
    assert "Autonomous self-repair attempted 2 times" in result.message
    assert "Fatal custom hardware fault" in result.data["last_error"]
