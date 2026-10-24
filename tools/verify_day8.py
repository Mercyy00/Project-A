"""
Runnable verification script for Jarvis Day 8 (25 Oct):
  - RunPythonTool schema verification (prints result, avoids input())
  - Concise error reporting with exact line numbers (ZeroDivisionError, SyntaxError, input() call)
  - 5-program code demo suite (factorial, prime numbers, multiplication table, string processing, file writer)
  - ReadWorkspaceFileTool verifying read-back of created workspace files
  - ToolRegistry integration

Author: Abhijit (System & Automation Engineer)
"""

import os
import sys

# Ensure repository root is in python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.registry import TOOL_REGISTRY, execute_tool
from tools.code_tools import RunPythonTool, ReadWorkspaceFileTool


def run_verification() -> bool:
    print("=" * 70)
    print("JARVIS DAY 8 (25 OCT) VERIFICATION SUITE - ABHIJIT (TOOLS)")
    print("=" * 70)

    all_passed = True
    runner = RunPythonTool()
    reader = ReadWorkspaceFileTool()

    # 1. Schema check
    print("\n[1] Verifying RunPythonTool get_schema()...")
    schema = runner.get_schema()
    desc = schema["description"].lower()
    code_desc = schema["parameters"]["properties"]["code"]["description"].lower()
    has_print = "print" in desc or "print" in code_desc
    has_avoid_input = "input" in desc or "input" in code_desc

    if has_print and has_avoid_input:
        print("    PASS: Schema clearly specifies printing results and avoiding input().")
    else:
        print("    FAIL: Schema missing print or avoid-input instructions.")
        all_passed = False

    # 2. Line number in error messages
    print("\n[2] Verifying error reporting with exact line numbers...")
    # Runtime error
    runtime_code = "a = 10\nb = 0\nprint(a / b)\n"
    r_err = runner.run(code=runtime_code, filename="test_err_runtime.py")
    if not r_err.success and "line 3" in r_err.message.lower() and "zerodivisionerror" in r_err.message.lower():
        print(f"    PASS: Runtime error detected line number: '{r_err.message}'")
    else:
        print(f"    FAIL: Runtime error format unexpected: {r_err.message}")
        all_passed = False

    # Syntax error
    syntax_code = "def bad_syntax()\n    pass\n"
    r_syn = runner.run(code=syntax_code, filename="test_err_syntax.py")
    if not r_syn.success and "line 1" in r_syn.message.lower():
        print(f"    PASS: Syntax error detected line number: '{r_syn.message}'")
    else:
        print(f"    FAIL: Syntax error format unexpected: {r_syn.message}")
        all_passed = False

    # input() warning
    input_code = "val = input('Prompt: ')\nprint(val)\n"
    r_inp = runner.run(code=input_code)
    if not r_inp.success and "line 1" in r_inp.message.lower() and "input()" in r_inp.message:
        print(f"    PASS: input() blocked with line number & avoidance notice: '{r_inp.message}'")
    else:
        print(f"    FAIL: input() blocking unexpected: {r_inp.message}")
        all_passed = False

    # 3. 5-Program Acceptance Test
    print("\n[3] Running 5-program code demo suite...")

    programs = [
        (
            "Factorial (5!)",
            "demo_p1_factorial.py",
            "def fact(n):\n    return 1 if n <= 1 else n * fact(n - 1)\nprint(f'5! = {fact(5)}')\n",
            "5! = 120"
        ),
        (
            "Prime Numbers up to 25",
            "demo_p2_primes.py",
            "primes = [n for n in range(2, 26) if all(n % i != 0 for i in range(2, int(n**0.5) + 1))]\nprint(f'Primes: {primes}')\n",
            "[2, 3, 5, 7, 11, 13, 17, 19, 23]"
        ),
        (
            "Multiplication Table (8x)",
            "demo_p3_table.py",
            "for i in range(1, 6):\n    print(f'8 x {i} = {8 * i}')\n",
            "8 x 5 = 40"
        ),
        (
            "String Processing & Stats",
            "demo_p4_strings.py",
            "words = 'Artificial Intelligence in Action'.split()\nprint(f'Words: {len(words)}, Len: {[len(w) for w in words]}')\n",
            "Words: 4, Len: [10, 12, 2, 6]"
        ),
        (
            "File Writer & Output Generator",
            "demo_p5_writer.py",
            "with open('verified_output.txt', 'w', encoding='utf-8') as f:\n    f.write('Generated at demo: Success code 200\\nTimestamp verified.')\nprint('Wrote output file.')\n",
            "Wrote output file."
        )
    ]

    for name, fn, code, expected in programs:
        res = runner.run(code=code, filename=fn)
        if res.success and expected in res.data["stdout"]:
            print(f"    PASS: Program '{name}' succeeded. Output: {res.data['stdout'].strip()[:60]}")
        else:
            print(f"    FAIL: Program '{name}' failed: {res.message}")
            all_passed = False

    # 4. Read back file created in program 5 using ReadWorkspaceFileTool
    print("\n[4] Verifying ReadWorkspaceFileTool reading back generated file...")
    read_res = reader.run(filename="verified_output.txt")
    if read_res.success and "Success code 200" in read_res.data["content"]:
        print(f"    PASS: ReadWorkspaceFileTool successfully read 'verified_output.txt' ({read_res.data['size_bytes']} bytes).")
    else:
        print(f"    FAIL: ReadWorkspaceFileTool failed: {read_res.message}")
        all_passed = False

    # 5. Registry integration
    print("\n[5] Verifying Registry integration...")
    if "read_workspace_file" in TOOL_REGISTRY and "run_python" in TOOL_REGISTRY:
        reg_run = execute_tool("run_python", {"code": "print('registry_check_ok')", "filename": "reg_check.py"})
        reg_read = execute_tool("read_workspace_file", {"filename": "verified_output.txt"})
        if reg_run.success and reg_read.success:
            print("    PASS: Both tools successfully executed via execute_tool() dispatch.")
        else:
            print(f"    FAIL: execute_tool dispatch failed: run={reg_run.success}, read={reg_read.success}")
            all_passed = False
    else:
        print("    FAIL: Tools not found in TOOL_REGISTRY.")
        all_passed = False

    print("\n" + "=" * 70)
    if all_passed:
        print("ALL VERIFICATIONS PASSED SUCCESSFULLY (100%)")
    else:
        print("SOME VERIFICATIONS FAILED")
    print("=" * 70)

    # Clean up demo files
    for fn in ["verified_output.txt", "test_err_runtime.py", "test_err_syntax.py", "reg_check.py"]:
        p = os.path.join("workspace", fn)
        if os.path.exists(p):
            try:
                os.remove(p)
            except OSError:
                pass

    return all_passed


if __name__ == "__main__":
    success = run_verification()
    sys.exit(0 if success else 1)
