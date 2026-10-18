import os
import shutil
import subprocess
from typing import Any, Dict, List, Optional
import psutil

from tools.base import BaseTool, ToolResult


class GetSystemStatsTool(BaseTool):
    """Tool that retrieves telemetry information from the host machine."""
    name: str = "get_system_stats"
    description: str = (
        "Retrieves current laptop telemetry including CPU usage percentage, "
        "RAM usage, and battery status. Takes no arguments."
    )

    def run(self, **kwargs: Any) -> ToolResult:
        """Retrieves system telemetry.

        Args:
            **kwargs: Extra keyword arguments (ignored).

        Returns:
            ToolResult: System statistics including CPU, RAM, and Battery.
        """
        try:
            cpu_percent = psutil.cpu_percent(interval=0.2)
            ram = psutil.virtual_memory()
            battery = psutil.sensors_battery()

            battery_info = (
                f"{battery.percent}% ({'Plugged in' if battery.power_plugged else 'On Battery'})"
                if battery else "No battery detected (Desktop or AC power)"
            )

            stats = {
                "cpu_usage_percent": cpu_percent,
                "ram_usage_percent": ram.percent,
                "ram_used_gb": round(ram.used / (1024 ** 3), 2),
                "ram_total_gb": round(ram.total / (1024 ** 3), 2),
                "battery": battery_info
            }
            return ToolResult(
                success=True,
                data=stats,
                message="System statistics retrieved successfully."
            )
        except Exception as e:
            return ToolResult(
                success=False,
                data=None,
                message=f"Failed to fetch system stats: {str(e)}"
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
                "properties": {},
                "required": []
            }
        }


class OpenAppTool(BaseTool):
    """Tool that launches desktop applications on Windows by shortcut name."""
    name: str = "open_app"
    description: str = (
        "Opens an application on the Windows host machine by shortcut name. "
        "Supported shortcuts: 'chrome', 'code', 'calc', 'notepad', 'spotify'."
    )

    # Primary Windows executable path mapping for the 5 supported shortcuts
    APP_MAPPING: Dict[str, str] = {
        "chrome": r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        "code": os.path.expandvars(r"%LOCALAPPDATA%\Programs\Microsoft VS Code\Code.exe"),
        "calc": r"C:\Windows\System32\calc.exe",
        "notepad": r"C:\Windows\System32\notepad.exe",
        "spotify": os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WindowsApps\Spotify.exe"),
    }

    # Alternate candidates for different Windows setups
    APP_CANDIDATES: Dict[str, List[str]] = {
        "chrome": [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
        ],
        "code": [
            os.path.expandvars(r"%LOCALAPPDATA%\Programs\Microsoft VS Code\Code.exe"),
            r"C:\Program Files\Microsoft VS Code\Code.exe",
            r"C:\Program Files (x86)\Microsoft VS Code\Code.exe",
        ],
        "calc": [
            r"C:\Windows\System32\calc.exe",
            os.path.expandvars(r"%SystemRoot%\System32\calc.exe"),
        ],
        "notepad": [
            r"C:\Windows\System32\notepad.exe",
            os.path.expandvars(r"%SystemRoot%\System32\notepad.exe"),
        ],
        "spotify": [
            os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WindowsApps\Spotify.exe"),
            os.path.expandvars(r"%APPDATA%\Spotify\Spotify.exe"),
        ],
    }

    def _resolve_executable_path(self, shortcut: str) -> Optional[str]:
        """Resolves the executable path for a given shortcut.

        Args:
            shortcut: Shortcut name in lowercase.

        Returns:
            Optional[str]: Path to the executable if found, or default fallback.
        """
        candidates = self.APP_CANDIDATES.get(shortcut, [])
        for candidate in candidates:
            if candidate and os.path.exists(candidate):
                return candidate
        which_path = shutil.which(shortcut) or shutil.which(f"{shortcut}.exe")
        if which_path:
            return which_path
        return self.APP_MAPPING.get(shortcut)

    def run(self, app_name: str, **kwargs: Any) -> ToolResult:
        """Launches the requested application in a non-blocking process.

        Args:
            app_name: The shortcut name ('chrome', 'code', 'calc', 'notepad', 'spotify').
            **kwargs: Extra keyword arguments.

        Returns:
            ToolResult: Execution outcome with process PID or error details.
        """
        try:
            if not app_name or not isinstance(app_name, str):
                return ToolResult(
                    success=False,
                    data=None,
                    message="app_name must be a non-empty string."
                )

            key = app_name.strip().lower()
            if key not in self.APP_MAPPING:
                available = ", ".join(sorted(self.APP_MAPPING.keys()))
                return ToolResult(
                    success=False,
                    data=None,
                    message=f"Unknown application shortcut '{app_name}'. Supported shortcuts: {available}."
                )

            executable_path = self._resolve_executable_path(key)
            if not executable_path:
                return ToolResult(
                    success=False,
                    data=None,
                    message=f"Executable path for '{app_name}' could not be resolved."
                )

            process = subprocess.Popen(
                [executable_path],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            return ToolResult(
                success=True,
                data={
                    "app_name": key,
                    "executable": executable_path,
                    "pid": process.pid
                },
                message=f"Application '{key}' launched successfully (PID: {process.pid})."
            )
        except Exception as e:
            return ToolResult(
                success=False,
                data=None,
                message=f"Failed to launch '{app_name}': {str(e)}"
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
                    "app_name": {
                        "type": "string",
                        "description": "The shortcut name of the application to open.",
                        "enum": ["chrome", "code", "calc", "notepad", "spotify"]
                    }
                },
                "required": ["app_name"]
            }
        }


class FileEntry(str):
    """String representing a file/folder name with dictionary and attribute access for metadata."""

    def __new__(
        cls,
        name: str,
        is_dir: bool = False,
        size_bytes: Optional[int] = None
    ) -> "FileEntry":
        obj = super().__new__(cls, name)
        obj.name = name
        obj.is_dir = is_dir
        obj.type = "directory" if is_dir else "file"
        obj.size_bytes = size_bytes
        return obj

    def __getitem__(self, key: Any) -> Any:
        if isinstance(key, str):
            if key == "name":
                return self.name
            if key == "type":
                return self.type
            if key == "is_dir":
                return self.is_dir
            if key == "size_bytes":
                return self.size_bytes
            raise KeyError(key)
        return super().__getitem__(key)

    def get(self, key: str, default: Any = None) -> Any:
        """Dictionary-like get method for file metadata."""
        if key == "name":
            return self.name
        if key == "type":
            return self.type
        if key == "is_dir":
            return self.is_dir
        if key == "size_bytes":
            return self.size_bytes
        return default


class ListDirectoryTool(BaseTool):
    """Tool that lists files and folders in a specified directory path."""
    name: str = "list_directory"
    description: str = (
        "Lists files and folders in a specified directory path. "
        "Defaults to current working directory ('.')."
    )

    def run(self, directory_path: str = ".", **kwargs: Any) -> ToolResult:
        """Lists entries in the target directory.

        Args:
            directory_path: Directory path to inspect (defaults to '.').
            **kwargs: Extra keyword arguments.

        Returns:
            ToolResult: Result object containing list of files/folders.
        """
        try:
            if not isinstance(directory_path, str):
                return ToolResult(
                    success=False,
                    data=None,
                    message="directory_path must be a valid string."
                )

            resolved_path = os.path.abspath(directory_path)
            if not os.path.exists(resolved_path):
                return ToolResult(
                    success=False,
                    data=None,
                    message=f"Directory '{directory_path}' does not exist."
                )

            if not os.path.isdir(resolved_path):
                return ToolResult(
                    success=False,
                    data=None,
                    message=f"Path '{directory_path}' is not a directory."
                )

            entries: List[FileEntry] = []
            with os.scandir(resolved_path) as it:
                for entry in it:
                    try:
                        is_dir = entry.is_dir(follow_symlinks=False)
                        size = entry.stat(follow_symlinks=False).st_size if not is_dir else None
                    except (OSError, PermissionError):
                        is_dir = False
                        size = None
                    entries.append(FileEntry(entry.name, is_dir=is_dir, size_bytes=size))

            entries.sort(key=lambda x: (not x.is_dir, x.name.lower()))

            return ToolResult(
                success=True,
                data=entries,
                message=f"Found {len(entries)} items in '{directory_path}'."
            )
        except PermissionError as e:
            return ToolResult(
                success=False,
                data=None,
                message=f"Permission denied accessing directory '{directory_path}': {str(e)}"
            )
        except Exception as e:
            return ToolResult(
                success=False,
                data=None,
                message=f"Failed to list directory '{directory_path}': {str(e)}"
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
                    "directory_path": {
                        "type": "string",
                        "description": "Path to the directory to list. Defaults to '.'.",
                        "default": "."
                    }
                },
                "required": []
            }
        }
