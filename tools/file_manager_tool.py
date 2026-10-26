"""
Windows File Manager and File Explorer Control Tool for JARVIS.
Author: Abhijit (System & Automation Engineer)

Provides complete control over Windows File Explorer and file system exploration:
1. List Drives: Discover all active disk drives (C:, D:, etc.) with total/free space.
2. Open Drives: Open any drive in Windows File Explorer.
3. Open Folders: Open any directory or special folders (Downloads, Desktop, Documents, etc.).
4. Search Folders: Search for folders by name across drives or directory trees.
5. Look at Folders: Inspect directory contents (subfolders, files, counts, sizes, timestamps).
6. Create Folders: Create new directories safely.
"""

from __future__ import annotations

import datetime
import fnmatch
import logging
import os
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

from tools.base import BaseTool, ToolResult

logger = logging.getLogger(__name__)

try:
    import psutil
    _PSUTIL_OK = True
except ImportError:
    _PSUTIL_OK = False

try:
    from tools.guard import is_stopped, log_action
except ImportError:
    def is_stopped() -> bool:
        return False

    def log_action(tool_name: str, args: Any, result_summary: Any) -> None:
        pass


def _format_size(size_bytes: int) -> str:
    """Formats raw bytes into human-readable string (KB, MB, GB)."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


class FileManagerTool(BaseTool):
    """Controls Windows File Explorer and explores drives, directories, and folders."""
    name: str = "file_manager_control"
    description: str = (
        "Controls Windows File Explorer and file system: list all disk drives, "
        "open physical drives (C:, D:), open folders, search for folders by name, "
        "look at / inspect folder contents (subfolders, files, sizes), and navigate directories."
    )

    # Standard user directory alias mappings
    _FOLDER_ALIASES: Dict[str, str] = {
        "downloads": os.path.expanduser(r"~\Downloads"),
        "download": os.path.expanduser(r"~\Downloads"),
        "desktop": os.path.expanduser(r"~\Desktop"),
        "documents": os.path.expanduser(r"~\Documents"),
        "docs": os.path.expanduser(r"~\Documents"),
        "pictures": os.path.expanduser(r"~\Pictures"),
        "photos": os.path.expanduser(r"~\Pictures"),
        "videos": os.path.expanduser(r"~\Videos"),
        "music": os.path.expanduser(r"~\Music"),
        "home": os.path.expanduser("~"),
        "user": os.path.expanduser("~"),
        "root": "C:\\",
        "c": "C:\\",
        "c:": "C:\\",
        "c drive": "C:\\",
        "d": "D:\\",
        "d:": "D:\\",
        "d drive": "D:\\",
    }

    def get_schema(self) -> Dict[str, Any]:
        """Returns JSON schema definition for LLM tool calling."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": [
                            "list_drives",
                            "open_drive",
                            "open_folder",
                            "look_at_folder",
                            "search_folders",
                            "create_folder",
                            "show_in_explorer",
                            "open_in_vscode",
                        ],
                        "description": "File manager action to perform.",
                    },
                    "drive": {
                        "type": "string",
                        "description": "Drive letter or name to open or query (e.g. 'C:', 'D:', 'C drive').",
                    },
                    "folder_path": {
                        "type": "string",
                        "description": "Path or folder alias to open or inspect (e.g. 'D:\\engineers', 'Downloads').",
                    },
                    "query": {
                        "type": "string",
                        "description": "Folder name or substring to search for.",
                    },
                    "root_path": {
                        "type": "string",
                        "description": "Root path or drive to start folder search from (e.g. 'D:\\', 'C:\\Users').",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum search results to return (default 25).",
                    },
                    "max_depth": {
                        "type": "integer",
                        "description": "Maximum directory depth when searching folders (default 4).",
                    },
                },
                "required": ["action"],
            },
        }

    # -------------------------------------------------------------------------
    # Helper Utilities
    # -------------------------------------------------------------------------

    @classmethod
    def resolve_path(cls, path_input: str) -> str:
        """Resolves user aliases, drive shortcuts, and environment variables into absolute path."""
        clean = (path_input or "").strip()
        if not clean:
            return os.getcwd()

        # Check direct aliases
        lower = clean.lower()
        if lower in cls._FOLDER_ALIASES:
            return cls._FOLDER_ALIASES[lower]

        # Check drive letter patterns like "c drive", "drive c", "c:"
        import re
        drive_m = re.match(r"^(?:open\s+)?(?:drive\s+)?([a-zA-Z]):?(?:\s+drive)?$", lower)
        if drive_m:
            return f"{drive_m.group(1).upper()}:\\"

        # Check expandvars and user expansion
        expanded = os.path.expandvars(os.path.expanduser(clean))
        if os.path.isabs(expanded):
            return os.path.normpath(expanded)

        # Relative to current working directory
        return os.path.normpath(os.path.abspath(expanded))

    @classmethod
    def _open_in_windows_explorer(cls, path: str, select: bool = False) -> bool:
        """Launches explorer.exe pointing to a path or selecting an item."""
        norm_path = os.path.normpath(path)
        try:
            if select:
                cmd = ["explorer.exe", f"/select,{norm_path}"]
            else:
                cmd = ["explorer.exe", norm_path]
            subprocess.Popen(cmd)
            return True
        except Exception as exc:
            logger.exception("Failed to open Explorer for '%s': %s", norm_path, exc)
            return False

    # -------------------------------------------------------------------------
    # Execution Dispatcher
    # -------------------------------------------------------------------------

    def run(self, **kwargs: Any) -> ToolResult:
        """Executes File Manager commands synchronously."""
        return self._execute_sync(**kwargs)

    async def execute(self, **kwargs: Any) -> ToolResult:
        """Executes File Manager commands asynchronously."""
        return self._execute_sync(**kwargs)

    def _execute_sync(self, **kwargs: Any) -> ToolResult:
        """Executes File Manager commands safely."""
        if is_stopped():
            return ToolResult(success=False, message="Action aborted: Emergency stop is active.")

        action = (kwargs.get("action") or "").lower().strip()
        drive = (kwargs.get("drive") or "").strip()
        folder_path = (kwargs.get("folder_path") or "").strip()
        query = (kwargs.get("query") or "").strip()
        root_path = (kwargs.get("root_path") or "").strip()
        max_results = kwargs.get("max_results", 25)
        max_depth = kwargs.get("max_depth", 4)

        logger.info(
            "Executing FileManager action '%s' (drive='%s', folder='%s', query='%s')",
            action, drive, folder_path, query
        )

        try:
            if action in ("list_drives", "drives", "show_drives"):
                return self._action_list_drives()
            elif action in ("open_drive", "drive"):
                target_drive = drive or folder_path or query
                return self._action_open_drive(target_drive)
            elif action in ("open_folder", "open", "explorer"):
                target_folder = folder_path or drive or query
                return self._action_open_folder(target_folder)
            elif action in ("look_at_folder", "inspect_folder", "list_folder", "view_folder"):
                target_folder = folder_path or drive or query
                return self._action_look_at_folder(target_folder)
            elif action in ("search_folders", "search_folder", "find_folder", "search"):
                search_q = query or folder_path or drive
                return self._action_search_folders(search_q, root_path, max_results, max_depth)
            elif action == "create_folder":
                return self._action_create_folder(folder_path or query)
            elif action == "show_in_explorer":
                target = folder_path or drive or query
                return self._action_show_in_explorer(target)
            elif action in ("open_in_vscode", "open_vscode", "vscode"):
                target = folder_path or drive or query or "."
                from tools.dev_tools import DevAgentTool
                return DevAgentTool().run(action="open_vscode", target=target)
            else:
                return ToolResult(
                    success=False,
                    message=f"Unknown File Manager action '{action}'. Valid actions include: "
                            "list_drives, open_drive, open_folder, look_at_folder, search_folders, create_folder, show_in_explorer, open_in_vscode.",
                )
        except Exception as exc:
            logger.exception("FileManager execution error for action '%s': %s", action, exc)
            return ToolResult(
                success=False,
                message=f"File Manager error: {str(exc)}",
                data={"action": action, "error": str(exc)},
            )

    # -------------------------------------------------------------------------
    # Core Actions
    # -------------------------------------------------------------------------

    def _action_list_drives(self) -> ToolResult:
        """Enumerates all drives on the machine with capacity and free space."""
        drives_info: List[Dict[str, Any]] = []

        if _PSUTIL_OK:
            try:
                for part in psutil.disk_partitions(all=False):
                    mount = part.mountpoint
                    try:
                        usage = psutil.disk_usage(mount)
                        drives_info.append({
                            "device": part.device,
                            "mountpoint": mount,
                            "fstype": part.fstype,
                            "total": _format_size(usage.total),
                            "used": _format_size(usage.used),
                            "free": _format_size(usage.free),
                            "percent_used": usage.percent,
                        })
                    except (PermissionError, OSError):
                        drives_info.append({
                            "device": part.device,
                            "mountpoint": mount,
                            "fstype": part.fstype,
                            "total": "N/A",
                            "free": "N/A",
                        })
            except Exception as exc:
                logger.debug("psutil drive enumeration error: %s", exc)

        # Fallback check standard Windows drive letters C..Z if psutil empty
        if not drives_info:
            for letter in "CDEFGHIJKLMNOPQRSTUVWXYZ":
                candidate = f"{letter}:\\"
                if os.path.exists(candidate):
                    drives_info.append({
                        "device": candidate,
                        "mountpoint": candidate,
                        "fstype": "NTFS/FAT",
                        "total": "Available",
                        "free": "Available",
                    })

        summary_lines = []
        for d in drives_info:
            mount = d.get("mountpoint") or d.get("device", "")
            free = d.get("free", "N/A")
            total = d.get("total", "N/A")
            pct = d.get("percent_used")
            pct_str = f" ({pct}% used)" if pct is not None else ""
            summary_lines.append(f"- Drive {mount}: {free} free of {total}{pct_str}")

        msg = f"Found {len(drives_info)} active drive(s):\n" + "\n".join(summary_lines)
        return ToolResult(
            success=True,
            message=msg,
            data={"action": "list_drives", "drives": drives_info, "count": len(drives_info)},
        )

    def _action_open_drive(self, drive_input: str) -> ToolResult:
        """Opens a drive in Windows File Explorer."""
        clean = (drive_input or "C").strip()
        resolved_path = self.resolve_path(clean)

        # Verify drive exists
        if not os.path.exists(resolved_path):
            # Attempt to append :\ if user just typed letter e.g. "D"
            if len(clean) == 1 and clean.isalpha():
                resolved_path = f"{clean.upper()}:\\"
            elif not os.path.exists(resolved_path):
                return ToolResult(
                    success=False,
                    message=f"Drive '{clean}' was not found or is inaccessible on this system.",
                    data={"action": "open_drive", "input": clean, "resolved": resolved_path},
                )

        opened = self._open_in_windows_explorer(resolved_path)
        if opened:
            return ToolResult(
                success=True,
                message=f"Opened Drive {resolved_path} in File Explorer.",
                data={"action": "open_drive", "path": resolved_path},
            )
        else:
            return ToolResult(
                success=False,
                message=f"Failed to open drive {resolved_path} in File Explorer.",
                data={"action": "open_drive", "path": resolved_path},
            )

    def _action_open_folder(self, folder_input: str) -> ToolResult:
        """Opens a directory in Windows File Explorer."""
        clean = (folder_input or ".").strip()
        resolved_path = self.resolve_path(clean)

        if not os.path.exists(resolved_path):
            return ToolResult(
                success=False,
                message=f"Directory '{clean}' does not exist (resolved: {resolved_path}).",
                data={"action": "open_folder", "input": folder_input, "resolved": resolved_path},
            )

        if os.path.isfile(resolved_path):
            # If path is a file, show it in explorer
            self._open_in_windows_explorer(resolved_path, select=True)
            return ToolResult(
                success=True,
                message=f"Highlighted file '{os.path.basename(resolved_path)}' in File Explorer.",
                data={"action": "open_folder", "path": resolved_path, "type": "file"},
            )

        opened = self._open_in_windows_explorer(resolved_path)
        if opened:
            return ToolResult(
                success=True,
                message=f"Opened folder '{os.path.basename(resolved_path) or resolved_path}' in File Explorer.",
                data={"action": "open_folder", "path": resolved_path},
            )
        else:
            return ToolResult(
                success=False,
                message=f"Failed to launch File Explorer for folder {resolved_path}.",
                data={"action": "open_folder", "path": resolved_path},
            )

    def _action_look_at_folder(self, folder_input: str) -> ToolResult:
        """Inspects folder contents: enumerates subdirectories, files, sizes, and timestamps."""
        clean = (folder_input or ".").strip()
        resolved_path = self.resolve_path(clean)

        if not os.path.exists(resolved_path):
            return ToolResult(
                success=False,
                message=f"Cannot inspect folder: '{clean}' does not exist (resolved: {resolved_path}).",
                data={"action": "look_at_folder", "resolved": resolved_path},
            )

        if not os.path.isdir(resolved_path):
            return ToolResult(
                success=False,
                message=f"Path '{resolved_path}' is a file, not a directory.",
                data={"action": "look_at_folder", "resolved": resolved_path},
            )

        subfolders: List[Dict[str, Any]] = []
        files: List[Dict[str, Any]] = []
        total_file_bytes: int = 0

        try:
            with os.scandir(resolved_path) as it:
                for entry in it:
                    try:
                        stat = entry.stat()
                        mtime_str = datetime.datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")
                        if entry.is_dir(follow_symlinks=False):
                            subfolders.append({
                                "name": entry.name,
                                "path": entry.path,
                                "modified": mtime_str,
                            })
                        elif entry.is_file(follow_symlinks=False):
                            size_bytes = stat.st_size
                            total_file_bytes += size_bytes
                            _, ext = os.path.splitext(entry.name)
                            files.append({
                                "name": entry.name,
                                "path": entry.path,
                                "size": _format_size(size_bytes),
                                "size_bytes": size_bytes,
                                "modified": mtime_str,
                                "extension": ext.lower(),
                            })
                    except (PermissionError, OSError):
                        continue
        except PermissionError:
            return ToolResult(
                success=False,
                message=f"Access denied reading folder '{resolved_path}'.",
                data={"action": "look_at_folder", "path": resolved_path},
            )

        # Sort subfolders and files alphabetically
        subfolders.sort(key=lambda x: x["name"].lower())
        files.sort(key=lambda x: x["name"].lower())

        # Build clean natural language summary
        folder_name = os.path.basename(resolved_path) or resolved_path
        msg_parts = [
            f"Folder '{folder_name}' ({resolved_path}):",
            f"Contains {len(subfolders)} subfolder(s) and {len(files)} file(s) (total file size: {_format_size(total_file_bytes)}).",
        ]

        if subfolders:
            subfolder_names = [f"📁 {s['name']}" for s in subfolders[:12]]
            if len(subfolders) > 12:
                subfolder_names.append(f"... and {len(subfolders) - 12} more")
            msg_parts.append("Subfolders: " + ", ".join(subfolder_names))

        if files:
            file_names = [f"📄 {f['name']} ({f['size']})" for f in files[:15]]
            if len(files) > 15:
                file_names.append(f"... and {len(files) - 15} more")
            msg_parts.append("Files:\n  " + "\n  ".join(file_names))

        return ToolResult(
            success=True,
            message="\n".join(msg_parts),
            data={
                "action": "look_at_folder",
                "path": resolved_path,
                "folder_name": folder_name,
                "subfolders_count": len(subfolders),
                "files_count": len(files),
                "total_file_bytes": total_file_bytes,
                "total_file_size": _format_size(total_file_bytes),
                "subfolders": subfolders,
                "files": files,
            },
        )

    def _action_search_folders(
        self,
        query: str,
        root_path: str = "",
        max_results: int = 25,
        max_depth: int = 4,
    ) -> ToolResult:
        """Searches for directories matching name pattern across given root or active drives."""
        clean_q = (query or "").strip().lower()
        if not clean_q:
            return ToolResult(
                success=False,
                message="Please provide a folder name or search query.",
                data={"action": "search_folders"},
            )

        # Determine roots to search
        roots_to_search: List[str] = []
        if root_path:
            resolved_root = self.resolve_path(root_path)
            if os.path.isdir(resolved_root):
                roots_to_search.append(resolved_root)
        else:
            # Current workspace, user home, and active drives
            roots_to_search.append(os.getcwd())
            home = os.path.expanduser("~")
            if home not in roots_to_search:
                roots_to_search.append(home)
            for d in ("D:\\", "C:\\"):
                if os.path.exists(d) and d not in roots_to_search:
                    roots_to_search.append(d)

        matches: List[Dict[str, Any]] = []

        # System directories to skip for speed and security
        skip_names = {
            "$recycle.bin", "system volume information", "windows", "winsxs",
            "node_modules", ".git", ".venv", "env", "__pycache__", "appdata",
        }

        for root in roots_to_search:
            if len(matches) >= max_results:
                break
            root_depth = root.rstrip(os.path.sep).count(os.path.sep)
            try:
                for dirpath, dirnames, _ in os.walk(root, topdown=True):
                    # Prune deep recursion
                    current_depth = dirpath.rstrip(os.path.sep).count(os.path.sep) - root_depth
                    if current_depth >= max_depth:
                        dirnames.clear()
                        continue

                    # Filter out system/noisy folders in-place
                    dirnames[:] = [d for d in dirnames if d.lower() not in skip_names and not d.startswith(".")]

                    for d in dirnames:
                        if clean_q in d.lower():
                            full_path = os.path.join(dirpath, d)
                            try:
                                mtime = datetime.datetime.fromtimestamp(os.path.getmtime(full_path)).strftime("%Y-%m-%d %H:%M")
                            except Exception:
                                mtime = "N/A"
                            matches.append({
                                "name": d,
                                "path": full_path,
                                "modified": mtime,
                            })
                            if len(matches) >= max_results:
                                dirnames.clear()
                                break
            except (PermissionError, OSError):
                continue

        if not matches:
            return ToolResult(
                success=True,
                message=f"No folders found matching '{clean_q}'.",
                data={"action": "search_folders", "query": clean_q, "matches": []},
            )

        match_lines = [f"- 📁 {m['name']} -> {m['path']}" for m in matches[:15]]
        if len(matches) > 15:
            match_lines.append(f"... and {len(matches) - 15} more matches")

        msg = f"Found {len(matches)} folder(s) matching '{clean_q}':\n" + "\n".join(match_lines)
        return ToolResult(
            success=True,
            message=msg,
            data={"action": "search_folders", "query": clean_q, "matches": matches, "count": len(matches)},
        )

    def _action_create_folder(self, folder_input: str) -> ToolResult:
        """Creates a new folder at the specified path."""
        clean = (folder_input or "").strip()
        if not clean:
            return ToolResult(success=False, message="Folder path/name cannot be empty.")

        resolved_path = self.resolve_path(clean)
        try:
            os.makedirs(resolved_path, exist_ok=True)
            return ToolResult(
                success=True,
                message=f"Created folder '{os.path.basename(resolved_path)}' at {resolved_path}.",
                data={"action": "create_folder", "path": resolved_path},
            )
        except Exception as exc:
            return ToolResult(
                success=False,
                message=f"Failed to create folder at {resolved_path}: {exc}",
                data={"action": "create_folder", "error": str(exc)},
            )

    def _action_show_in_explorer(self, target_input: str) -> ToolResult:
        """Highlights a file or folder in File Explorer."""
        resolved = self.resolve_path(target_input)
        if not os.path.exists(resolved):
            return ToolResult(success=False, message=f"Path '{resolved}' does not exist.")

        self._open_in_windows_explorer(resolved, select=True)
        return ToolResult(
            success=True,
            message=f"Selected '{os.path.basename(resolved)}' in Windows File Explorer.",
            data={"action": "show_in_explorer", "path": resolved},
        )
