"""Screen capture and vision utilities for Project Jarvis (Aryan).

Captures desktop screen using mss, optimizes size for AI models,
provides Gemini multimodal screen understanding, and respects privacy switches.
"""
from __future__ import annotations

from datetime import datetime
import logging
import os
from pathlib import Path
from typing import Optional, Sequence, Tuple, Union

from dotenv import load_dotenv
from google import genai
import mss
from PIL import Image

# Load environment variables (.env) if present
load_dotenv()

logger = logging.getLogger(__name__)

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
        except Exception as exc:
            logger.debug("Failed to set thread desktop access: %s", exc)


def take_screenshot(
    region: Optional[Union[Tuple[int, int, int, int], Sequence[int]]] = None
) -> str:
    """Capture a screenshot of the primary monitor or a specified region.

    Args:
        region: Optional (left, top, width, height) bounding box sequence.
                If None, captures the full primary monitor.

    Returns:
        String path to the saved JPEG screenshot inside temp_vision/.

    Raises:
        PermissionError: If VISION_PAUSED environment variable is set to '1'.
        ValueError: If region coordinates are invalid.
        RuntimeError: If screen capture or image processing fails.
    """
    if os.getenv("VISION_PAUSED", "0") == "1":
        raise PermissionError(
            "Screen capture is currently paused by user privacy mode (VISION_PAUSED=1)."
        )

    _ensure_desktop_access()

    try:
        mss_factory = getattr(mss, "MSS", mss.mss)
        with mss_factory() as sct:
            if region:
                if len(region) != 4:
                    raise ValueError(
                        f"Region must have exactly 4 elements (left, top, width, height), got {region}"
                    )
                monitor = {
                    "left": int(region[0]),
                    "top": int(region[1]),
                    "width": int(region[2]),
                    "height": int(region[3]),
                }
            else:
                monitor = sct.monitors[1]  # Primary monitor

            sct_img = sct.grab(monitor)
            img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")

            # Resize to max 1280px wide for optimal AI token speed & network efficiency
            target_width = 1280
            if img.width > target_width:
                aspect_ratio = img.height / img.width
                target_height = max(1, int(target_width * aspect_ratio))
                img = img.resize((target_width, target_height), Image.Resampling.LANCZOS)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            filename = f"screenshot_{timestamp}.jpg"
            filepath = TEMP_VISION_DIR / filename

            # Save with 70% JPEG quality
            img.save(filepath, format="JPEG", quality=70, optimize=True)
            return str(filepath)
    except PermissionError:
        raise
    except ValueError:
        raise
    except Exception as exc:
        raise RuntimeError(f"Failed to capture screenshot: {exc}") from exc


def describe_screen(
    question: str,
    screenshot_path: Optional[str] = None,
    region: Optional[Union[Tuple[int, int, int, int], Sequence[int]]] = None,
) -> str:
    """Analyze the computer screen using Google Gemini Multimodal Vision.

    Sends the current screen (or region / provided screenshot) along with
    the user's question to the Gemini API and returns the textual description.

    Args:
        question: Question or query asking about the screen contents.
        screenshot_path: Optional path to an existing screenshot file.
                         If None, a new screenshot is taken automatically.
        region: Optional (left, top, width, height) bounding box to capture
                if screenshot_path is not specified.

    Returns:
        The model's textual answer describing or answering questions about the screen.

    Raises:
        PermissionError: If VISION_PAUSED=1 privacy mode is active.
        ValueError: If question is empty or GEMINI_API_KEY is missing/invalid.
        RuntimeError: If Gemini API call or screenshot loading fails.
    """
    if os.getenv("VISION_PAUSED", "0") == "1":
        raise PermissionError(
            "Screen vision is currently paused by user privacy mode (VISION_PAUSED=1)."
        )

    if not question or not str(question).strip():
        raise ValueError("Question must be a non-empty string.")

    # Validate Gemini API Key
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key.strip() in ("", "your_gemini_api_key_here"):
        raise ValueError(
            "GEMINI_API_KEY is missing or invalid. "
            "Please configure GEMINI_API_KEY in your .env file."
        )

    model_name = os.getenv("GEMINI_MODEL") or os.getenv("MODEL_NAME", "gemini-2.5-flash")

    # Acquire screenshot path
    if screenshot_path is None:
        target_path = take_screenshot(region=region)
    else:
        target_path = screenshot_path

    if not os.path.exists(target_path):
        raise FileNotFoundError(f"Screenshot image file not found at: {target_path}")

    try:
        with Image.open(target_path) as img:
            # Create Gemini Client and call models.generate_content
            client = genai.Client(api_key=api_key.strip())
            response = client.models.generate_content(
                model=model_name,
                contents=[img, question.strip()],
            )

            answer = response.text or ""
            return answer.strip()
    except PermissionError:
        raise
    except ValueError:
        raise
    except Exception as exc:
        raise RuntimeError(f"Gemini Vision API call failed: {exc}") from exc
