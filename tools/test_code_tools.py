"""
Unit tests for Jarvis code tools, safety updates, and web search tool.
Author: Abhijit (System & Automation Engineer)
"""

import os
import shutil
import pytest
from tools.base import ToolResult
from tools.safety import (
    is_path_safe,
    get_designated_project_dir,
    set_designated_project_dir,
)
from tools.code_tools import (
    RunCommandTool,
    EditFileTool,
    RunPythonTool,
    ReadWorkspaceFileTool,
)
from tools.system_tools import SearchWebTool
from tools.registry import TOOL_REGISTRY, execute_tool, get_registered_tools


@pytest.fixture(autouse=True)
def setup_test_workspace():
    """Sets up a clean workspace and projects test directory."""
    proj_dir = os.path.realpath("workspace/projects/test_proj")
    os.makedirs(proj_dir, exist_ok=True)
    yield proj_dir
    if os.path.exists("workspace/projects/test_proj"):
        try:
            shutil.rmtree("workspace/projects/test_proj")
        except OSError:
            pass


def test_safety_allows_workspace_projects_and_codebase():
    """Verifies is_path_safe allows workspace/projects, designated project directory, and codebase files."""
    assert is_path_safe("workspace/projects/test_proj/app.py")
    assert is_path_safe("workspace/projects/my-web/index.html")
    assert is_path_safe("tools/safety.py")
    assert is_path_safe("tools/code_tools.py")

    # Designated project directory
    proj_root = get_designated_project_dir()
    assert is_path_safe(os.path.join(proj_root, "tools", "registry.py"))

    # Destructive Windows system directories remain blocked
    assert not is_path_safe(r"C:\Windows\System32\cmd.exe")
    assert not is_path_safe(r"C:\Program Files\Common Files")


def test_registry_contains_new_tools():
    """Verifies run_command, edit_file, run_python, and read_workspace_file are in TOOL_REGISTRY."""
    assert "run_command" in TOOL_REGISTRY
    assert "edit_file" in TOOL_REGISTRY
    assert "run_python" in TOOL_REGISTRY
    assert "read_workspace_file" in TOOL_REGISTRY

    registered_names = [t.name for t in get_registered_tools()]
    assert "run_command" in registered_names
    assert "edit_file" in registered_names
    assert "run_python" in registered_names
    assert "read_workspace_file" in registered_names


def test_run_command_tool_success():
    """Verifies RunCommandTool successfully executes a command and captures stdout."""
    tool = RunCommandTool()
    res = tool.run(command="python -c \"print('Hello from Jarvis')\"")
    assert isinstance(res, ToolResult)
    assert res.success is True
    assert "Hello from Jarvis" in res.data["stdout"]
    assert res.data["exit_code"] == 0


def test_run_command_tool_failure():
    """Verifies RunCommandTool captures non-zero exit code and stderr."""
    tool = RunCommandTool()
    res = tool.run(command="python -c \"import non_existent_pkg_xyz\"")
    assert isinstance(res, ToolResult)
    assert res.success is False
    assert res.data["exit_code"] != 0
    assert "non_existent_pkg_xyz" in res.data["stderr"]


def test_run_command_blocks_destructive_commands():
    """Verifies RunCommandTool rejects destructive disk formatting or deletion commands."""
    tool = RunCommandTool()
    res = tool.run(command="format C: /fs:ntfs")
    assert res.success is False
    assert "destructive" in res.message.lower()


def test_edit_file_tool():
    """Verifies EditFileTool performs targeted search-and-replace."""
    test_file = "workspace/projects/test_proj/sample.txt"
    with open(test_file, "w", encoding="utf-8") as f:
        f.write("def add(a, b):\n    return a - b\n")

    tool = EditFileTool()

    # Successful replacement
    res = tool.run(
        file_path=test_file,
        target_text="return a - b",
        replacement_text="return a + b"
    )
    assert res.success is True
    assert res.data["occurrences_replaced"] == 1

    with open(test_file, "r", encoding="utf-8") as f:
        content = f.read()
    assert "return a + b" in content

    # Target text not found
    fail_res = tool.run(
        file_path=test_file,
        target_text="non_existent_string",
        replacement_text="foo"
    )
    assert fail_res.success is False
    assert "not found" in fail_res.message.lower()


def test_run_python_tool_inline():
    """Verifies RunPythonTool runs inline Python snippets."""
    tool = RunPythonTool()
    res = tool.run(code="print(2 + 2)")
    assert res.success is True
    assert "4" in res.data["stdout"]


def test_run_python_tool_file():
    """Verifies RunPythonTool executes a Python script file."""
    script_file = "workspace/projects/test_proj/script.py"
    with open(script_file, "w", encoding="utf-8") as f:
        f.write("import sys; print(f'Args: {sys.argv[1:]}')")

    tool = RunPythonTool()
    res = tool.run(file_path=script_file, args=["alpha", "beta"])
    assert res.success is True
    assert "['alpha', 'beta']" in res.data["stdout"]


def test_read_workspace_file_tool():
    """Verifies ReadWorkspaceFileTool reads files inside workspace."""
    tool = ReadWorkspaceFileTool()
    test_file = "workspace/projects/test_proj/reader_test.txt"
    with open(test_file, "w", encoding="utf-8") as f:
        f.write("Reader tool test content")

    res = tool.run(filename="projects/test_proj/reader_test.txt")
    assert res.success is True
    assert "Reader tool test content" in res.message


def test_search_web_tool():
    """Verifies SearchWebTool handles queries and schema correctly."""
    tool = SearchWebTool()
    schema = tool.get_schema()
    assert schema["name"] == "search_web"
    assert "query" in schema["parameters"]["properties"]

    # Query validation
    empty_res = tool.run(query="")
    assert empty_res.success is False

    # Execute a live search
    res = tool.run(query="Python programming language", max_results=3)
    assert isinstance(res, ToolResult)
    # Even if offline or network times out, it returns a structured ToolResult
    if res.success:
        assert isinstance(res.data, (str, dict))
        assert len(res.data) > 0
    else:
        assert "Search failed" in res.message


def test_execute_tool_dispatching():
    """Verifies execute_tool safely dispatches to the new tools."""
    res_cmd = execute_tool("run_command", {"command": "python -c \"print('dispatch_ok')\""})
    assert res_cmd.success is True
    assert "dispatch_ok" in res_cmd.data["stdout"]

    res_py = execute_tool("run_python", {"code": "print('python_dispatch_ok')", "filename": "disp.py"})
    assert res_py.success is True
    assert "python_dispatch_ok" in res_py.data["stdout"]
