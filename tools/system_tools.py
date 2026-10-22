import os
import shutil
import subprocess
import urllib.parse
import webbrowser
from typing import Any, Dict, List, Optional
import psutil

from tools.base import BaseTool, ToolResult
from tools.safety import is_path_safe
from pathlib import Path


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
                "cpu_percent": cpu_percent,
                "ram_usage_percent": ram.percent,
                "ram_used_pct": ram.percent,
                "ram_used_gb": round(ram.used / (1024 ** 3), 2),
                "ram_total_gb": round(ram.total / (1024 ** 3), 2),
                "battery": battery_info,
                "battery_pct": battery.percent if battery else 100,
                "battery_plugged": battery.power_plugged if battery else True,
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
        "Supported shortcuts: 'calc', 'chrome', 'cmd', 'code', 'excel', 'explorer', "
        "'notepad', 'paint', 'powershell', 'settings', 'spotify', 'taskmgr', 'vlc', 'word'."
    )

    # Primary Windows executable path mapping for supported shortcuts
    APP_MAPPING: Dict[str, str] = {
        "calc": r"C:\Windows\System32\calc.exe",
        "calculator": r"C:\Windows\System32\calc.exe",
        "chrome": r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        "cmd": r"C:\Windows\System32\cmd.exe",
        "code": os.path.expandvars(r"%LOCALAPPDATA%\Programs\Microsoft VS Code\Code.exe"),
        "excel": r"C:\Program Files\Microsoft Office\root\Office16\EXCEL.EXE",
        "explorer": r"C:\Windows\explorer.exe",
        "mspaint": r"C:\Windows\System32\mspaint.exe",
        "notepad": r"C:\Windows\System32\notepad.exe",
        "paint": r"C:\Windows\System32\mspaint.exe",
        "powerpoint": r"C:\Program Files\Microsoft Office\root\Office16\POWERPNT.EXE",
        "powershell": r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe",
        "settings": r"C:\Windows\ImmersiveControlPanel\SystemSettings.exe",
        "spotify": os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WindowsApps\Spotify.exe"),
        "taskmgr": r"C:\Windows\System32\Taskmgr.exe",
        "terminal": os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WindowsApps\wt.exe"),
        "vlc": r"C:\Program Files\VideoLAN\VLC\vlc.exe",
        "word": r"C:\Program Files\Microsoft Office\root\Office16\WINWORD.EXE",
    }

    # Alternate candidates for different Windows setups
    APP_CANDIDATES: Dict[str, List[str]] = {
        "calc": [
            r"C:\Windows\System32\calc.exe",
            os.path.expandvars(r"%SystemRoot%\System32\calc.exe"),
        ],
        "calculator": [
            r"C:\Windows\System32\calc.exe",
            os.path.expandvars(r"%SystemRoot%\System32\calc.exe"),
        ],
        "chrome": [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
        ],
        "cmd": [
            r"C:\Windows\System32\cmd.exe",
            os.path.expandvars(r"%SystemRoot%\System32\cmd.exe"),
        ],
        "code": [
            os.path.expandvars(r"%LOCALAPPDATA%\Programs\Microsoft VS Code\Code.exe"),
            r"C:\Program Files\Microsoft VS Code\Code.exe",
            r"C:\Program Files (x86)\Microsoft VS Code\Code.exe",
        ],
        "excel": [
            r"C:\Program Files\Microsoft Office\root\Office16\EXCEL.EXE",
            r"C:\Program Files (x86)\Microsoft Office\root\Office16\EXCEL.EXE",
            r"C:\Program Files\Microsoft Office\Office16\EXCEL.EXE",
            r"C:\Program Files (x86)\Microsoft Office\Office16\EXCEL.EXE",
            r"C:\Program Files\Microsoft Office\Office15\EXCEL.EXE",
            r"C:\Program Files (x86)\Microsoft Office\Office15\EXCEL.EXE",
        ],
        "explorer": [
            r"C:\Windows\explorer.exe",
            os.path.expandvars(r"%SystemRoot%\explorer.exe"),
        ],
        "mspaint": [
            r"C:\Windows\System32\mspaint.exe",
            os.path.expandvars(r"%SystemRoot%\System32\mspaint.exe"),
            os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WindowsApps\mspaint.exe"),
        ],
        "notepad": [
            "notepad.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WindowsApps\notepad.exe"),
            r"C:\Windows\System32\notepad.exe",
            os.path.expandvars(r"%SystemRoot%\System32\notepad.exe"),
        ],
        "paint": [
            r"C:\Windows\System32\mspaint.exe",
            os.path.expandvars(r"%SystemRoot%\System32\mspaint.exe"),
            os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WindowsApps\mspaint.exe"),
        ],
        "powerpoint": [
            r"C:\Program Files\Microsoft Office\root\Office16\POWERPNT.EXE",
            r"C:\Program Files (x86)\Microsoft Office\root\Office16\POWERPNT.EXE",
            r"C:\Program Files\Microsoft Office\Office16\POWERPNT.EXE",
            r"C:\Program Files (x86)\Microsoft Office\Office16\POWERPNT.EXE",
            r"C:\Program Files\Microsoft Office\Office15\POWERPNT.EXE",
            r"C:\Program Files (x86)\Microsoft Office\Office15\POWERPNT.EXE",
        ],
        "powershell": [
            r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe",
            os.path.expandvars(r"%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe"),
        ],
        "settings": [
            r"C:\Windows\ImmersiveControlPanel\SystemSettings.exe",
            os.path.expandvars(r"%SystemRoot%\ImmersiveControlPanel\SystemSettings.exe"),
            r"C:\Windows\System32\control.exe",
            os.path.expandvars(r"%SystemRoot%\System32\control.exe"),
        ],
        "spotify": [
            os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WindowsApps\Spotify.exe"),
            os.path.expandvars(r"%APPDATA%\Spotify\Spotify.exe"),
        ],
        "taskmgr": [
            r"C:\Windows\System32\Taskmgr.exe",
            os.path.expandvars(r"%SystemRoot%\System32\Taskmgr.exe"),
        ],
        "terminal": [
            os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WindowsApps\wt.exe"),
        ],
        "vlc": [
            r"C:\Program Files\VideoLAN\VLC\vlc.exe",
            r"C:\Program Files (x86)\VideoLAN\VLC\vlc.exe",
        ],
        "word": [
            r"C:\Program Files\Microsoft Office\root\Office16\WINWORD.EXE",
            r"C:\Program Files (x86)\Microsoft Office\root\Office16\WINWORD.EXE",
            r"C:\Program Files\Microsoft Office\Office16\WINWORD.EXE",
            r"C:\Program Files (x86)\Microsoft Office\Office16\WINWORD.EXE",
            r"C:\Program Files\Microsoft Office\Office15\WINWORD.EXE",
            r"C:\Program Files (x86)\Microsoft Office\Office15\WINWORD.EXE",
        ],
    }

    # Extended natural language alias map for common app names
    APP_ALIASES: Dict[str, str] = {
        "calculator": "calc",
        "calculator app": "calc",
        "calc": "calc",
        "vscode": "code",
        "vs code": "code",
        "visual studio code": "code",
        "google chrome": "chrome",
        "browser": "chrome",
        "command prompt": "cmd",
        "command": "cmd",
        "ms word": "word",
        "word": "word",
        "microsoft word": "word",
        "ms excel": "excel",
        "excel": "excel",
        "microsoft excel": "excel",
        "ms paint": "paint",
        "drawing": "paint",
        "task manager": "taskmgr",
        "taskmanager": "taskmgr",
        "windows terminal": "terminal",
        "file explorer": "explorer",
        "files": "explorer",
        "control panel": "settings",
        "camera": "camera",
    }

    # Windows UWP protocol schemes for modern store apps
    APP_PROTOCOLS: Dict[str, str] = {
        "calc": "calculator:",
        "calculator": "calculator:",
        "settings": "ms-settings:",
        "camera": "microsoft.windows.camera:",
        "spotify": "spotify:",
        "whatsapp": "whatsapp:",
    }

    # Windows 11 UWP App Execution Alias / AppsFolder mappings
    APP_APPSFOLDER: Dict[str, str] = {
        "notepad": r"shell:AppsFolder\Microsoft.WindowsNotepad_8wekyb3d8bbwe!App",
        "calc": r"shell:AppsFolder\Microsoft.WindowsCalculator_8wekyb3d8bbwe!App",
        "calculator": r"shell:AppsFolder\Microsoft.WindowsCalculator_8wekyb3d8bbwe!App",
        "camera": r"shell:AppsFolder\Microsoft.WindowsCamera_8wekyb3d8bbwe!App",
        "terminal": r"shell:AppsFolder\Microsoft.WindowsTerminal_8wekyb3d8bbwe!App",
        "paint": r"shell:AppsFolder\Microsoft.MSPaint_8wekyb3d8bbwe!Microsoft.MSPaint",
    }

    @staticmethod
    def _find_start_menu_shortcut(name: str) -> Optional[str]:
        """Scans Windows Start Menu directories for matching .lnk application shortcuts."""
        if os.name != "nt":
            return None
        dirs = [
            os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs"),
            os.path.expandvars(r"%PROGRAMDATA%\Microsoft\Windows\Start Menu\Programs"),
        ]
        target = name.lower()
        for d in dirs:
            if not os.path.exists(d):
                continue
            for root, _, files in os.walk(d):
                for f in files:
                    if f.lower().endswith(".lnk") and target in f.lower():
                        return os.path.join(root, f)
        return None

    # Common executable names mapped for PATH and Registry lookups
    APP_EXECUTABLES: Dict[str, List[str]] = {
        "calc": ["calc.exe"],
        "chrome": ["chrome.exe"],
        "cmd": ["cmd.exe"],
        "code": ["code.exe"],
        "excel": ["excel.exe"],
        "explorer": ["explorer.exe"],
        "mspaint": ["mspaint.exe"],
        "notepad": ["notepad.exe"],
        "paint": ["mspaint.exe"],
        "powerpoint": ["powerpnt.exe"],
        "powershell": ["powershell.exe"],
        "settings": ["SystemSettings.exe", "control.exe"],
        "spotify": ["spotify.exe"],
        "taskmgr": ["taskmgr.exe"],
        "terminal": ["wt.exe"],
        "vlc": ["vlc.exe"],
        "word": ["winword.exe"],
    }

    @staticmethod
    def _query_registry_app_path(exe_name: str) -> Optional[str]:
        """Queries Windows Registry App Paths for registered application executables."""
        if os.name != "nt":
            return None
        try:
            import winreg
            for root in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
                key_path = rf"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\{exe_name}"
                try:
                    with winreg.OpenKey(root, key_path) as k:
                        val, _ = winreg.QueryValueEx(k, "")
                        if val and os.path.exists(val):
                            return val
                except OSError:
                    continue
        except Exception:
            pass
        return None

    def _resolve_executable_path(self, shortcut: str) -> Optional[str]:
        """Resolves the executable path for a given shortcut.

        Args:
            shortcut: Shortcut name in lowercase.

        Returns:
            Optional[str]: Path to the executable if found, or default fallback.
        """
        # 1. Check predefined candidate paths
        candidates = self.APP_CANDIDATES.get(shortcut, [])
        for candidate in candidates:
            if candidate and os.path.exists(candidate):
                return candidate

        # 2. Check PATH via shutil.which for shortcut and alias executables
        exe_aliases = self.APP_EXECUTABLES.get(shortcut, [shortcut, f"{shortcut}.exe"])
        for alias in [shortcut, f"{shortcut}.exe"] + exe_aliases:
            which_path = shutil.which(alias)
            if which_path and os.path.exists(which_path):
                return which_path

        # 3. Check Windows Registry App Paths
        for alias in exe_aliases:
            alias_name = alias if alias.endswith(".exe") else f"{alias}.exe"
            reg_path = self._query_registry_app_path(alias_name)
            if reg_path and os.path.exists(reg_path):
                return reg_path

        # 4. Fallback to mapped default path
        mapped = self.APP_MAPPING.get(shortcut)
        return mapped

    def run(self, app_name: str, **kwargs: Any) -> ToolResult:
        """Launches the requested application in a non-blocking process.

        Args:
            app_name: The shortcut or application name (e.g., 'calculator', 'chrome', 'cmd', 'notepad').
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

            raw_key = app_name.strip().lower()
            key = self.APP_ALIASES.get(raw_key, raw_key)

            # Direct launch for notepad (handles classic notepad and Windows 11 UWP App Execution Alias)
            if key == "notepad":
                notepad_candidates = [
                    "notepad.exe",
                    shutil.which("notepad.exe") or "notepad.exe",
                    os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WindowsApps\notepad.exe"),
                    r"C:\Windows\System32\notepad.exe",
                    os.path.expandvars(r"%SystemRoot%\System32\notepad.exe"),
                    r"C:\Windows\notepad.exe",
                ]
                for candidate in notepad_candidates:
                    if candidate and (not os.path.isabs(candidate) or os.path.exists(candidate)):
                        try:
                            proc = subprocess.Popen(
                                [candidate],
                                stdin=subprocess.DEVNULL,
                                stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL
                            )
                            return ToolResult(
                                success=True,
                                data={
                                    "app_name": "notepad",
                                    "executable": candidate,
                                    "pid": proc.pid
                                },
                                message=f"Application 'notepad' launched successfully (PID: {proc.pid})."
                            )
                        except Exception:
                            continue

                # Windows 11 UWP App Execution Alias / AppsFolder fallback
                uwp_notepad = self.APP_APPSFOLDER.get("notepad")
                if uwp_notepad and os.name == "nt":
                    try:
                        proc = subprocess.Popen(["explorer.exe", uwp_notepad])
                        return ToolResult(
                            success=True,
                            data={"app_name": "notepad", "uwp_alias": uwp_notepad, "pid": proc.pid},
                            message="Application 'notepad' launched successfully via Windows 11 UWP App Execution Alias."
                        )
                    except Exception:
                        pass

            # 1. Try Windows UWP protocol if registered (e.g. calculator:, ms-settings:)
            protocol = self.APP_PROTOCOLS.get(raw_key) or self.APP_PROTOCOLS.get(key)
            if protocol and os.name == "nt":
                try:
                    os.startfile(protocol)
                    return ToolResult(
                        success=True,
                        data={"app_name": raw_key, "protocol": protocol},
                        message=f"Application '{app_name}' launched successfully via Windows protocol '{protocol}'."
                    )
                except Exception:
                    pass

            # 2. Resolve executable path
            executable_path = self._resolve_executable_path(key)

            # 3. If not in predefined mapping, scan Windows Start Menu for installed .lnk shortcuts
            if not executable_path and os.name == "nt":
                executable_path = self._find_start_menu_shortcut(raw_key) or self._find_start_menu_shortcut(key)

            if not executable_path:
                if key not in self.APP_MAPPING:
                    available = ", ".join(sorted(self.APP_MAPPING.keys()))
                    return ToolResult(
                        success=False,
                        data=None,
                        message=f"Unknown application shortcut '{app_name}'. Supported shortcuts: {available}."
                    )
                return ToolResult(
                    success=False,
                    data=None,
                    message=f"Executable path for '{app_name}' could not be resolved."
                )

            # 4. If Start Menu shortcut (.lnk), launch via Windows Shell
            if executable_path.lower().endswith(".lnk") and os.name == "nt":
                try:
                    os.startfile(executable_path)
                    return ToolResult(
                        success=True,
                        data={"app_name": raw_key, "shortcut_path": executable_path},
                        message=f"Application '{app_name}' launched successfully from Start Menu."
                    )
                except Exception as exc:
                    return ToolResult(
                        success=False,
                        data=None,
                        message=f"Failed to launch Start Menu shortcut for '{app_name}': {exc}"
                    )

            if not os.path.exists(executable_path) and not shutil.which(executable_path):
                return ToolResult(
                    success=False,
                    data=None,
                    message=f"Application '{app_name}' is not installed or executable not found at '{executable_path}'."
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
                        "enum": sorted(list(self.APP_MAPPING.keys()))
                    }
                },
                "required": ["app_name"]
            }
        }


class OpenFileTool(BaseTool):
    """Tool that opens a file, PDF, Word document, or presentation in its default Windows desktop application."""
    name: str = "open_file"
    description: str = (
        "Opens a file, PDF, Word document, or presentation in its default Windows desktop application."
    )

    def run(
        self,
        file_path: str = "",
        path: Optional[str] = None,
        filepath: Optional[str] = None,
        **kwargs: Any
    ) -> ToolResult:
        """Opens a file in its default Windows desktop application.

        Args:
            file_path: Relative or absolute path to the file to open (e.g. 'workspace/file.pdf').
            path: Alias for file_path.
            filepath: Alias for file_path.
            **kwargs: Extra keyword arguments.

        Returns:
            ToolResult: Execution outcome indicating whether the file was opened.
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

            # Normalize user home and Desktop references
            expanded_path = os.path.expanduser(clean_path)
            clean_lower = clean_path.replace("\\", "/").lower()
            if clean_lower.startswith("desktop/") or clean_lower == "desktop":
                expanded_path = str(Path.home() / clean_path)

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

            if os.name == "nt":
                os.startfile(resolved_path)
            else:
                subprocess.Popen(["xdg-open", resolved_path])

            return ToolResult(
                success=True,
                data={
                    "file_path": clean_path,
                    "resolved_path": resolved_path
                },
                message=f"File '{clean_path}' opened in default application."
            )
        except Exception as e:
            return ToolResult(
                success=False,
                data=None,
                message=f"Failed to open file '{clean_path}': {str(e)}"
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
                        "description": "Path to the file to open (e.g. 'workspace/file.pdf'). Must be inside workspace/ or allowed safe directories."
                    }
                },
                "required": ["file_path"]
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


class OpenWebsiteTool(BaseTool):
    """Tool that opens a website in the default browser by shortcut or direct URL."""
    name: str = "open_website"
    description: str = (
        "Opens a website in the default web browser. Accepts popular shortcuts "
        "('youtube', 'google', 'gmail', 'github') or direct URLs starting with 'http://' or 'https://'."
    )

    SHORTCUTS: Dict[str, str] = {
        "youtube": "https://www.youtube.com",
        "google": "https://www.google.com",
        "gmail": "https://mail.google.com",
        "github": "https://github.com",
    }

    def run(self, site: str, **kwargs: Any) -> ToolResult:
        """Opens a website shortcut or HTTP(S) URL in the default web browser.

        Args:
            site: Shortcut name ('youtube', 'google', 'gmail', 'github') or full HTTP/HTTPS URL.
            **kwargs: Extra keyword arguments.

        Returns:
            ToolResult: Execution outcome indicating success or error details.
        """
        try:
            if not site or not isinstance(site, str) or not site.strip():
                return ToolResult(
                    success=False,
                    data=None,
                    message="site must be a non-empty string."
                )

            clean_site = site.strip()
            parsed = urllib.parse.urlparse(clean_site)

            # Check for explicit URL scheme
            if parsed.scheme:
                scheme_lower = parsed.scheme.lower()
                if scheme_lower not in ("http", "https"):
                    return ToolResult(
                        success=False,
                        data=None,
                        message=f"Invalid URL scheme '{parsed.scheme}'. Only 'http://' and 'https://' are supported."
                    )
                if not parsed.netloc and not parsed.path:
                    return ToolResult(
                        success=False,
                        data=None,
                        message=f"Invalid URL '{clean_site}': Missing host/domain."
                    )
                target_url = clean_site
            elif clean_site.lower().startswith(("http://", "https://")):
                target_url = clean_site
            elif clean_site.lower() in self.SHORTCUTS:
                target_url = self.SHORTCUTS[clean_site.lower()]
            else:
                supported = ", ".join(sorted(self.SHORTCUTS.keys()))
                return ToolResult(
                    success=False,
                    data=None,
                    message=(
                        f"Unknown website shortcut '{site}'. "
                        f"Supported shortcuts: {supported}. "
                        "Alternatively, provide a full URL starting with 'http://' or 'https://'."
                    )
                )

            webbrowser.open(target_url)
            return ToolResult(
                success=True,
                data={
                    "site": site,
                    "url": target_url
                },
                message=f"Website '{target_url}' opened successfully."
            )
        except Exception as e:
            return ToolResult(
                success=False,
                data=None,
                message=f"Failed to open website '{site}': {str(e)}"
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
                    "site": {
                        "type": "string",
                        "description": (
                            "Website shortcut ('youtube', 'google', 'gmail', 'github') "
                            "or full URL starting with 'http://' or 'https://'."
                        )
                    }
                },
                "required": ["site"]
            }
        }


class SearchWebTool(BaseTool):
    """Tool that searches the web for real-time information and documentation."""
    name: str = "search_web"
    description: str = "Searches the web for real-time information and documentation."

    def run(
        self,
        query: str,
        site: str = "google",
        max_results: int = 5,
        **kwargs: Any
    ) -> ToolResult:
        """Searches Google or YouTube, opens browser, and retrieves live search snippets.

        Args:
            query: The search term, topic, or technical question to search for.
            site: Target platform, either 'google' or 'youtube' (default: 'google').
            max_results: Maximum number of search results to retrieve (default: 5).
            **kwargs: Extra keyword arguments.

        Returns:
            ToolResult: Execution outcome with formatted search summary or error details.
        """
        try:
            if not query or not isinstance(query, str) or not query.strip():
                return ToolResult(
                    success=False,
                    data=None,
                    message="query must be a non-empty string."
                )

            clean_query = query.strip()
            site_clean = (site or "google").strip().lower()
            if site_clean not in ("google", "youtube"):
                return ToolResult(
                    success=False,
                    data=None,
                    message=f"Unsupported search site '{site}'. Supported options: 'google', 'youtube'."
                )

            encoded_query = urllib.parse.quote_plus(clean_query)
            if site_clean == "youtube":
                target_url = f"https://www.youtube.com/results?search_query={encoded_query}"
            else:
                target_url = f"https://www.google.com/search?q={encoded_query}"

            # Open browser safely
            try:
                import webbrowser
                webbrowser.open(target_url)
            except Exception as browser_err:
                return ToolResult(
                    success=False,
                    data=None,
                    message=f"Failed to execute search: {str(browser_err)}"
                )

            # Retrieve real search snippets via DuckDuckGo
            results: List[Dict[str, Any]] = []
            summary = ""
            try:
                try:
                    from ddgs import DDGS
                except ImportError:
                    from duckduckgo_search import DDGS
                effective_query = f"site:youtube.com {clean_query}" if site_clean == "youtube" else clean_query
                results = list(DDGS().text(effective_query, max_results=max_results))
                if results:
                    summary = "\n\n".join([f"**{r.get('title', '')}**\n{r.get('body', '')}\n{r.get('href', '')}" for r in results])
            except Exception:
                pass

            data_payload = {
                "url": target_url,
                "site": site_clean,
                "summary": summary,
                "results": results,
            }

            msg = f"Found {len(results)} search results." if results else f"Opened search for '{clean_query}' on {site_clean}."
            if summary:
                msg = f"{msg}\n\n{summary}"

            return ToolResult(
                success=True,
                data=data_payload,
                message=msg
            )
        except Exception as exc:
            return ToolResult(
                success=False,
                data=None,
                message=f"Search failed: {str(exc)}"
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
                    "query": {
                        "type": "string",
                        "description": "The search query or keywords to search for."
                    },
                    "site": {
                        "type": "string",
                        "description": "Search platform ('google' or 'youtube').",
                        "enum": ["google", "youtube"],
                        "default": "google"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of search results to retrieve (default: 5).",
                        "default": 5
                    }
                },
                "required": ["query"]
            }
        }



class ClipboardReadTool(BaseTool):
    """Tool that retrieves the current text content from the system clipboard."""
    name: str = "clipboard_read"
    description: str = (
        "Reads and returns the current text content stored in the system clipboard. "
        "Takes no arguments."
    )

    def run(self, **kwargs: Any) -> ToolResult:
        """Reads text from the system clipboard.

        Args:
            **kwargs: Extra keyword arguments.

        Returns:
            ToolResult: The clipboard text content.
        """
        try:
            import pyperclip
            text = pyperclip.paste()
            return ToolResult(
                success=True,
                data={"text": text, "length": len(text) if text else 0},
                message="Clipboard content read successfully." if text else "Clipboard is currently empty."
            )
        except Exception as e:
            return ToolResult(
                success=False,
                data=None,
                message=f"Failed to read clipboard: {str(e)}"
            )

    def get_schema(self) -> Dict[str, Any]:
        """Returns JSON schema definition for LLM tool calling."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }


class ClipboardWriteTool(BaseTool):
    """Tool that copies text into the system clipboard."""
    name: str = "clipboard_write"
    description: str = (
        "Copies the given text into the system clipboard so it can be pasted elsewhere."
    )

    def run(self, text: Optional[str] = None, **kwargs: Any) -> ToolResult:
        """Copies text to the system clipboard.

        Args:
            text: The text string to copy into the clipboard.
            **kwargs: Extra keyword arguments.

        Returns:
            ToolResult: Execution outcome confirming clipboard write.
        """
        try:
            if text is None or not isinstance(text, str):
                return ToolResult(
                    success=False,
                    data=None,
                    message="text must be a string."
                )

            if not text.strip():
                return ToolResult(
                    success=False,
                    data=None,
                    message="The clipboard text is empty. What text would you like me to copy to the clipboard?"
                )

            import pyperclip
            pyperclip.copy(text)
            return ToolResult(
                success=True,
                data={"length": len(text)},
                message=f"Copied {len(text)} characters to clipboard."
            )
        except Exception as e:
            return ToolResult(
                success=False,
                data=None,
                message=f"Failed to copy to clipboard: {str(e)}"
            )

    def get_schema(self) -> Dict[str, Any]:
        """Returns JSON schema definition for LLM tool calling."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "The text string to copy into the clipboard."
                    }
                },
                "required": ["text"]
            }
        }


class SetVolumeTool(BaseTool):
    """Tool that adjusts the Windows master system audio volume."""
    name: str = "set_volume"
    description: str = (
        "Sets the Windows master audio volume to a specified percentage between 0 and 100."
    )

    @staticmethod
    def _set_volume_powershell(vol_int: int) -> Optional[int]:
        """Sets Windows master audio volume via PowerShell CoreAudio endpoint fallback."""
        try:
            scalar_val = float(vol_int) / 100.0
            ps_script = f"""
Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;

[Guid("5CDF2C82-841E-4546-9722-0CF74078229A"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
public interface IAudioEndpointVolume {{
    int RegisterControlChangeNotify(IntPtr pNotify);
    int UnregisterControlChangeNotify(IntPtr pNotify);
    int GetChannelCount(out int pnChannelCount);
    int SetMasterVolumeLevel(float fLevelDB, ref Guid pguidEventContext);
    int SetMasterVolumeLevelScalar(float fLevel, ref Guid pguidEventContext);
    int GetMasterVolumeLevel(out float pfLevelDB);
    int GetMasterVolumeLevelScalar(out float pfLevel);
}}

[Guid("D666063F-1587-4E43-81F1-B948E807363F"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
public interface IMMDevice {{
    int Activate(ref Guid id, int clsCtx, IntPtr activationParams, [MarshalAs(UnmanagedType.IUnknown)] out object ppInterface);
}}

[Guid("A95664D2-9614-4F35-A746-DE8DB63617E6"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
public interface IMMDeviceEnumerator {{
    int EnumAudioEndpoints(int dataFlow, int stateMask, out IntPtr ppDevices);
    int GetDefaultAudioEndpoint(int dataFlow, int role, out IMMDevice ppDevice);
}}

[ComImport, Guid("BCDE0395-E52F-467C-8E3D-C4579291692E")]
public class MMDeviceEnumeratorComObject {{ }}

public class AudioHelper {{
    public static float SetAndGetVolume(float level) {{
        var enumerator = (IMMDeviceEnumerator)(new MMDeviceEnumeratorComObject());
        IMMDevice dev;
        enumerator.GetDefaultAudioEndpoint(0, 1, out dev);
        var iid = new Guid("5CDF2C82-841E-4546-9722-0CF74078229A");
        object ep;
        dev.Activate(ref iid, 23, IntPtr.Zero, out ep);
        var vol = (IAudioEndpointVolume)ep;
        var guid = Guid.Empty;
        vol.SetMasterVolumeLevelScalar(level, ref guid);
        float current;
        vol.GetMasterVolumeLevelScalar(out current);
        return current;
    }}
}}
'@
[AudioHelper]::SetAndGetVolume({scalar_val})
"""
            res = subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_script],
                capture_output=True,
                text=True,
                timeout=8
            )
            if res.returncode == 0 and res.stdout.strip():
                try:
                    return round(float(res.stdout.strip()) * 100)
                except ValueError:
                    return vol_int
        except Exception:
            pass
        return None

    def run(self, level: int, **kwargs: Any) -> ToolResult:
        """Sets the system volume.

        Args:
            level: Target volume percentage between 0 and 100.
            **kwargs: Extra keyword arguments.

        Returns:
            ToolResult: Execution outcome with adjusted volume level.
        """
        try:
            if level is None:
                return ToolResult(
                    success=False,
                    data=None,
                    message="level parameter is required."
                )

            try:
                vol_int = int(level)
            except (ValueError, TypeError):
                return ToolResult(
                    success=False,
                    data=None,
                    message=f"Volume level must be an integer between 0 and 100, got '{level}'."
                )

            if vol_int < 0 or vol_int > 100:
                return ToolResult(
                    success=False,
                    data=None,
                    message=f"Volume level {vol_int} is out of bounds. Must be between 0 and 100."
                )

            # 1. Primary audio control via pycaw
            try:
                from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
                from comtypes import CLSCTX_ALL
                from ctypes import cast, POINTER

                device = None
                try:
                    device = AudioUtilities.GetSpeakers()
                except AttributeError:
                    device = AudioUtilities.get_speakers()

                if device:
                    scalar_val = float(vol_int) / 100.0
                    volume = None
                    if hasattr(device, "EndpointVolume") and device.EndpointVolume:
                        volume = device.EndpointVolume
                    elif hasattr(device, "Activate"):
                        interface = device.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                        volume = cast(interface, POINTER(IAudioEndpointVolume))
                    elif hasattr(device, "_dev") and hasattr(device._dev, "Activate"):
                        interface = device._dev.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                        volume = cast(interface, POINTER(IAudioEndpointVolume))

                    if volume is not None:
                        volume.SetMasterVolumeLevelScalar(scalar_val, None)
                        current_scalar = volume.GetMasterVolumeLevelScalar()
                        current_pct = round(current_scalar * 100)
                        return ToolResult(
                            success=True,
                            data={"volume_level": current_pct},
                            message=f"System volume set to {current_pct}%."
                        )
            except Exception:
                # pycaw failed or unavailable, fallback to native PowerShell audio endpoint
                pass

            # 2. Resilient native PowerShell CoreAudio endpoint fallback
            ps_pct = self._set_volume_powershell(vol_int)
            if ps_pct is not None:
                return ToolResult(
                    success=True,
                    data={"volume_level": ps_pct},
                    message=f"System volume set to {ps_pct}%."
                )

            return ToolResult(
                success=False,
                data=None,
                message="Failed to set volume: audio endpoint unavailable."
            )
        except Exception as e:
            return ToolResult(
                success=False,
                data=None,
                message=f"Failed to set volume: {str(e)}"
            )

    def get_schema(self) -> Dict[str, Any]:
        """Returns JSON schema definition for LLM tool calling."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "level": {
                        "type": "integer",
                        "description": "Volume percentage from 0 (mute) to 100 (maximum).",
                        "minimum": 0,
                        "maximum": 100
                    }
                },
                "required": ["level"]
            }
        }


class SetBrightnessTool(BaseTool):
    """Tool that adjusts the Windows screen display brightness."""
    name: str = "set_brightness"
    description: str = (
        "Sets the display screen brightness to a percentage between 0 and 100."
    )

    def run(self, level: int, **kwargs: Any) -> ToolResult:
        """Sets the screen brightness.

        Args:
            level: Target brightness percentage between 0 and 100.
            **kwargs: Extra keyword arguments.

        Returns:
            ToolResult: Execution outcome with adjusted brightness level.
        """
        try:
            if level is None:
                return ToolResult(
                    success=False,
                    data=None,
                    message="level parameter is required."
                )

            try:
                bright_int = int(level)
            except (ValueError, TypeError):
                return ToolResult(
                    success=False,
                    data=None,
                    message=f"Brightness level must be an integer between 0 and 100, got '{level}'."
                )

            if bright_int < 0 or bright_int > 100:
                return ToolResult(
                    success=False,
                    data=None,
                    message=f"Brightness level {bright_int} is out of bounds. Must be between 0 and 100."
                )

            import screen_brightness_control as sbc
            sbc.set_brightness(bright_int)
            curr = sbc.get_brightness()
            current_val = curr[0] if isinstance(curr, list) and curr else bright_int

            return ToolResult(
                success=True,
                data={"brightness_level": current_val},
                message=f"Screen brightness set to {current_val}%."
            )
        except Exception as e:
            return ToolResult(
                success=False,
                data=None,
                message=f"Failed to set screen brightness: {str(e)}"
            )

    def get_schema(self) -> Dict[str, Any]:
        """Returns JSON schema definition for LLM tool calling."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "level": {
                        "type": "integer",
                        "description": "Brightness percentage from 0 to 100.",
                        "minimum": 0,
                        "maximum": 100
                    }
                },
                "required": ["level"]
            }
        }


class LockScreenTool(BaseTool):
    """Tool that locks the Windows workstation immediately."""
    name: str = "lock_screen"
    description: str = (
        "Immediately locks the Windows workstation screen using Windows API. Takes no arguments."
    )

    def run(self, **kwargs: Any) -> ToolResult:
        """Locks the Windows workstation screen.

        Args:
            **kwargs: Extra keyword arguments.

        Returns:
            ToolResult: Result indicating lock operation status.
        """
        try:
            import ctypes
            res = ctypes.windll.user32.LockWorkStation()
            if res != 0:
                return ToolResult(
                    success=True,
                    data={"locked": True},
                    message="Windows workstation screen locked successfully."
                )
            else:
                return ToolResult(
                    success=False,
                    data={"locked": False},
                    message="LockWorkStation call failed."
                )
        except Exception as e:
            return ToolResult(
                success=False,
                data=None,
                message=f"Failed to lock workstation screen: {str(e)}"
            )

    def get_schema(self) -> Dict[str, Any]:
        """Returns JSON schema definition for LLM tool calling."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }


class BatteryTool(BaseTool):
    """Tool that inspects laptop battery charge and power connection status."""
    name: str = "battery"
    description: str = (
        "Retrieves battery charge percentage, charging/plugged-in status, and remaining time. "
        "Takes no arguments."
    )

    def run(self, **kwargs: Any) -> ToolResult:
        """Inspects system battery telemetry.

        Args:
            **kwargs: Extra keyword arguments.

        Returns:
            ToolResult: Battery telemetry details.
        """
        try:
            battery = psutil.sensors_battery()
            if battery is None:
                return ToolResult(
                    success=True,
                    data={
                        "percent": None,
                        "power_plugged": True,
                        "is_desktop": True,
                        "secsleft": None
                    },
                    message="No battery detected. Running on AC wall power (Desktop PC)."
                )

            status_str = "Plugged in (Charging)" if battery.power_plugged else "On Battery"
            secs = battery.secsleft if battery.secsleft != psutil.POWER_TIME_UNLIMITED else None
            mins_left = round(secs / 60) if secs is not None and secs > 0 else None

            data = {
                "percent": battery.percent,
                "power_plugged": battery.power_plugged,
                "status": status_str,
                "minutes_left": mins_left
            }
            return ToolResult(
                success=True,
                data=data,
                message=f"Battery level is {battery.percent}% ({status_str})."
            )
        except Exception as e:
            return ToolResult(
                success=False,
                data=None,
                message=f"Failed to inspect battery status: {str(e)}"
            )

    def get_schema(self) -> Dict[str, Any]:
        """Returns JSON schema definition for LLM tool calling."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
