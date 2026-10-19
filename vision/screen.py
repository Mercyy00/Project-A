"""Screen capture and vision utilities for Project Jarvis (Aryan).
Captures desktop screen using mss, optimizes size for AI models,
and respects privacy switches.
"""
from __future__ import annotations
from datetime import datetime
import os
from pathlib import Path
from typing import Optional, Tuple
import mss
from PIL import Image

TEMP_VISION_DIR = Path("temp_vision")
TEMP_VISION_DIR.mkdir(parents=True, exist_ok=True)


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
        except Exception:
            pass


def take_screenshot(region: Optional[Tuple[int, int, int, int]] = None) -> str:
    """Capture a screenshot of the primary monitor or a specified region.

    Args:
        region: Optional (left, top, width, height) bounding box.
                If None, captures full primary screen.

    Returns:
        Absolute or relative string path to the saved JPEG screenshot.

    Raises:
        PermissionError: If VISION_PAUSED environment variable is set to '1'.
        RuntimeError: If capture fails.
    """
    if os.getenv("VISION_PAUSED", "0") == "1":
        raise PermissionError("Screen capture is currently paused by user privacy mode (VISION_PAUSED=1).")

    _ensure_desktop_access()

    try:
        # Use mss.MSS or mss.mss for cross-version compatibility
        mss_factory = getattr(mss, "MSS", mss.mss)
        with mss_factory() as sct:
            if region:
                monitor = {
                    "left": region[0],
                    "top": region[1],
                    "width": region[2],
                    "height": region[3],
                }
            else:
                monitor = sct.monitors[1]  # Primary monitor

            sct_img = sct.grab(monitor)
            img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")

            # Resize to max 1280px wide for optimal AI token speed
            target_width = 1280
            if img.width > target_width:
                aspect_ratio = img.height / img.width
                target_height = int(target_width * aspect_ratio)
                img = img.resize((target_width, target_height), Image.Resampling.LANCZOS)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"screenshot_{timestamp}.jpg"
            filepath = TEMP_VISION_DIR / filename

            # Save with 70% JPEG quality
            img.save(filepath, format="JPEG", quality=70, optimize=True)
            return str(filepath)
    except Exception as exc:
        raise RuntimeError(f"Failed to capture screenshot: {exc}") from exc
