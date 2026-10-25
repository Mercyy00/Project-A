"""
Autonomous Development and Code Verification Tools for JARVIS.

Ported from Mark LVI's dev_agent.py.
Provides tools to:
- Run automated pytest suites
- Inspect git status and diffs
- Perform syntax validation on Python files
- Safely install Python dependencies with PEP 508 injection defenses
"""

from __future__ import annotations

import os
import re
import sys
import subprocess
import py_compile
from pathlib import Path
from typing import Any, Dict, List, Optional

from tools.base import BaseTool, ToolResult

PEP508_PACKAGE_RE = re.compile(
    r"^[a-zA-Z0-9]([a-zA-Z0-9._-]*[a-zA-Z0-9])?(\[[a-zA-Z0-9._,-]+\])?([><=~!]=?[a-zA-Z0-9.*+!-]+)?$"
)


def is_package_name_valid(name: str) -> bool:
    """Validate package name against PEP 508 and reject flag injection attacks."""
    if not name or not isinstance(name, str):
        return False
    name = name.strip()
    if name.startswith("-") or any(char in name for char in (";", "&", "|", "`", "$", " ", "\n", "\r", "\t")):
        return False
    return bool(PEP508_PACKAGE_RE.match(name))


class DevAgentTool(BaseTool):
    """Autonomous software engineering and test runner."""
    name: str = "dev_agent"
    description: str = (
        "Autonomous development agent: executes pytest suites, checks git status/diff, "
        "validates Python file syntax, or safely installs packages."
    )

    def get_schema(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["run_tests", "git_status", "git_diff", "check_syntax", "install_package"],
                        "description": "Dev action to run."
                    },
                    "target": {
                        "type": "string",
                        "description": "Test path, file path, or package name depending on action."
                    }
                },
                "required": ["action"]
            }
        }

    def run(self, action: str, target: Optional[str] = None, **kwargs) -> ToolResult:
        act = action.lower().strip()
        try:
            if act == "run_tests":
                test_target = target or "tests"
                cmd = [sys.executable, "-m", "pytest", test_target, "-q"]
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                success = res.returncode == 0
                output = (res.stdout + "\n" + res.stderr).strip()
                return ToolResult(
                    success=success,
                    data={"exit_code": res.returncode, "output": output[:2000]},
                    message=f"Pytest completed (exit {res.returncode}):\n{output[-300:]}"
                )

            elif act == "git_status":
                res = subprocess.run(["git", "status", "--short"], capture_output=True, text=True, timeout=10)
                output = res.stdout.strip() or "Working tree clean."
                return ToolResult(
                    success=res.returncode == 0,
                    data={"status": output},
                    message=f"Git status:\n{output}"
                )

            elif act == "git_diff":
                res = subprocess.run(["git", "diff", "--stat"], capture_output=True, text=True, timeout=10)
                output = res.stdout.strip() or "No uncommitted diffs."
                return ToolResult(
                    success=res.returncode == 0,
                    data={"diff": output},
                    message=f"Git diff summary:\n{output}"
                )

            elif act == "check_syntax":
                if not target or not Path(target).exists():
                    return ToolResult(success=False, message=f"Target file not found: {target}")
                py_compile.compile(target, doraise=True)
                return ToolResult(
                    success=True,
                    data={"file": target},
                    message=f"Syntax check passed for {target}"
                )

            elif act == "install_package":
                if not target or not is_package_name_valid(target):
                    return ToolResult(
                        success=False,
                        message=f"Rejected: invalid or dangerous package specification '{target}'"
                    )
                cmd = [sys.executable, "-m", "pip", "install", target]
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
                return ToolResult(
                    success=res.returncode == 0,
                    data={"package": target, "exit_code": res.returncode},
                    message=f"Pip install {'succeeded' if res.returncode == 0 else 'failed'}: {res.stdout[-200:]}"
                )

            return ToolResult(success=False, message=f"Unsupported dev action: {action}")

        except subprocess.TimeoutExpired:
            return ToolResult(success=False, message=f"Action '{action}' timed out.")
        except Exception as exc:
            return ToolResult(success=False, message=f"Dev agent failed: {str(exc)}")
