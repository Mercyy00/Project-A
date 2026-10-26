"""Project JARVIS - Fast Smart Dependency Checker & Installer.

Ensures all requirements.txt dependencies are installed in the active environment.
Uses a cached hash stamp in venv/.requirements_hash to skip network queries
and achieve sub-second launch times once packages are installed.
"""

from __future__ import annotations

import hashlib
import os
import subprocess
import sys
from pathlib import Path


def check_and_install_dependencies(force: bool = False) -> bool:
    project_root = Path(__file__).resolve().parent.parent
    req_file = project_root / "requirements.txt"
    if not req_file.exists():
        return True

    current_hash = hashlib.md5(req_file.read_bytes()).hexdigest()
    stamp_file = project_root / "venv" / ".requirements_hash"

    # Fast cache path: if stamp matches and core modules import cleanly, skip pip!
    if not force and stamp_file.exists():
        try:
            if stamp_file.read_text(encoding="utf-8").strip() == current_hash:
                import uvicorn
                import fastapi
                import psutil
                import PyQt6
                return True
        except Exception:
            pass

    # Installation path: run pip install
    print("[*] Setting up dependencies from requirements.txt...")
    print("[*] (Using --prefer-binary for fast pre-compiled Windows wheels)...")
    cmd = [sys.executable, "-m", "pip", "install", "-r", str(req_file), "--prefer-binary"]
    res = subprocess.run(cmd)

    if res.returncode == 0:
        try:
            stamp_file.parent.mkdir(parents=True, exist_ok=True)
            stamp_file.write_text(current_hash, encoding="utf-8")
        except Exception:
            pass
        return True
    return False


if __name__ == "__main__":
    force = "--install" in sys.argv or "--update" in sys.argv
    success = check_and_install_dependencies(force=force)
    sys.exit(0 if success else 1)
