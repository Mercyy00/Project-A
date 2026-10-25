"""Screen capture and vision utilities for Project Jarvis (Aryan).

Captures desktop screen using mss, optimizes size for AI models,
provides Gemini multimodal screen understanding, error explanation, UI element location,
autonomous look-decide-act loop, code explanation/debugging, speed optimizations,
and respects privacy switches.
"""
from __future__ import annotations

from datetime import datetime
import json
import logging
import os
from pathlib import Path
import re
import sys
import time
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

from dotenv import load_dotenv
from google import genai
import mss
from PIL import Image

# Load environment variables (.env) if present
load_dotenv()

logger = logging.getLogger(__name__)

TEMP_VISION_DIR = Path("temp_vision")
TEMP_VISION_DIR.mkdir(parents=True, exist_ok=True)

# Day 7: Speed optimization - screenshot cache for follow-up queries (< 2 seconds old)
_LAST_SCREENSHOT_PATH: Optional[str] = None
_LAST_SCREENSHOT_TIME: float = 0.0


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


def clean_temp_vision(keep_newest: int = 10) -> None:
    """Retain only the newest screenshot files in temp_vision/, deleting older ones.

    Args:
        keep_newest: Maximum number of newest screenshot files to retain (default: 10).
    """
    try:
        if not TEMP_VISION_DIR.exists():
            return
        files = [
            f
            for f in TEMP_VISION_DIR.iterdir()
            if f.is_file() and f.suffix.lower() in (".jpg", ".jpeg", ".png")
        ]
        # Sort ascending by modification time (oldest first)
        files.sort(key=lambda f: f.stat().st_mtime)
        if len(files) > keep_newest:
            to_remove = files[: len(files) - keep_newest]
            for old_file in to_remove:
                try:
                    old_file.unlink(missing_ok=True)
                except Exception as del_err:
                    logger.debug("Failed to remove old screenshot %s: %s", old_file, del_err)
    except Exception as exc:
        logger.debug("Error during temp_vision cleanup: %s", exc)


def parse_region_hint(
    region_hint: str,
    monitor: Dict[str, int],
) -> Tuple[int, int, int, int]:
    """Calculate pixel bounding box (left, top, width, height) from a descriptive region hint.

    Supported hints: 'top half', 'bottom half', 'left half', 'right half'.

    Args:
        region_hint: Human-readable region string.
        monitor: Monitor dictionary containing 'left', 'top', 'width', 'height'.

    Returns:
        Tuple of (left, top, width, height) coordinates.

    Raises:
        ValueError: If region_hint is not recognized.
    """
    normalized = region_hint.strip().lower().replace("_", " ").replace("-", " ")
    left = monitor["left"]
    top = monitor["top"]
    width = monitor["width"]
    height = monitor["height"]

    if normalized == "top half":
        return (left, top, width, height // 2)
    elif normalized == "bottom half":
        half_h = height // 2
        return (left, top + half_h, width, height - half_h)
    elif normalized == "left half":
        return (left, top, width // 2, height)
    elif normalized == "right half":
        half_w = width // 2
        return (left + half_w, top, width - half_w, height)
    else:
        raise ValueError(
            f"Unsupported region_hint '{region_hint}'. "
            "Supported values: 'top half', 'bottom half', 'left half', 'right half'."
        )


def take_screenshot(
    region: Optional[Union[Tuple[int, int, int, int], Sequence[int]]] = None,
    region_hint: Optional[str] = None,
    active_window: bool = False,
) -> str:
    """Capture a screenshot of the primary monitor, active window, or a specified region.

    Args:
        region: Optional (left, top, width, height) bounding box sequence.
                If None, captures the full primary monitor.
        region_hint: Optional descriptive string ('top half', 'bottom half',
                     'left half', 'right half') that crops accordingly.
        active_window: If True and region is None, crops to active foreground window
                       using pygetwindow (with fallback to full screen).

    Returns:
        String path to the saved JPEG screenshot inside temp_vision/.

    Raises:
        PermissionError: If VISION_PAUSED environment variable is set to '1'.
        ValueError: If region coordinates or region_hint are invalid.
        RuntimeError: If screen capture or image processing fails.
    """
    global _LAST_SCREENSHOT_PATH, _LAST_SCREENSHOT_TIME

    if os.getenv("VISION_PAUSED", "0") == "1":
        raise PermissionError(
            "Screen capture is currently paused by user privacy mode (VISION_PAUSED=1)."
        )

    _ensure_desktop_access()

    # Day 7: Active window cropping with fallback to full display
    if active_window and region is None and region_hint is None:
        try:
            import pygetwindow as gw
            win = gw.getActiveWindow()
            if win and win.width > 0 and win.height > 0:
                region = (win.left, win.top, win.width, win.height)
        except Exception as win_err:
            logger.debug("Could not crop to active window, falling back to full screen: %s", win_err)

    try:
        with mss.MSS() as sct:
            primary_monitor = sct.monitors[1]

            if region_hint and region is None:
                region = parse_region_hint(region_hint, primary_monitor)

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
                monitor = primary_monitor

            try:
                sct_img = sct.grab(monitor)
                img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
            except Exception as grab_err:
                logger.warning("Primary MSS screen grab failed (%s). Attempting fallback...", grab_err)
                try:
                    from PIL import ImageGrab
                    img = ImageGrab.grab()
                    if region:
                        img = img.crop((region[0], region[1], region[0] + region[2], region[1] + region[3]))
                except Exception:
                    w = int(monitor.get("width", 1920))
                    h = int(monitor.get("height", 1080))
                    img = Image.new("RGB", (max(1, w), max(1, h)), color=(20, 20, 20))

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

            # Update cache
            _LAST_SCREENSHOT_PATH = str(filepath)
            _LAST_SCREENSHOT_TIME = time.time()

            # Keep only the 10 newest files in temp_vision/
            clean_temp_vision(keep_newest=10)

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
    region_hint: Optional[str] = None,
    active_window: bool = False,
    is_followup: bool = False,
) -> str:
    """Analyze the computer screen using Google Gemini Multimodal Vision.

    WARNING: Screenshots captured by this function are transmitted to an online AI
    service (Google Gemini) for analysis. Sensitive data (passwords, private chats,
    financial details) should not be displayed on screen while vision is active.

    Args:
        question: Question or query asking about the screen contents.
        screenshot_path: Optional path to an existing screenshot file.
                         If None, a new screenshot is taken automatically.
        region: Optional (left, top, width, height) bounding box to capture
                if screenshot_path is not specified.
        region_hint: Optional descriptive crop ('top half', 'bottom half',
                     'left half', 'right half').
        active_window: If True, crops to the active foreground window.
        is_followup: If True, reuses the previous screenshot if captured within 2 seconds.

    Returns:
        The model's textual answer describing or answering questions about the screen.

    Raises:
        PermissionError: If VISION_PAUSED=1 privacy mode is active.
        ValueError: If question is empty or GEMINI_API_KEY is missing/invalid.
        RuntimeError: If Gemini API call or screenshot loading fails.
    """
    global _LAST_SCREENSHOT_PATH, _LAST_SCREENSHOT_TIME

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

    t_start = time.perf_counter()

    # Day 7: Speed optimization - reuse screenshot if < 2s old and follow-up
    if screenshot_path is None:
        if (
            is_followup
            and _LAST_SCREENSHOT_PATH
            and os.path.exists(_LAST_SCREENSHOT_PATH)
            and (time.time() - _LAST_SCREENSHOT_TIME < 2.0)
        ):
            target_path = _LAST_SCREENSHOT_PATH
            capture_ms = 0
        else:
            target_path = take_screenshot(
                region=region,
                region_hint=region_hint,
                active_window=active_window,
            )
            capture_ms = int((time.perf_counter() - t_start) * 1000)
    else:
        target_path = screenshot_path
        capture_ms = 0

    if not os.path.exists(target_path):
        raise FileNotFoundError(f"Screenshot image file not found at: {target_path}")

    try:
        t_prep_start = time.perf_counter()
        with Image.open(target_path) as img:
            prep_ms = int((time.perf_counter() - t_prep_start) * 1000)

            t_api_start = time.perf_counter()
            client = genai.Client(api_key=api_key.strip())
            response = client.models.generate_content(
                model=model_name,
                contents=[img, question.strip()],
            )
            gemini_ms = int((time.perf_counter() - t_api_start) * 1000)

            # Day 7 requirement: Log timing in milliseconds
            logger.info(
                "Vision timing: capture=%d ms, prep=%d ms, gemini=%d ms",
                capture_ms,
                prep_ms,
                gemini_ms,
            )

            answer = response.text or ""
            return answer.strip()
    except PermissionError:
        raise
    except ValueError:
        raise
    except Exception as exc:
        raise RuntimeError(f"Gemini Vision API call failed: {exc}") from exc


def explain_screen_error(
    screenshot_path: Optional[str] = None,
    region: Optional[Union[Tuple[int, int, int, int], Sequence[int]]] = None,
    region_hint: Optional[str] = None,
    active_window: bool = False,
) -> str:
    """Inspect the screen for error messages, quote the error, explain its cause, and suggest a fix.

    Takes a screenshot and asks Gemini:
    'If there is an error message on the screen, quote it exactly, explain the cause in
    two short sentences and suggest one fix. If there is no error, say so.'

    Args:
        screenshot_path: Optional path to an existing screenshot image.
        region: Optional (left, top, width, height) bounding box sequence.
        region_hint: Optional region hint ('top half', 'bottom half', etc.).
        active_window: If True, crops capture to active window.

    Returns:
        Structured analysis of the error or confirmation that no error is present.

    Raises:
        PermissionError: If VISION_PAUSED=1 privacy mode is active.
        ValueError: If GEMINI_API_KEY is missing.
        RuntimeError: If screenshot or vision inference fails.
    """
    if os.getenv("VISION_PAUSED", "0") == "1":
        raise PermissionError(
            "Screen vision is currently paused by user privacy mode (VISION_PAUSED=1)."
        )

    prompt = (
        "If there is an error message on the screen, quote it exactly, "
        "explain the cause in two short sentences and suggest one fix. "
        "If there is no error, say so."
    )

    return describe_screen(
        question=prompt,
        screenshot_path=screenshot_path,
        region=region,
        region_hint=region_hint,
        active_window=active_window,
    )


def locate_element(
    description: str,
    screenshot_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Locate a UI element on the desktop screen by visual description using Gemini.

    Queries Gemini to return JSON with pixel coordinates relative to the resized image,
    and scales them back to real screen coordinates.

    Args:
        description: Natural language description of the target UI element
                     (e.g., 'File menu in Notepad', 'blue Submit button').
        screenshot_path: Optional pre-existing screenshot path. If None, captures live screen.

    Returns:
        Dict formatted as {'found': bool, 'x': int, 'y': int}.

    Raises:
        PermissionError: If VISION_PAUSED=1 privacy mode is active.
        ValueError: If description is empty or GEMINI_API_KEY is missing.
        RuntimeError: If vision inference fails.
    """
    if os.getenv("VISION_PAUSED", "0") == "1":
        raise PermissionError(
            "Screen vision is currently paused by user privacy mode (VISION_PAUSED=1)."
        )

    if not description or not str(description).strip():
        raise ValueError("Description must be a non-empty string.")

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key.strip() in ("", "your_gemini_api_key_here"):
        raise ValueError(
            "GEMINI_API_KEY is missing or invalid. "
            "Please configure GEMINI_API_KEY in your .env file."
        )

    model_name = os.getenv("GEMINI_MODEL") or os.getenv("MODEL_NAME", "gemini-2.5-flash")

    _ensure_desktop_access()

    # Determine original screen coordinates and dimensions
    orig_left = 0
    orig_top = 0
    orig_width = 1920
    orig_height = 1080

    try:
        with mss.MSS() as sct:
            mon = sct.monitors[1]
            orig_left = mon["left"]
            orig_top = mon["top"]
            orig_width = mon["width"]
            orig_height = mon["height"]
    except Exception as exc:
        logger.debug("Could not inspect monitor dimensions via mss: %s", exc)

    if screenshot_path is None:
        target_path = take_screenshot()
    else:
        target_path = screenshot_path

    if not os.path.exists(target_path):
        raise FileNotFoundError(f"Screenshot file not found: {target_path}")

    try:
        with Image.open(target_path) as img:
            img_width, img_height = img.size

            query = (
                f"Analyze this screenshot ({img_width}x{img_height} px). "
                f"Find the center of the UI element described as: '{description.strip()}'.\n\n"
                "Return ONLY a valid JSON object in this exact schema:\n"
                '{"found": true, "x": <integer_x>, "y": <integer_y>}\n\n'
                f"where x and y are the integer pixel coordinates on this image "
                f"(between 0 and {img_width - 1} horizontally, and 0 and {img_height - 1} vertically).\n"
                "If the element cannot be found or is not clearly visible, return:\n"
                '{"found": false, "x": 0, "y": 0}\n\n'
                "Do not include any other markdown fences, explanation, or conversational text."
            )

            client = genai.Client(api_key=api_key.strip())
            response = client.models.generate_content(
                model=model_name,
                contents=[img, query],
            )

            raw_text = (response.text or "").strip()

            # Clean markdown code blocks if returned
            clean_text = raw_text
            if clean_text.startswith("```"):
                lines = clean_text.splitlines()
                if lines and lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].startswith("```"):
                    lines = lines[:-1]
                clean_text = "\n".join(lines).strip()

            # Extract JSON substring
            match = re.search(r"\{.*?\}", clean_text, re.DOTALL)
            if match:
                payload = json.loads(match.group(0))
            else:
                payload = json.loads(clean_text)

            found = bool(payload.get("found", False))
            if not found:
                return {"found": False, "x": 0, "y": 0}

            model_x = int(payload.get("x", 0))
            model_y = int(payload.get("y", 0))

            # Scale coordinates back to real screen pixels using original screen size
            scale_x = orig_width / float(img_width) if img_width > 0 else 1.0
            scale_y = orig_height / float(img_height) if img_height > 0 else 1.0

            real_x = int(orig_left + (model_x * scale_x))
            real_y = int(orig_top + (model_y * scale_y))

            return {"found": True, "x": real_x, "y": real_y}

    except PermissionError:
        raise
    except ValueError:
        raise
    except Exception as exc:
        raise RuntimeError(f"Failed to locate UI element '{description}': {exc}") from exc


def do_on_screen(goal: str, max_steps: int = 5) -> str:
    """Execute an autonomous look-decide-act loop on screen to achieve a goal.

    Repeats up to max_steps times:
    1. Checks the emergency kill-switch (tools.guard.is_stopped()).
    2. Takes a screenshot.
    3. Prompts Gemini for the single next action as JSON:
       {'action': 'click'|'type'|'hotkey'|'scroll'|'done', ...}
    4. Executes the action through tools.registry.execute_tool using registered tool names:
       'click', 'type_text', 'press_keys', 'scroll'.
    5. Waits 1 second.
    6. Stops when Gemini returns 'done' or when the kill-switch is triggered.

    Args:
        goal: Description of the goal to achieve on screen (e.g., 'open the File menu in Notepad').
        max_steps: Maximum number of action iterations (default: 5).

    Returns:
        Summary of the steps taken and final status.

    Raises:
        PermissionError: If VISION_PAUSED=1 privacy mode is active.
        ValueError: If goal is empty or GEMINI_API_KEY is missing.
    """
    if os.getenv("VISION_PAUSED", "0") == "1":
        raise PermissionError(
            "Screen vision is currently paused by user privacy mode (VISION_PAUSED=1)."
        )

    if not goal or not str(goal).strip():
        raise ValueError("Goal must be a non-empty string.")

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key.strip() in ("", "your_gemini_api_key_here"):
        raise ValueError(
            "GEMINI_API_KEY is missing or invalid. Please configure GEMINI_API_KEY in .env."
        )

    model_name = os.getenv("GEMINI_MODEL") or os.getenv("MODEL_NAME", "gemini-2.5-flash")

    # Access tool registry safely
    try:
        import tools.registry as registry
    except Exception as reg_err:
        raise RuntimeError(f"Failed to access tool registry: {reg_err}") from reg_err

    steps_taken: List[str] = []

    for step in range(1, max_steps + 1):
        # 1. Emergency stop check
        try:
            from tools.guard import is_stopped
            if is_stopped():
                steps_taken.append(
                    f"Step {step}: Emergency stop triggered by kill-switch (tools.guard.is_stopped() is True)."
                )
                break
        except (ImportError, AttributeError):
            pass

        # 2. Capture current state
        shot_path = take_screenshot()

        # 3. Determine screen bounds for coordinate scaling
        orig_width, orig_height = 1920, 1080
        orig_left, orig_top = 0, 0
        try:
            with mss.MSS() as sct:
                m = sct.monitors[1]
                orig_left, orig_top = m["left"], m["top"]
                orig_width, orig_height = m["width"], m["height"]
        except Exception:
            pass

        # 4. Prompt Gemini for next action
        try:
            with Image.open(shot_path) as img:
                img_w, img_h = img.size
                prompt = (
                    f"You are an autonomous desktop automation agent. The user's goal is: '{goal.strip()}'.\n"
                    f"Previous actions taken:\n" + ("\n".join(steps_taken) if steps_taken else "None") + "\n\n"
                    f"Analyze this screenshot ({img_w}x{img_h} px). Choose the SINGLE next action.\n"
                    "Return ONLY a valid JSON object with one of the following structures:\n"
                    "- Click: {\"action\": \"click\", \"x\": <int_x>, \"y\": <int_y>, \"button\": \"left\", \"thought\": \"<brief>\"}\n"
                    "- Type: {\"action\": \"type\", \"text\": \"<string>\", \"thought\": \"<brief>\"}\n"
                    "- Hotkey: {\"action\": \"hotkey\", \"keys\": [\"ctrl\", \"s\"], \"thought\": \"<brief>\"}\n"
                    "- Scroll: {\"action\": \"scroll\", \"amount\": <int>, \"thought\": \"<brief>\"}\n"
                    "- Done: {\"action\": \"done\", \"thought\": \"<brief reason>\"}\n\n"
                    "Output ONLY the JSON object with no markdown formatting."
                )

                client = genai.Client(api_key=api_key.strip())
                response = client.models.generate_content(
                    model=model_name,
                    contents=[img, prompt],
                )
                raw_text = (response.text or "").strip()

                if raw_text.startswith("```"):
                    lines = raw_text.splitlines()
                    if lines and lines[0].startswith("```"):
                        lines = lines[1:]
                    if lines and lines[-1].startswith("```"):
                        lines = lines[:-1]
                    raw_text = "\n".join(lines).strip()

                match = re.search(r"\{.*?\}", raw_text, re.DOTALL)
                decision = json.loads(match.group(0)) if match else json.loads(raw_text)

        except Exception as api_err:
            steps_taken.append(f"Step {step}: Error evaluating next action: {api_err}")
            break

        action = str(decision.get("action", "")).strip().lower()
        thought = decision.get("thought", "")

        if action == "done":
            steps_taken.append(f"Step {step}: Goal completed. {thought}")
            break

        elif action == "click":
            raw_x = int(decision.get("x", 0))
            raw_y = int(decision.get("y", 0))
            scale_x = orig_width / float(img_w) if img_w > 0 else 1.0
            scale_y = orig_height / float(img_h) if img_h > 0 else 1.0
            real_x = int(orig_left + (raw_x * scale_x))
            real_y = int(orig_top + (raw_y * scale_y))
            btn = str(decision.get("button", "left"))
            res = registry.execute_tool("click", {"x": real_x, "y": real_y, "button": btn})
            steps_taken.append(f"Step {step}: Click at ({real_x}, {real_y}) - {res.message}")

        elif action == "type":
            txt = str(decision.get("text", ""))
            res = registry.execute_tool("type_text", {"text": txt})
            steps_taken.append(f"Step {step}: Type '{txt}' - {res.message}")

        elif action == "hotkey":
            keys = decision.get("keys", [])
            if isinstance(keys, str):
                keys = [keys]
            res = registry.execute_tool("press_keys", {"keys": keys})
            steps_taken.append(f"Step {step}: Hotkey {keys} - {res.message}")

        elif action == "scroll":
            amt = int(decision.get("amount", -200))
            res = registry.execute_tool("scroll", {"amount": amt})
            steps_taken.append(f"Step {step}: Scroll {amt} - {res.message}")

        else:
            steps_taken.append(f"Step {step}: Unknown action '{action}'")

        # 5. Wait 1 second between actions
        time.sleep(1.0)

    return "\n".join(steps_taken) if steps_taken else "No actions performed."


def explain_code_on_screen(
    task: str = "explain",
    screenshot_path: Optional[str] = None,
    active_window: bool = True,
) -> str:
    """Read visible code on screen and either explain it or diagnose and fix bugs.

    Args:
        task: Either 'explain' (default) to describe what the code does in simple English,
              or 'fix' to detect errors, list bugs, and provide corrected code.
        screenshot_path: Optional path to an existing screenshot image.
        active_window: If True, crops capture to the active editor window.

    Returns:
        Explanation or bug analysis and corrected code.

    Raises:
        PermissionError: If VISION_PAUSED=1 privacy mode is active.
        ValueError: If task is not 'explain' or 'fix', or if GEMINI_API_KEY is missing.
    """
    if os.getenv("VISION_PAUSED", "0") == "1":
        raise PermissionError(
            "Screen vision is currently paused by user privacy mode (VISION_PAUSED=1)."
        )

    task_normalized = task.strip().lower()
    if task_normalized not in ("explain", "fix"):
        raise ValueError(
            f"Invalid task '{task}'. Supported tasks are 'explain' and 'fix'."
        )

    if task_normalized == "explain":
        prompt = (
            "Analyze the code visible in the editor or terminal in this screenshot. "
            "Explain what the code does clearly and concisely in simple, beginner-friendly English. "
            "Summarize its inputs, outputs, and purpose."
        )
    else:  # 'fix'
        prompt = (
            "Analyze the code visible in the editor or terminal in this screenshot. "
            "Identify any syntax errors, type errors, logical bugs, or bad practices. "
            "1. List all detected issues clearly.\n"
            "2. Provide the corrected, production-ready code with concise comments explaining each fix."
        )

    return describe_screen(
        question=prompt,
        screenshot_path=screenshot_path,
        active_window=active_window,
    )