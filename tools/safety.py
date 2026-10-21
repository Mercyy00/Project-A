"""
Safety guards and path validation for Jarvis system tools.
Author: Abhijit (System & Automation Engineer)
"""

import os
from pathlib import Path
from typing import List, Optional


# Forbidden system root prefixes on Windows (case-normalized)
_BLOCKED_DIRECTORIES: List[str] = [
    r"c:\windows",
    r"c:\program files",
    r"c:\program files (x86)",
    r"c:\programdata",
]

# Add platform-specific environment paths dynamically
for _env_key in ("SystemRoot", "WINDIR", "ProgramFiles", "ProgramFiles(x86)", "ProgramW6432", "ProgramData"):
    _val = os.environ.get(_env_key)
    if _val:
        _BLOCKED_DIRECTORIES.append(os.path.normcase(os.path.abspath(_val)))

# Designated project root directory (default: repo root)
_DEFAULT_PROJECT_DIR = str(Path(__file__).resolve().parent.parent)
_custom_project_dir: Optional[str] = None


def set_designated_project_dir(path: Optional[str]) -> None:
    """Sets or clears an explicit designated project directory for safe code inspection.

    Args:
        path: Absolute or relative directory path to designate, or None to reset.
    """
    global _custom_project_dir
    _custom_project_dir = os.path.realpath(path) if path else None


def get_designated_project_dir() -> str:
    """Returns the designated project directory (from custom setting, env vars, or repo root).

    Returns:
        str: Absolute path to the designated project directory.
    """
    if _custom_project_dir:
        return _custom_project_dir
    env_dir = os.environ.get("JARVIS_PROJECT_DIR") or os.environ.get("PROJECT_ROOT")
    if env_dir:
        return os.path.realpath(env_dir)
    return os.path.realpath(_DEFAULT_PROJECT_DIR)


def is_path_safe(path: str) -> bool:
    """Validates whether a given file or directory path is safe for access.

    Enforces security isolation:
    - Resolves symlinks and relative traversals ('..') using os.path.realpath.
    - Explicitly blocks sensitive Windows system paths (C:\\Windows, C:\\Program Files, etc.).
    - Detects directory traversal escape attempts (e.g. escaping workspace/ via '..').
    - Allows paths inside 'workspace/', 'workspace/projects/', 'projects/', or directories starting with 'temp_'.
    - Allows subpaths inside the designated project directory for codebase inspection and project management.

    Args:
        path: The file or directory path string to validate.

    Returns:
        bool: True if path is safe to access, False otherwise.
    """
    try:
        if not path or not isinstance(path, str):
            return False

        clean_path = path.strip()
        if not clean_path or "\x00" in clean_path:
            return False

        # Resolve path to eliminate '.' and '..' traversal tricks
        resolved = os.path.realpath(clean_path)
        norm_resolved = os.path.normcase(resolved)

        # 1. Block explicit dangerous system directories (C:\Windows, C:\Program Files, etc.)
        for blocked in _BLOCKED_DIRECTORIES:
            if norm_resolved == blocked or norm_resolved.startswith(blocked + os.sep) or (os.altsep and norm_resolved.startswith(blocked + os.altsep)):
                return False

        # Also check drive-agnostic Windows/Program Files prefixes
        drive, rest = os.path.splitdrive(norm_resolved)
        blocked_drive_roots = (
            "\\windows",
            "\\windows\\",
            "\\program files",
            "\\program files\\",
            "\\program files (x86)",
            "\\program files (x86)\\",
            "\\programdata",
            "\\programdata\\",
        )
        for blocked_root in blocked_drive_roots:
            if rest == blocked_root or rest.startswith(blocked_root if blocked_root.endswith("\\") else blocked_root + "\\"):
                return False

        # 2. Detect directory traversal escape out of workspace/ or temp_ sandbox
        norm_input = clean_path.replace("\\", "/").lower()
        if norm_input.startswith(("./workspace/", "workspace/")):
            # Must remain inside a workspace directory
            p = Path(resolved)
            if not any(parent.name.lower() == "workspace" for parent in p.parents) and p.name.lower() != "workspace":
                return False
        elif norm_input.startswith(("./temp_", "temp_")):
            p = Path(resolved)
            if not any(parent.name.lower().startswith("temp_") for parent in p.parents) and not p.name.lower().startswith("temp_"):
                return False

        p = Path(resolved)

        # 3. Allow paths inside workspace, workspace/projects, projects, or temp_
        for parent in p.parents:
            parent_name = parent.name.lower()
            if parent_name in ("workspace", "projects") or parent_name.startswith("temp_"):
                return True

        target_name = p.name.lower()
        if target_name in ("workspace", "projects"):
            return True
        if target_name.startswith("temp_") and (os.path.isdir(resolved) or not p.suffix or clean_path.endswith(("/", "\\"))):
            return True

        # 4. Allow paths inside the designated project directory (codebase inspection & projects)
        designated_dir = get_designated_project_dir()
        if designated_dir:
            norm_designated = os.path.normcase(designated_dir)
            # Ensure designated dir is not a drive root or system folder
            if norm_designated not in ("c:\\", "d:\\", "e:\\", "/", "\\"):
                if norm_resolved == norm_designated or norm_resolved.startswith(norm_designated + os.sep) or (os.altsep and norm_resolved.startswith(norm_designated + os.altsep)):
                    return True

        # Everything else outside is blocked
        return False

    except Exception:
        return False
