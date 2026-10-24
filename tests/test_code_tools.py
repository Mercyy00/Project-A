"""
Unit tests for Jarvis Code Tools (RunPythonTool, RunCommandTool, EditFileTool).
Covers Day 5 requirements: code execution in workspace, safety blocks, timeouts, and validations.
Author: Abhijit (System & Automation Engineer)
"""

import os
import shutil
import pytest
from tools.base import ToolResult
from tools.code_tools import (
    RunPythonTool,
    RunCommandTool,
    EditFileTool,
    validate_python_code_safety,
)
from tools.registry import TOOL_REGISTRY, execute_tool, get_registered_tools


@pytest.fixture(autouse=True)
def setup_workspace_dir():
    """Ensures workspace directory exists and cleans up temporary test scripts."""
    ws = os.path.realpath("workspace")
    os.makedirs(ws, exist_ok=True)
    yield ws
    # Clean up test files created during tests
    for f in ["factorial_test.py", "test_hello.py", "truncate_test.py", "infinite_loop.py", "reg_test.py"]:
        p = os.path.join(ws, f)
        if os.path.exists(p):
            try:
                os.remove(p)
            except OSError:
                pass


def test_run_python_factorial_acceptance():
    """Acceptance test: 'Write a factorial program and run it' prints 120 for 5!."""
    tool = RunPythonTool()
    code = """
def factorial(n):
    return 1 if n <= 1 else n * factorial(n - 1)

print(factorial(5))
"""
    res = tool.run(code=code, filename="factorial_test.py")
    assert isinstance(res, ToolResult)
    assert res.success is True
    assert "120" in res.data["stdout"]
    assert res.data["exit_code"] == 0
    assert os.path.exists(os.path.join("workspace", "factorial_test.py"))


def test_run_python_custom_filename():
    """Verifies that code is saved with the specified filename inside workspace/."""
    tool = RunPythonTool()
    code = "print('Hello from Jarvis')"
    res = tool.run(code=code, filename="test_hello.py")
    assert res.success is True
    assert "Hello from Jarvis" in res.data["stdout"]
    assert os.path.exists(os.path.join("workspace", "test_hello.py"))


def test_filename_path_separator_validation():
    """Verifies that filename cannot contain path separators or relative escape sequences."""
    tool = RunPythonTool()

    # Forward slash
    res1 = tool.run(code="print(1)", filename="nested/script.py")
    assert res1.success is False
    assert "path separator" in res1.message.lower()

    # Backslash
    res2 = tool.run(code="print(1)", filename="nested\\script.py")
    assert res2.success is False
    assert "path separator" in res2.message.lower()

    # Parent directory escape
    res3 = tool.run(code="print(1)", filename="../script.py")
    assert res3.success is False
    assert "path separator" in res3.message.lower()


def test_run_python_infinite_loop_timeout():
    """Verifies that an infinite loop is terminated when timeout expires."""
    tool = RunPythonTool()
    code = "import time\nwhile True:\n    time.sleep(0.05)"
    # Using a 2-second timeout for fast and reliable test execution
    res = tool.run(code=code, filename="infinite_loop.py", timeout=2)
    assert res.success is False
    assert "timed out" in res.message.lower()
    assert res.data["timed_out"] is True
    assert res.data["exit_code"] == -1


def test_blocked_call_shutil_rmtree():
    """Verifies that shutil.rmtree is blocked with a clear reason."""
    tool = RunPythonTool()
    code = "import shutil\nshutil.rmtree('workspace/data')"
    res = tool.run(code=code)
    assert res.success is False
    assert "shutil.rmtree" in res.message
    assert "destructive" in res.message.lower()


def test_blocked_call_os_system():
    """Verifies that os.system is blocked with a clear reason."""
    tool = RunPythonTool()
    code = "import os\nos.system('dir')"
    res = tool.run(code=code)
    assert res.success is False
    assert "os.system" in res.message


def test_blocked_call_subprocess_shell_true():
    """Verifies that subprocess with shell=True is blocked with a clear reason."""
    tool = RunPythonTool()
    code = "import subprocess\nsubprocess.run(['dir'], shell=True)"
    res = tool.run(code=code)
    assert res.success is False
    assert "shell=True" in res.message


def test_blocked_call_os_remove_outside_workspace():
    """Verifies that os.remove on paths outside workspace is blocked."""
    tool = RunPythonTool()
    code = "import os\nos.remove('C:\\\\Windows\\\\System32\\\\notepad.exe')"
    res = tool.run(code=code)
    assert res.success is False
    assert "outside workspace" in res.message.lower() or "os.remove" in res.message.lower()


def test_blocked_call_os_remove_parent_escape():
    """Verifies that os.remove with '..' relative traversal outside workspace is blocked."""
    tool = RunPythonTool()
    code = "import os\nos.remove('../outside_secret.txt')"
    res = tool.run(code=code)
    assert res.success is False
    assert "outside workspace" in res.message.lower() or "os.remove" in res.message.lower()


def test_output_truncation():
    """Verifies that output exceeding 4000 characters is truncated."""
    tool = RunPythonTool()
    code = "print('Z' * 5000)"
    res = tool.run(code=code, filename="truncate_test.py")
    assert res.success is True
    assert len(res.data["stdout"]) <= 4100
    assert "truncated" in res.data["stdout"].lower()


def test_run_python_schema():
    """Verifies the JSON schema for RunPythonTool."""
    tool = RunPythonTool()
    schema = tool.get_schema()
    assert schema["name"] == "run_python"
    assert "code" in schema["parameters"]["properties"]
    assert "filename" in schema["parameters"]["properties"]
    assert "code" in schema["parameters"]["required"]


def test_registry_integration_run_python():
    """Verifies that run_python is correctly registered and callable via execute_tool."""
    assert "run_python" in TOOL_REGISTRY
    res = execute_tool("run_python", {"code": "print('registry_success')", "filename": "reg_test.py"})
    assert res.success is True
    assert "registry_success" in res.data["stdout"]


def test_empty_code_rejected():
    """Verifies that empty code is rejected with an informative error."""
    tool = RunPythonTool()
    res = tool.run(code="")
    assert res.success is False
    assert "non-empty" in res.message.lower()
