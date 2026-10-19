"""
Unit and integration tests for Jarvis system and file tools.
Author: Abhijit (System & Automation Engineer)
"""

import os
import shutil
from typing import Any, Dict, Generator
import pytest

from tools.base import BaseTool, ToolResult
from tools.safety import is_path_safe
from tools.file_tools import ReadFileTool, WriteFileTool
from tools.registry import (
    TOOL_REGISTRY,
    execute_tool,
    get_registered_tools,
    get_tools_schema,
)


@pytest.fixture(autouse=True)
def setup_workspace_sandbox() -> Generator[str, None, None]:
    """Ensures a clean workspace sandbox exists before tests and cleans up test artifacts."""
    workspace_dir = os.path.realpath("workspace")
    os.makedirs(workspace_dir, exist_ok=True)
    test_files_created = []

    yield workspace_dir

    # Cleanup any temporary files created in workspace
    for item in os.listdir(workspace_dir):
        if item.startswith("test_") or item.startswith("temp_"):
            target = os.path.join(workspace_dir, item)
            try:
                if os.path.isfile(target):
                    os.remove(target)
                elif os.path.isdir(target):
                    shutil.rmtree(target)
            except OSError:
                pass


@pytest.fixture
def temp_folder_sandbox() -> Generator[str, None, None]:
    """Provides a temporary sandbox folder starting with temp_."""
    temp_dir = os.path.realpath("temp_pytest_sandbox")
    os.makedirs(temp_dir, exist_ok=True)

    yield temp_dir

    if os.path.exists(temp_dir):
        try:
            shutil.rmtree(temp_dir)
        except OSError:
            pass


# ---------------------------------------------------------------------------
# 1. Safety Guard Tests (tools/safety.py)
# ---------------------------------------------------------------------------

def test_safety_blocks_windows_system_paths() -> None:
    """Verifies C:\\Windows and C:\\Program Files paths are rejected by is_path_safe."""
    assert not is_path_safe(r"C:\Windows\System32\test.txt")
    assert not is_path_safe(r"C:\Windows\notepad.exe")
    assert not is_path_safe(r"C:\Program Files\test.txt")
    assert not is_path_safe(r"C:\Program Files (x86)\test.txt")
    assert not is_path_safe(r"C:\ProgramData\test.txt")


def test_safety_blocks_dot_dot_escape() -> None:
    """Verifies directory traversal '..' attacks are detected and blocked."""
    assert not is_path_safe("workspace/../test.txt")
    assert not is_path_safe("workspace/../../test.txt")
    assert not is_path_safe("workspace/../../Windows/System32/cmd.exe")
    assert not is_path_safe("workspace/sub/../../escaped.txt")
    assert not is_path_safe("temp_folder/../secret.txt")


def test_safety_allows_workspace_and_temp_folders() -> None:
    """Verifies paths inside workspace/ and folders starting with temp_ are allowed."""
    assert is_path_safe("workspace/test.txt")
    assert is_path_safe("workspace/nested/deep/file.json")
    assert is_path_safe(os.path.realpath("workspace/sample.txt"))
    assert is_path_safe("temp_test/test.txt")
    assert is_path_safe("temp_data/records.csv")
    assert is_path_safe("temp_12345/sub/log.txt")


def test_safety_blocks_arbitrary_outside_paths() -> None:
    """Verifies arbitrary paths outside workspace and temp_ folders are blocked."""
    assert not is_path_safe("C:\\random_directory\\file.txt")
    assert not is_path_safe("D:\\other_project\\file.txt")
    assert not is_path_safe("")
    assert not is_path_safe("   ")
    assert not is_path_safe(None)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# 2. WriteFileTool Security & Permission Denied Tests
# ---------------------------------------------------------------------------

def test_write_to_windows_system32_returns_permission_denied() -> None:
    """Writing to C:\\Windows\\System32\\test.txt returns ToolResult(success=False) with 'Permission Denied'."""
    tool = WriteFileTool()
    forbidden_path = r"C:\Windows\System32\test.txt"

    result = tool.run(file_path=forbidden_path, content="unauthorized content")
    assert isinstance(result, ToolResult)
    assert result.success is False
    assert result.data is None
    assert "Permission Denied" in result.message


def test_write_to_windows_system32_via_execute_tool_returns_permission_denied() -> None:
    """Dispatching write_file to C:\\Windows\\System32\\test.txt via registry returns 'Permission Denied'."""
    forbidden_path = r"C:\Windows\System32\test.txt"

    result = execute_tool("write_file", {"file_path": forbidden_path, "content": "malicious"})
    assert isinstance(result, ToolResult)
    assert result.success is False
    assert result.data is None
    assert "Permission Denied" in result.message


def test_write_to_program_files_returns_permission_denied() -> None:
    """Writing to C:\\Program Files returns Permission Denied."""
    tool = WriteFileTool()
    result = tool.run(file_path=r"C:\Program Files\test_payload.txt", content="payload")
    assert result.success is False
    assert "Permission Denied" in result.message


def test_write_dot_dot_escape_returns_permission_denied() -> None:
    """Attempting to write outside workspace via '..' traversal returns 'Permission Denied'."""
    tool = WriteFileTool()
    escape_path = "workspace/../test_escape_write.txt"

    result = tool.run(file_path=escape_path, content="escaped write")
    assert result.success is False
    assert "Permission Denied" in result.message


# ---------------------------------------------------------------------------
# 3. ReadFileTool Security & Traversal Tests
# ---------------------------------------------------------------------------

def test_read_from_windows_system32_returns_permission_denied() -> None:
    """Reading from C:\\Windows\\System32 returns ToolResult(success=False) with 'Permission Denied'."""
    tool = ReadFileTool()
    forbidden_path = r"C:\Windows\System32\drivers\etc\hosts"

    result = tool.run(file_path=forbidden_path)
    assert isinstance(result, ToolResult)
    assert result.success is False
    assert result.data is None
    assert "Permission Denied" in result.message


def test_read_dot_dot_escape_returns_permission_denied() -> None:
    """Attempting to read outside workspace via '..' traversal returns 'Permission Denied'."""
    tool = ReadFileTool()
    escape_path = "workspace/../AGENTS.md"

    result = tool.run(file_path=escape_path)
    assert result.success is False
    assert "Permission Denied" in result.message


# ---------------------------------------------------------------------------
# 4. Writing & Reading Inside workspace/ Succeeds
# ---------------------------------------------------------------------------

def test_writing_and_reading_inside_workspace_succeeds() -> None:
    """Writing and reading a text file inside workspace/ succeeds with exact content match."""
    write_tool = WriteFileTool()
    read_tool = ReadFileTool()

    target_file = "workspace/test_hello.txt"
    test_content = "Hello Project Jarvis! Safe file operations verified."

    # 1. Write file
    write_result = write_tool.run(file_path=target_file, content=test_content)
    assert isinstance(write_result, ToolResult)
    assert write_result.success is True
    assert write_result.data is not None
    assert write_result.data.get("bytes_written") == len(test_content.encode("utf-8"))

    # 2. Read file
    read_result = read_tool.run(file_path=target_file)
    assert isinstance(read_result, ToolResult)
    assert read_result.success is True
    assert read_result.data == test_content
    assert read_result.data.get("content") == test_content
    assert test_content in read_result.to_llm_string()


def test_writing_and_reading_inside_workspace_via_registry() -> None:
    """Writing and reading inside workspace/ using execute_tool succeeds."""
    target_file = "workspace/test_registry_io.txt"
    test_content = "Registry dispatch IO verification"

    write_res = execute_tool("write_file", {"file_path": target_file, "content": test_content})
    assert write_res.success is True

    read_res = execute_tool("read_file", {"file_path": target_file})
    assert read_res.success is True
    assert read_res.data == test_content


def test_write_file_overwrite_protection() -> None:
    """WriteFileTool must not overwrite existing file unless overwrite=True."""
    write_tool = WriteFileTool()
    target_file = "workspace/test_overwrite.txt"

    # Initial write
    res1 = write_tool.run(file_path=target_file, content="Original content")
    assert res1.success is True

    # Attempt overwrite without overwrite=True
    res2 = write_tool.run(file_path=target_file, content="New content", overwrite=False)
    assert res2.success is False
    assert "already exists" in res2.message

    # Verify content was NOT overwritten
    read_tool = ReadFileTool()
    read_res1 = read_tool.run(file_path=target_file)
    assert read_res1.data == "Original content"

    # Overwrite with overwrite=True
    res3 = write_tool.run(file_path=target_file, content="Overwritten content", overwrite=True)
    assert res3.success is True

    # Verify content was updated
    read_res2 = read_tool.run(file_path=target_file)
    assert read_res2.data == "Overwritten content"


def test_writing_nested_directories_in_workspace_succeeds() -> None:
    """Writing to a nested subdirectory inside workspace/ creates directories and succeeds."""
    write_tool = WriteFileTool()
    read_tool = ReadFileTool()

    nested_file = "workspace/test_nested_dir/sub/sample.txt"
    content = "Deeply nested file write"

    write_res = write_tool.run(file_path=nested_file, content=content)
    assert write_res.success is True

    read_res = read_tool.run(file_path=nested_file)
    assert read_res.success is True
    assert read_res.data == content


# ---------------------------------------------------------------------------
# 5. Writing and Reading Inside temp_ Folder Succeeds
# ---------------------------------------------------------------------------

def test_writing_and_reading_inside_temp_folder(temp_folder_sandbox: str) -> None:
    """Writing and reading inside a folder starting with temp_ succeeds."""
    write_tool = WriteFileTool()
    read_tool = ReadFileTool()

    target_file = os.path.join(temp_folder_sandbox, "temp_data.txt")
    content = "Temporary data buffer"

    write_res = write_tool.run(file_path=target_file, content=content)
    assert write_res.success is True

    read_res = read_tool.run(file_path=target_file)
    assert read_res.success is True
    assert read_res.data == content


# ---------------------------------------------------------------------------
# 6. Tool Registry & Schema Compliance
# ---------------------------------------------------------------------------

def test_file_tools_registered_in_registry() -> None:
    """Verifies ReadFileTool and WriteFileTool are registered and accessible by name and class name."""
    assert "read_file" in TOOL_REGISTRY
    assert "write_file" in TOOL_REGISTRY
    assert "ReadFileTool" in TOOL_REGISTRY
    assert "WriteFileTool" in TOOL_REGISTRY
    assert isinstance(TOOL_REGISTRY["read_file"], ReadFileTool)
    assert isinstance(TOOL_REGISTRY["write_file"], WriteFileTool)


def test_registered_tools_list_contains_file_tools() -> None:
    """Verifies get_registered_tools includes ReadFileTool and WriteFileTool."""
    registered = get_registered_tools()
    tool_names = [tool.name for tool in registered]
    assert "read_file" in tool_names
    assert "write_file" in tool_names


def test_schemas_are_valid() -> None:
    """Verifies get_schema() for each tool generates valid JSON schema definitions."""
    read_schema = ReadFileTool().get_schema()
    assert isinstance(read_schema, dict)
    assert read_schema["name"] == "read_file"
    assert "description" in read_schema
    assert read_schema["parameters"]["type"] == "object"
    assert "file_path" in read_schema["parameters"]["properties"]
    assert "file_path" in read_schema["parameters"]["required"]

    write_schema = WriteFileTool().get_schema()
    assert isinstance(write_schema, dict)
    assert write_schema["name"] == "write_file"
    assert "description" in write_schema
    assert write_schema["parameters"]["type"] == "object"
    assert "file_path" in write_schema["parameters"]["properties"]
    assert "content" in write_schema["parameters"]["properties"]
    assert "overwrite" in write_schema["parameters"]["properties"]
    assert "file_path" in write_schema["parameters"]["required"]
    assert "content" in write_schema["parameters"]["required"]

    all_schemas = get_tools_schema()
    schema_names = [s["name"] for s in all_schemas]
    assert "read_file" in schema_names
    assert "write_file" in schema_names
    assert "get_system_stats" in schema_names


# ---------------------------------------------------------------------------
# 7. Existing Tools Unchanged & Contract Integrity
# ---------------------------------------------------------------------------

def test_existing_tools_preserved() -> None:
    """Verifies existing tools are preserved with exact names and interfaces."""
    expected_tools = [
        "get_system_stats",
        "open_app",
        "list_directory",
        "open_website",
        "search_web",
        "read_file",
        "write_file",
    ]
    for name in expected_tools:
        assert name in TOOL_REGISTRY, f"Tool '{name}' must exist in TOOL_REGISTRY"
        tool = TOOL_REGISTRY[name]
        assert isinstance(tool, BaseTool)
        assert hasattr(tool, "run")
        assert hasattr(tool, "get_schema")
