"""
Unit tests for Jarvis Code Tools (RunPythonTool, RunCommandTool, EditFileTool, ReadWorkspaceFileTool).
Covers Day 5 & Day 8 requirements:
  - Safe Python execution in workspace/
  - Precise schema instructions (prints results, avoids interactive input)
  - Concise error reporting with exact line numbers
  - ReadWorkspaceFileTool for reading back files created in workspace/
  - 5-program acceptance demo suite

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
    ReadWorkspaceFileTool,
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
    for f in [
        "factorial_test.py",
        "test_hello.py",
        "truncate_test.py",
        "infinite_loop.py",
        "reg_test.py",
        "runtime_err_test.py",
        "syntax_err_test.py",
        "demo_primes.py",
        "demo_table.py",
        "demo_strings.py",
        "demo_filewriter.py",
        "output_data.txt",
        "sample_read.txt",
    ]:
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


def test_run_python_schema_improved():
    """Day 8: Verifies precise get_schema() description advising print() and avoiding input()."""
    tool = RunPythonTool()
    schema = tool.get_schema()
    assert schema["name"] == "run_python"
    desc = schema["description"].lower()
    code_desc = schema["parameters"]["properties"]["code"]["description"].lower()

    # Must tell the model to print result
    assert "print" in desc or "print" in code_desc
    # Must advise model to avoid input()
    assert "input" in desc or "input" in code_desc
    assert "code" in schema["parameters"]["required"]


def test_error_formatting_includes_line_number_runtime():
    """Day 8: Verifies that runtime errors return concise messages with the exact line number."""
    tool = RunPythonTool()
    code = (
        "def compute():\n"
        "    a = 10\n"
        "    b = 0\n"
        "    return a / b\n"
        "compute()\n"
    )
    res = tool.run(code=code, filename="runtime_err_test.py")
    assert res.success is False
    # Error message must specify line number
    assert "line 4" in res.message.lower()
    assert "zerodivisionerror" in res.message.lower()
    assert res.data["line_number"] == 4


def test_error_formatting_includes_line_number_syntax():
    """Day 8: Verifies that syntax errors return concise messages with the line number."""
    tool = RunPythonTool()
    code = (
        "x = 5\n"
        "if x == 5\n"
        "    print('syntax error')\n"
    )
    res = tool.run(code=code, filename="syntax_err_test.py")
    assert res.success is False
    assert "line 2" in res.message.lower()
    assert "syntax" in res.message.lower()


def test_input_blocked_with_line_number_and_advice():
    """Day 8: Verifies that interactive input() is blocked and advises the model to avoid input()."""
    tool = RunPythonTool()
    code = (
        "user_name = input('Enter name: ')\n"
        "print('Hello ' + user_name)\n"
    )
    res = tool.run(code=code)
    assert res.success is False
    assert "line 1" in res.message.lower()
    assert "input()" in res.message
    assert "avoid input()" in res.message.lower()


def test_read_workspace_file_tool_success():
    """Day 8: Verifies ReadWorkspaceFileTool successfully reads back files created in workspace/."""
    ws = os.path.realpath("workspace")
    sample_file = os.path.join(ws, "sample_read.txt")
    with open(sample_file, "w", encoding="utf-8") as f:
        f.write("Line 1: Model generated result\nLine 2: 42\n")

    reader = ReadWorkspaceFileTool()
    res = reader.run(filename="sample_read.txt")

    assert res.success is True
    assert "Model generated result" in res.message
    assert "42" in res.data["content"]
    assert res.data["filename"] == "sample_read.txt"


def test_read_workspace_file_tool_errors():
    """Day 8: Verifies ReadWorkspaceFileTool error handling (missing file, traversal escape, empty name)."""
    reader = ReadWorkspaceFileTool()

    # Empty filename
    res_empty = reader.run(filename="")
    assert res_empty.success is False
    assert "non-empty" in res_empty.message.lower()

    # Missing file
    res_missing = reader.run(filename="does_not_exist_99.txt")
    assert res_missing.success is False
    assert "not found" in res_missing.message.lower()

    # Traversal escape
    res_escape = reader.run(filename="../secret_outside.txt")
    assert res_escape.success is False
    assert "permission denied" in res_escape.message.lower() or "traversal" in res_escape.message.lower()


def test_registry_integration_read_workspace_file():
    """Day 8: Verifies read_workspace_file is in registry and callable via execute_tool."""
    assert "read_workspace_file" in TOOL_REGISTRY
    ws = os.path.realpath("workspace")
    with open(os.path.join(ws, "reg_test.txt"), "w", encoding="utf-8") as f:
        f.write("Registry integration verified")

    res = execute_tool("read_workspace_file", {"filename": "reg_test.txt"})
    assert res.success is True
    assert "Registry integration verified" in res.message

    # Clean up
    try:
        os.remove(os.path.join(ws, "reg_test.txt"))
    except OSError:
        pass


def test_day8_acceptance_five_programs_and_reader():
    """Day 8 Acceptance test: Five different programs run successfully through RunPythonTool,

    and created output is readable via ReadWorkspaceFileTool.
    """
    runner = RunPythonTool()
    reader = ReadWorkspaceFileTool()

    # 1. Factorial program
    p1 = """
def fact(n):
    return 1 if n <= 1 else n * fact(n - 1)
print(f"5! = {fact(5)}")
"""
    r1 = runner.run(code=p1, filename="demo_fact.py")
    assert r1.success is True
    assert "5! = 120" in r1.data["stdout"]

    # 2. Prime numbers finder
    p2 = """
def primes_up_to(limit):
    primes = []
    for num in range(2, limit + 1):
        if all(num % i != 0 for i in range(2, int(num ** 0.5) + 1)):
            primes.append(num)
    return primes
print(f"Primes: {primes_up_to(20)}")
"""
    r2 = runner.run(code=p2, filename="demo_primes.py")
    assert r2.success is True
    assert "[2, 3, 5, 7, 11, 13, 17, 19]" in r2.data["stdout"]

    # 3. Multiplication table loop
    p3 = """
table = [f"7 x {i} = {7 * i}" for i in range(1, 6)]
print("\\n".join(table))
"""
    r3 = runner.run(code=p3, filename="demo_table.py")
    assert r3.success is True
    assert "7 x 1 = 7" in r3.data["stdout"]
    assert "7 x 5 = 35" in r3.data["stdout"]

    # 4. String manipulation and statistics
    p4 = """
text = "Jarvis Autonomous Assistant"
words = text.split()
print(f"Word count: {len(words)}, Upper: {text.upper()}")
"""
    r4 = runner.run(code=p4, filename="demo_strings.py")
    assert r4.success is True
    assert "Word count: 3" in r4.data["stdout"]
    assert "JARVIS AUTONOMOUS ASSISTANT" in r4.data["stdout"]

    # 5. Program writing a file to workspace/ and reading it back with ReadWorkspaceFileTool
    p5 = """
with open("output_data.txt", "w", encoding="utf-8") as f:
    f.write("Calculation Result: 1024")
print("File written successfully.")
"""
    r5 = runner.run(code=p5, filename="demo_filewriter.py")
    assert r5.success is True
    assert "File written successfully." in r5.data["stdout"]

    # Read back the created file using ReadWorkspaceFileTool
    read_res = reader.run(filename="output_data.txt")
    assert read_res.success is True
    assert "Calculation Result: 1024" in read_res.data["content"]


def test_empty_code_rejected():
    """Verifies that empty code is rejected with an informative error."""
    tool = RunPythonTool()
    res = tool.run(code="")
    assert res.success is False
    assert "non-empty" in res.message.lower()
