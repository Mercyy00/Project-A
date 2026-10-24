"""
Code execution and file editing tools for Jarvis coding agent capabilities.
Author: Abhijit (System & Automation Engineer)
"""

import ast
import os
import re
import subprocess
import sys
from typing import Any, Dict, List, Optional, Tuple
from tools.base import BaseTool, ToolResult
from tools.safety import is_path_safe, get_designated_project_dir


# Destructive commands that must be blocked for system safety
_BLOCKED_COMMAND_PATTERNS = [
    re.compile(r"\bformat\s+[a-z]:", re.IGNORECASE),
    re.compile(r"\brmdir\s+/[sq]\s+[a-z]:\\", re.IGNORECASE),
    re.compile(r"\brd\s+/[sq]\s+[a-z]:\\", re.IGNORECASE),
    re.compile(r"\bdel\s+/[fsq]\s+[a-z]:\\", re.IGNORECASE),
    re.compile(r"\brm\s+-rf\s+/", re.IGNORECASE),
    re.compile(r"\b(mkfs|dd\s+if=)", re.IGNORECASE),
]


def validate_python_code_safety(code: str) -> Tuple[bool, Optional[str]]:
    """Inspects Python code for obviously destructive calls before execution.

    Blocks:
        - shutil.rmtree
        - os.system
        - subprocess calls with shell=True
        - os.remove / os.unlink targeting paths outside workspace/

    Args:
        code: Python source code string.

    Returns:
        Tuple[bool, Optional[str]]: (is_safe, error_reason_if_unsafe)
    """
    if not isinstance(code, str) or not code.strip():
        return False, "Code must be a non-empty string."

    # 1. Block shutil.rmtree
    if re.search(r"\bshutil\s*\.\s*rmtree\b", code):
        return (
            False,
            "Execution blocked: 'shutil.rmtree' is prohibited because recursive directory deletion is destructive and unsafe."
        )

    # 2. Block os.system
    if re.search(r"\bos\s*\.\s*system\b", code):
        return (
            False,
            "Execution blocked: 'os.system' is prohibited because arbitrary shell command execution bypasses safe process containment."
        )

    # 3. Block subprocess with shell=True
    if re.search(r"\bshell\s*=\s*(?:True|1)\b", code):
        return (
            False,
            "Execution blocked: 'subprocess' with 'shell=True' is prohibited to prevent shell injection and arbitrary command execution."
        )

    # 4. AST Analysis for deeper structural checks
    try:
        tree = ast.parse(code)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                # Check rmtree call
                if isinstance(node.func, ast.Attribute) and node.func.attr == "rmtree":
                    return (
                        False,
                        "Execution blocked: 'shutil.rmtree' is prohibited because recursive directory deletion is destructive and unsafe."
                    )
                # Check system call
                if isinstance(node.func, ast.Attribute) and node.func.attr == "system":
                    if isinstance(node.func.value, ast.Name) and node.func.value.id == "os":
                        return (
                            False,
                            "Execution blocked: 'os.system' is prohibited because arbitrary shell command execution bypasses safe process containment."
                        )
                # Check subprocess shell=True
                for kw in node.keywords:
                    if kw.arg == "shell":
                        if isinstance(kw.value, ast.Constant) and bool(kw.value.value) is True:
                            return (
                                False,
                                "Execution blocked: 'subprocess' with 'shell=True' is prohibited to prevent shell injection and arbitrary command execution."
                            )
                # Check os.remove / os.unlink
                is_remove = False
                if isinstance(node.func, ast.Attribute) and node.func.attr in ("remove", "unlink"):
                    if isinstance(node.func.value, ast.Name) and node.func.value.id == "os":
                        is_remove = True
                elif isinstance(node.func, ast.Name) and node.func.id in ("remove", "unlink"):
                    is_remove = True

                if is_remove and node.args:
                    arg = node.args[0]
                    if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                        raw_path = arg.value
                        norm = os.path.normpath(raw_path)
                        ws_abs = os.path.realpath("workspace")
                        if os.path.isabs(norm):
                            if not os.path.realpath(norm).lower().startswith(ws_abs.lower()):
                                return (
                                    False,
                                    f"Execution blocked: 'os.remove' on path '{raw_path}' outside workspace is prohibited."
                                )
                        else:
                            if norm.startswith("..") or (not norm.startswith("workspace") and not is_path_safe(norm)):
                                return (
                                    False,
                                    f"Execution blocked: 'os.remove' on path '{raw_path}' outside workspace is prohibited."
                                )
    except SyntaxError:
        pass

    # Regex check for os.remove with explicit path outside workspace
    remove_matches = re.finditer(r"\bos\s*\.\s*(?:remove|unlink)\s*\(\s*([rfu]?[b]?['\"][^'\"]+['\"])", code)
    for m in remove_matches:
        raw_path = m.group(1).lstrip("rfubRFUB").strip("'\"")
        norm = os.path.normpath(raw_path)
        ws_abs = os.path.realpath("workspace")
        if os.path.isabs(norm):
            if not os.path.realpath(norm).lower().startswith(ws_abs.lower()):
                return (
                    False,
                    f"Execution blocked: 'os.remove' on path '{raw_path}' outside workspace is prohibited."
                )
        else:
            if norm.startswith(".."):
                return (
                    False,
                    f"Execution blocked: 'os.remove' on path '{raw_path}' outside workspace is prohibited."
                )

    return True, None


class RunCommandTool(BaseTool):
    """Tool that executes shell commands (npm, pip, python, git, build commands, etc.)."""
    name: str = "run_command"
    description: str = (
        "Executes a shell command (such as npm, pip, python, node, git, or build scripts) "
        "inside the designated project directory or safe workspace. Returns exit code, stdout, and stderr."
    )

    def run(
        self,
        command: str,
        cwd: Optional[str] = None,
        timeout: int = 60,
        **kwargs: Any
    ) -> ToolResult:
        """Executes a shell command synchronously and returns the output.

        Args:
            command: The command line string to execute.
            cwd: Working directory in which to execute the command (optional, defaults to project root).
            timeout: Maximum seconds to wait before terminating the process (default: 60).
            **kwargs: Extra keyword arguments.

        Returns:
            ToolResult: Execution outcome with exit code, stdout, and stderr.
        """
        try:
            if not command or not isinstance(command, str) or not command.strip():
                return ToolResult(
                    success=False,
                    data=None,
                    message="command must be a non-empty string."
                )

            clean_command = command.strip()

            # Safety check: Block overtly destructive system wiping commands
            for pattern in _BLOCKED_COMMAND_PATTERNS:
                if pattern.search(clean_command):
                    return ToolResult(
                        success=False,
                        data=None,
                        message=f"Command rejected for safety: destructive pattern detected in '{clean_command}'."
                    )

            # Determine working directory
            effective_cwd = get_designated_project_dir()
            if cwd:
                if not isinstance(cwd, str) or not cwd.strip():
                    return ToolResult(
                        success=False,
                        data=None,
                        message="cwd must be a non-empty string if provided."
                    )
                clean_cwd = cwd.strip()
                if not is_path_safe(clean_cwd):
                    return ToolResult(
                        success=False,
                        data=None,
                        message=f"Permission Denied: Execution directory '{clean_cwd}' is not allowed."
                    )
                effective_cwd = os.path.realpath(clean_cwd)

            if not os.path.exists(effective_cwd):
                return ToolResult(
                    success=False,
                    data=None,
                    message=f"Execution directory does not exist: '{effective_cwd}'."
                )

            # Execute command non-interactively
            proc = subprocess.run(
                clean_command,
                shell=True,
                capture_output=True,
                stdin=subprocess.DEVNULL,
                text=True,
                cwd=effective_cwd,
                timeout=timeout,
                encoding="utf-8",
                errors="replace"
            )

            data = {
                "exit_code": proc.returncode,
                "stdout": proc.stdout,
                "stderr": proc.stderr,
                "cwd": effective_cwd,
                "command": clean_command
            }

            if proc.returncode == 0:
                summary = f"Command succeeded (exit code 0).\nOutput:\n{proc.stdout}" if proc.stdout else "Command succeeded with no stdout."
                return ToolResult(
                    success=True,
                    data=data,
                    message=summary.strip()
                )
            else:
                err_msg = proc.stderr.strip() or proc.stdout.strip() or f"Process exited with code {proc.returncode}"
                return ToolResult(
                    success=False,
                    data=data,
                    message=f"Command failed (exit code {proc.returncode}): {err_msg}"
                )

        except subprocess.TimeoutExpired:
            return ToolResult(
                success=False,
                data={"exit_code": -1, "stdout": "", "stderr": f"Timed out after {timeout}s"},
                message=f"Command timed out after {timeout} seconds: '{command}'"
            )
        except Exception as e:
            return ToolResult(
                success=False,
                data=None,
                message=f"Failed to execute command '{command}': {str(e)}"
            )

    def get_schema(self) -> Dict[str, Any]:
        """Returns JSON schema definition for LLM tool calling.

        Returns:
            Dict[str, Any]: JSON schema specification.
        """
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The shell command to execute (e.g. 'npm install', 'git status', 'python app.py')."
                    },
                    "cwd": {
                        "type": "string",
                        "description": "Optional working directory for execution. Defaults to project root.",
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Maximum seconds to wait before terminating command. Defaults to 60.",
                        "default": 60
                    }
                },
                "required": ["command"]
            }
        }


class EditFileTool(BaseTool):
    """Tool that performs targeted search-and-replace edits inside safe project files."""
    name: str = "edit_file"
    description: str = (
        "Edits an existing file by replacing target_text with replacement_text. "
        "Allows precise codebase modifications without overwriting entire files."
    )

    def run(
        self,
        file_path: str = "",
        target_text: str = "",
        replacement_text: str = "",
        path: Optional[str] = None,
        filepath: Optional[str] = None,
        replace_all: bool = False,
        encoding: str = "utf-8",
        **kwargs: Any
    ) -> ToolResult:
        """Replaces target_text with replacement_text in the specified file.

        Args:
            file_path: Path to the file to edit.
            target_text: Exact string to find and replace.
            replacement_text: String to insert in place of target_text.
            path: Alias for file_path.
            filepath: Alias for file_path.
            replace_all: If True, replaces all occurrences; if False, replaces first occurrence only. Defaults to False.
            encoding: Character encoding to use (default: 'utf-8').
            **kwargs: Extra keyword arguments.

        Returns:
            ToolResult: Execution outcome with replacement statistics.
        """
        try:
            target_path = file_path or path or filepath
            if not target_path or not isinstance(target_path, str) or not target_path.strip():
                return ToolResult(
                    success=False,
                    data=None,
                    message="file_path must be a non-empty string."
                )

            if target_text is None or not isinstance(target_text, str) or not target_text:
                return ToolResult(
                    success=False,
                    data=None,
                    message="target_text must be a non-empty string to match."
                )

            if replacement_text is None or not isinstance(replacement_text, str):
                return ToolResult(
                    success=False,
                    data=None,
                    message="replacement_text must be a string."
                )

            clean_path = target_path.strip()

            # Security check
            if not is_path_safe(clean_path):
                return ToolResult(
                    success=False,
                    data=None,
                    message=f"Permission Denied: Access to '{clean_path}' is not allowed."
                )

            resolved_path = os.path.realpath(clean_path)
            if not os.path.exists(resolved_path):
                return ToolResult(
                    success=False,
                    data=None,
                    message=f"File not found: '{clean_path}'."
                )

            if not os.path.isfile(resolved_path):
                return ToolResult(
                    success=False,
                    data=None,
                    message=f"Path is not a regular file: '{clean_path}'."
                )

            with open(resolved_path, "r", encoding=encoding, errors="replace") as f:
                content = f.read()

            if target_text not in content:
                return ToolResult(
                    success=False,
                    data=None,
                    message=f"target_text not found in '{clean_path}'."
                )

            occurrences = content.count(target_text)
            if replace_all:
                new_content = content.replace(target_text, replacement_text)
                replaced_count = occurrences
            else:
                new_content = content.replace(target_text, replacement_text, 1)
                replaced_count = 1

            with open(resolved_path, "w", encoding=encoding) as f:
                f.write(new_content)

            return ToolResult(
                success=True,
                data={
                    "path": clean_path,
                    "occurrences_found": occurrences,
                    "occurrences_replaced": replaced_count,
                    "replace_all": replace_all
                },
                message=f"Successfully replaced {replaced_count} occurrence(s) of target_text in '{clean_path}'."
            )

        except PermissionError as pe:
            return ToolResult(
                success=False,
                data=None,
                message=f"Permission Denied: Operating system denied access to '{target_path}': {str(pe)}"
            )
        except Exception as e:
            return ToolResult(
                success=False,
                data=None,
                message=f"Failed to edit file '{target_path}': {str(e)}"
            )

    def get_schema(self) -> Dict[str, Any]:
        """Returns JSON schema definition for LLM tool calling.

        Returns:
            Dict[str, Any]: JSON schema specification.
        """
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to the file to edit."
                    },
                    "target_text": {
                        "type": "string",
                        "description": "The exact string segment in the file to find and replace."
                    },
                    "replacement_text": {
                        "type": "string",
                        "description": "The new string segment to insert in place of target_text."
                    },
                    "replace_all": {
                        "type": "boolean",
                        "description": "Whether to replace all occurrences or only the first occurrence. Defaults to False.",
                        "default": False
                    }
                },
                "required": ["file_path", "target_text", "replacement_text"]
            }
        }


class RunPythonTool(BaseTool):
    """Tool that safely saves and executes Python code inside the workspace/ directory."""
    name: str = "run_python"
    description: str = (
        "Saves Python code into the workspace/ directory and executes it safely with a 10-second timeout. "
        "Enforces safety guardrails against destructive operations, captures stdout and stderr, "
        "and truncates output to 4000 characters."
    )

    def run(
        self,
        code: Optional[str] = None,
        filename: str = "script.py",
        file_path: Optional[str] = None,
        path: Optional[str] = None,
        args: Optional[List[str]] = None,
        cwd: Optional[str] = None,
        timeout: int = 10,
        **kwargs: Any
    ) -> ToolResult:
        """Executes a Python program safely inside workspace/.

        Args:
            code: Python code string to execute.
            filename: Target file name inside workspace/ without path separators (defaults to 'script.py').
            file_path: Optional file path to execute directly (for backward compatibility).
            path: Alias for file_path.
            args: Optional list of command-line argument strings to pass to the script.
            cwd: Optional execution directory (defaults to workspace/).
            timeout: Execution timeout in seconds (default: 10).
            **kwargs: Extra keyword arguments.

        Returns:
            ToolResult: Structured execution outcome with stdout, stderr, and exit code.
        """
        try:
            target_path = file_path or path
            extra_args = args if (args is not None and isinstance(args, list)) else []

            if code is not None:
                if not isinstance(code, str) or not code.strip():
                    return ToolResult(
                        success=False,
                        data=None,
                        message="code must be a non-empty string."
                    )

                if not filename or not isinstance(filename, str) or not filename.strip():
                    return ToolResult(
                        success=False,
                        data=None,
                        message="filename must be a non-empty string."
                    )

                clean_filename = filename.strip()

                # Validate that filename has no path separators or directory traversals
                if (
                    "/" in clean_filename
                    or "\\" in clean_filename
                    or os.path.sep in clean_filename
                    or (os.path.altsep and os.path.altsep in clean_filename)
                    or ".." in clean_filename
                    or ":" in clean_filename
                ):
                    return ToolResult(
                        success=False,
                        data=None,
                        message="filename must not contain path separators. Code must be saved directly inside workspace/."
                    )

                # Block code containing destructive calls
                is_safe, blocked_reason = validate_python_code_safety(code)
                if not is_safe:
                    return ToolResult(
                        success=False,
                        data=None,
                        message=blocked_reason or "Code execution blocked due to safety violations."
                    )

                # Save code into workspace/ (create the folder if it does not exist)
                workspace_dir = os.path.realpath("workspace")
                os.makedirs(workspace_dir, exist_ok=True)
                dest_file = os.path.join(workspace_dir, clean_filename)
                with open(dest_file, "w", encoding="utf-8") as f:
                    f.write(code)

                effective_file = dest_file
                effective_cwd = workspace_dir
                effective_filename = clean_filename

            elif target_path:
                clean_path = target_path.strip()
                if not is_path_safe(clean_path):
                    return ToolResult(
                        success=False,
                        data=None,
                        message=f"Permission Denied: Access to '{clean_path}' is not allowed."
                    )

                resolved_path = os.path.realpath(clean_path)
                if not os.path.exists(resolved_path):
                    return ToolResult(
                        success=False,
                        data=None,
                        message=f"Script file not found: '{clean_path}'."
                    )

                effective_file = resolved_path
                effective_cwd = os.path.realpath(cwd) if cwd else os.path.realpath("workspace")
                effective_filename = os.path.basename(resolved_path)

            else:
                return ToolResult(
                    success=False,
                    data=None,
                    message="Either 'code' or 'file_path' must be provided."
                )

            python_exe = sys.executable
            cmd = [python_exe, effective_file] + [str(a) for a in extra_args]

            proc = subprocess.run(
                cmd,
                capture_output=True,
                stdin=subprocess.DEVNULL,
                text=True,
                cwd=effective_cwd,
                timeout=timeout,
                encoding="utf-8",
                errors="replace"
            )

            # Truncate output to 4000 characters
            max_chars = 4000
            stdout = proc.stdout
            stderr = proc.stderr
            if len(stdout) > max_chars:
                stdout = stdout[:max_chars] + f"\n... [Output truncated to {max_chars} characters]"
            if len(stderr) > max_chars:
                stderr = stderr[:max_chars] + f"\n... [Error output truncated to {max_chars} characters]"

            data = {
                "exit_code": proc.returncode,
                "stdout": stdout,
                "stderr": stderr,
                "cwd": effective_cwd,
                "filename": effective_filename
            }

            if proc.returncode == 0:
                summary = stdout.strip() if stdout.strip() else "Python execution succeeded with no stdout."
                return ToolResult(
                    success=True,
                    data=data,
                    message=summary
                )
            else:
                err_msg = stderr.strip() or stdout.strip() or f"Process exited with code {proc.returncode}"
                return ToolResult(
                    success=False,
                    data=data,
                    message=f"Python execution failed (exit code {proc.returncode}): {err_msg}"
                )

        except subprocess.TimeoutExpired:
            return ToolResult(
                success=False,
                data={
                    "exit_code": -1,
                    "stdout": "",
                    "stderr": f"Timed out after {timeout} seconds",
                    "timed_out": True,
                    "filename": filename if code is not None else ""
                },
                message=f"Python execution timed out after {timeout} seconds."
            )
        except Exception as e:
            return ToolResult(
                success=False,
                data=None,
                message=f"Failed to execute Python code: {str(e)}"
            )

    def get_schema(self) -> Dict[str, Any]:
        """Returns JSON schema definition for LLM tool calling.

        Returns:
            Dict[str, Any]: JSON schema specification.
        """
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "Python source code to execute inside workspace/."
                    },
                    "filename": {
                        "type": "string",
                        "description": "Target filename inside workspace/ without path separators (default: 'script.py').",
                        "default": "script.py"
                    }
                },
                "required": ["code"]
            }
        }


# Export list of code tools
TOOLS: List[BaseTool] = [
    RunCommandTool(),
    EditFileTool(),
    RunPythonTool(),
]
