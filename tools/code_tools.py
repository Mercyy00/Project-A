"""
Code execution and file editing tools for Jarvis coding agent capabilities.
Author: Abhijit (System & Automation Engineer)
"""

import os
import re
import subprocess
import sys
from typing import Any, Dict, List, Optional
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
    """Tool that safely executes a Python script file or code snippet."""
    name: str = "run_python"
    description: str = (
        "Executes a Python script or inline Python code snippet safely using the project environment. "
        "Returns stdout, stderr, and exit code."
    )

    def run(
        self,
        code: Optional[str] = None,
        file_path: Optional[str] = None,
        path: Optional[str] = None,
        args: Optional[List[str]] = None,
        cwd: Optional[str] = None,
        timeout: int = 60,
        **kwargs: Any
    ) -> ToolResult:
        """Executes a Python script or code string.

        Args:
            code: Python code string to execute (optional if file_path is provided).
            file_path: Relative or absolute path to a Python script to execute.
            path: Alias for file_path.
            args: Optional list of command-line argument strings to pass to the script.
            cwd: Optional working directory for execution.
            timeout: Maximum execution time in seconds (default: 60).
            **kwargs: Extra keyword arguments.

        Returns:
            ToolResult: Execution outcome with stdout, stderr, and exit code.
        """
        try:
            target_path = file_path or path
            extra_args = args if (args is not None and isinstance(args, list)) else []

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
                        message=f"Permission Denied: Directory '{clean_cwd}' is not allowed."
                    )
                effective_cwd = os.path.realpath(clean_cwd)

            python_exe = sys.executable

            if target_path:
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

                cmd = [python_exe, resolved_path] + [str(a) for a in extra_args]
            elif code:
                if not isinstance(code, str) or not code.strip():
                    return ToolResult(
                        success=False,
                        data=None,
                        message="code must be a non-empty string if provided."
                    )
                cmd = [python_exe, "-c", code] + [str(a) for a in extra_args]
            else:
                return ToolResult(
                    success=False,
                    data=None,
                    message="Either 'code' or 'file_path' must be provided."
                )

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

            data = {
                "exit_code": proc.returncode,
                "stdout": proc.stdout,
                "stderr": proc.stderr,
                "cwd": effective_cwd
            }

            if proc.returncode == 0:
                summary = f"Python execution succeeded (exit code 0).\nOutput:\n{proc.stdout}" if proc.stdout else "Python execution succeeded with no stdout."
                return ToolResult(
                    success=True,
                    data=data,
                    message=summary.strip()
                )
            else:
                err_msg = proc.stderr.strip() or proc.stdout.strip() or f"Exited with code {proc.returncode}"
                return ToolResult(
                    success=False,
                    data=data,
                    message=f"Python execution failed (exit code {proc.returncode}): {err_msg}"
                )

        except subprocess.TimeoutExpired:
            return ToolResult(
                success=False,
                data={"exit_code": -1, "stdout": "", "stderr": f"Timed out after {timeout}s"},
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
                        "description": "Inline Python code to execute (optional if file_path is provided)."
                    },
                    "file_path": {
                        "type": "string",
                        "description": "Path to the Python script to execute (optional if code is provided)."
                    },
                    "args": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of command-line arguments to pass to the script."
                    },
                    "cwd": {
                        "type": "string",
                        "description": "Optional working directory for execution."
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Maximum seconds to wait before terminating. Defaults to 60.",
                        "default": 60
                    }
                },
                "required": []
            }
        }


# Export list of code tools
TOOLS: List[BaseTool] = [
    RunCommandTool(),
    EditFileTool(),
    RunPythonTool(),
]
