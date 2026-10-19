"""
Safety guards and path validation for Jarvis system tools.
Author: Abhijit (System & Automation Engineer)
"""

import os
from pathlib import Path
from typing import List


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


def is_path_safe(path: str) -> bool:
    """Validates whether a given file or directory path is safe for access.

    Enforces security isolation:
    - Resolves symlinks and relative traversals ('..') using os.path.realpath.
    - Explicitly blocks sensitive Windows system paths (C:\\Windows, C:\\Program Files, etc.).
    - Only allows paths located inside 'workspace/' or directories starting with 'temp_'.

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

        # 2. Allow only paths inside workspace/ or folders starting with temp_
        p = Path(resolved)

        # Check ancestor directories (parents)
        for parent in p.parents:
            parent_name = parent.name.lower()
            if parent_name == "workspace" or parent_name.startswith("temp_"):
                return True

        # Check if the target itself is a directory named workspace or starting with temp_
        target_name = p.name.lower()
        if target_name == "workspace":
            return True
        if target_name.startswith("temp_") and (os.path.isdir(resolved) or not p.suffix or clean_path.endswith(("/", "\\"))):
            return True

        # Everything else outside is blocked
        return False

    except Exception:
        return False
