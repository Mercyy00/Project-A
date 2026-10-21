"""Day 1 Hello Screenshot Utility for Project Jarvis (Aryan).

Captures the primary monitor using mss, saves the image to temp_vision/hello.png,
prints image dimensions, and prints a reminder for .gitignore configuration.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
import sys
from typing import Tuple

import mss
from PIL import Image

logger = logging.getLogger(__name__)

TEMP_VISION_DIR = Path("temp_vision")


def _ensure_desktop_access() -> None:
    """Ensure the current thread has access to the active desktop on Windows."""
    if os.name == "nt":
        try:
            import ctypes
            user32 = ctypes.windll.user32
            # 0x01FF = DESKTOP_ALL_ACCESS
            hdesk = user32.OpenInputDesktop(0, False, 0x01FF)
            if hdesk:
                user32.SetThreadDesktop(hdesk)
        except Exception as exc:
            logger.debug("Failed to set thread desktop access: %s", exc)


def capture_hello_screenshot() -> Tuple[str, Tuple[int, int]]:
    """Capture a baseline screenshot of the primary monitor and save to temp_vision/hello.png.

    Returns:
        Tuple of (file_path_str, (width, height)).

    Raises:
        RuntimeError: If screen capture or image writing fails.
    """
    try:
        _ensure_desktop_access()
        TEMP_VISION_DIR.mkdir(parents=True, exist_ok=True)
        target_path = TEMP_VISION_DIR / "hello.png"

        with mss.MSS() as sct:
            primary_monitor = sct.monitors[1]
            sct_img = sct.grab(primary_monitor)
            img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
            img.save(target_path, format="PNG")
            size = (img.width, img.height)

        print(f"[SUCCESS] Screenshot saved to: {target_path}")
        print(f"[INFO] Image resolution: {size[0]}x{size[1]}")
        print("[REMINDER] Ask Jayesh to add temp_vision/ to .gitignore")

        return str(target_path), size

    except Exception as exc:
        logger.exception("Failed to capture hello screenshot: %s", exc)
        raise RuntimeError(f"Failed to capture hello screenshot: {exc}") from exc


if __name__ == "__main__":
    try:
        path, dimensions = capture_hello_screenshot()
        sys.exit(0)
    except Exception as err:
        print(f"[ERROR] {err}", file=sys.stderr)
        sys.exit(1)
