"""
File management tools for reading and writing files safely within Jarvis workspace.
Author: Abhijit (System & Automation Engineer)
"""

import os
from pathlib import Path
from typing import Any, Dict, Optional
from tools.base import BaseTool, ToolResult
from tools.safety import is_path_safe


def normalize_target_path(clean_path: str) -> str:
    """Normalize file path, mapping desktop/documents/downloads to actual user directories."""
    clean = clean_path.strip()
    clean_norm = clean.replace("\\", "/")
    parts = [p for p in clean_norm.split("/") if p]
    for idx, part in enumerate(parts):
        low = part.lower()
        if low == "desktop":
            sub = Path(*parts[idx + 1:]) if idx + 1 < len(parts) else Path()
            return str(Path.home() / "Desktop" / sub)
        if low in ("documents", "downloads"):
            sub = Path(*parts[idx + 1:]) if idx + 1 < len(parts) else Path()
            return str(Path.home() / low.capitalize() / sub)
    return os.path.expanduser(clean)


class FileContent(str):
    """String containing file content with optional dictionary-like access."""

    def __getitem__(self, key: Any) -> Any:
        if isinstance(key, str) and key == "content":
            return str(self)
        return super().__getitem__(key)

    def get(self, key: str, default: Any = None) -> Any:
        """Dictionary-like get method for content access."""
        if key == "content":
            return str(self)
        return default


class ReadFileTool(BaseTool):
    """Tool that safely reads text content from a file inside allowed directories."""
    name: str = "read_file"
    description: str = (
        "Reads the contents of a text file. Permitted locations include workspace/, "
        "user's Desktop ('Desktop/filename.ext'), Documents, Downloads, and temp_ directories. "
        "Access to sensitive system roots is blocked."
    )

    def run(
        self,
        file_path: str = "",
        path: Optional[str] = None,
        filepath: Optional[str] = None,
        encoding: str = "utf-8",
        **kwargs: Any
    ) -> ToolResult:
        """Reads file content from disk.

        Args:
            file_path: Relative or absolute path to the file to read.
            path: Alias for file_path.
            filepath: Alias for file_path.
            encoding: Character encoding to use (default: 'utf-8').
            **kwargs: Extra keyword arguments (ignored).

        Returns:
            ToolResult: Execution outcome with file content on success, or error details.
        """
        try:
            target_path = file_path or path or filepath
            if not target_path or not isinstance(target_path, str) or not target_path.strip():
                return ToolResult(
                    success=False,
                    data=None,
                    message="file_path must be a non-empty string."
                )

            clean_path = target_path.strip()

            expanded_path = normalize_target_path(clean_path)

            # Enforce path security isolation first
            if not is_path_safe(expanded_path):
                return ToolResult(
                    success=False,
                    data=None,
                    message=f"Permission Denied: Access to '{clean_path}' is not allowed."
                )

            resolved_path = os.path.realpath(expanded_path)
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
                raw_content = f.read()

            content = FileContent(raw_content)

            return ToolResult(
                success=True,
                data=content,
                message=f"File '{clean_path}' read successfully."
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
                message=f"Failed to read file '{target_path}': {str(e)}"
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
                        "description": "Path to the file to read (must be inside workspace/ or temp_ folders)."
                    },
                    "encoding": {
                        "type": "string",
                        "description": "Character encoding to use. Defaults to 'utf-8'.",
                        "default": "utf-8"
                    }
                },
                "required": ["file_path"]
            }
        }


class WriteFileTool(BaseTool):
    """Tool that safely writes text content to a file inside allowed directories."""
    name: str = "write_file"
    description: str = (
        "Writes text content to a file. Permitted locations include workspace/, "
        "user's Desktop ('Desktop/filename.ext'), Documents, Downloads, and temp_ directories. "
        "Existing files will not be overwritten unless overwrite=True is explicitly specified."
    )

    def run(
        self,
        file_path: str = "",
        content: Optional[str] = None,
        path: Optional[str] = None,
        filepath: Optional[str] = None,
        text: Optional[str] = None,
        data: Optional[str] = None,
        overwrite: bool = False,
        encoding: str = "utf-8",
        **kwargs: Any
    ) -> ToolResult:
        """Writes text content to disk.

        Args:
            file_path: Relative or absolute path to the file to write.
            content: Text content to write.
            path: Alias for file_path.
            filepath: Alias for file_path.
            text: Alias for content.
            data: Alias for content.
            overwrite: Whether to overwrite if the file already exists (default: False).
            encoding: Character encoding to use (default: 'utf-8').
            **kwargs: Extra keyword arguments (ignored).

        Returns:
            ToolResult: Execution outcome with write details on success, or error details.
        """
        try:
            target_path = file_path or path or filepath
            if not target_path or not isinstance(target_path, str) or not target_path.strip():
                return ToolResult(
                    success=False,
                    data=None,
                    message="file_path must be a non-empty string."
                )

            clean_path = target_path.strip()

            target_content = content if content is not None else (text if text is not None else (data if data is not None else ""))
            if not isinstance(target_content, str):
                target_content = str(target_content)

            expanded_path = normalize_target_path(clean_path)

            # Enforce path security isolation first
            if not is_path_safe(expanded_path):
                return ToolResult(
                    success=False,
                    data=None,
                    message=f"Permission Denied: Access to '{clean_path}' is not allowed."
                )

            resolved_path = os.path.realpath(expanded_path)

            # Check if file exists and prevent overwrite unless explicitly requested
            if os.path.exists(resolved_path) and not overwrite:
                return ToolResult(
                    success=False,
                    data=None,
                    message=f"File '{clean_path}' already exists and overwrite is set to False."
                )

            # Ensure parent directories exist
            parent_dir = os.path.dirname(resolved_path)
            if parent_dir and not os.path.exists(parent_dir):
                os.makedirs(parent_dir, exist_ok=True)

            with open(resolved_path, "w", encoding=encoding) as f:
                f.write(target_content)

            bytes_written = len(target_content.encode(encoding))

            return ToolResult(
                success=True,
                data={
                    "path": clean_path,
                    "bytes_written": bytes_written,
                    "overwrite": overwrite
                },
                message=f"File '{clean_path}' written successfully ({bytes_written} bytes)."
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
                message=f"Failed to write file '{target_path}': {str(e)}"
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
                        "description": "Path of the file to write (must be inside workspace/ or temp_ folders)."
                    },
                    "content": {
                        "type": "string",
                        "description": "Text content to write to the file."
                    },
                    "overwrite": {
                        "type": "boolean",
                        "description": "Whether to overwrite the file if it already exists. Defaults to False.",
                        "default": False
                    },
                    "encoding": {
                        "type": "string",
                        "description": "Character encoding to use. Defaults to 'utf-8'.",
                        "default": "utf-8"
                    }
                },
                "required": ["file_path", "content"]
            }
        }
