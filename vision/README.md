# Vision Module — Project Jarvis

**Owner**: Aryan (`feature/aryan-vision`)  
**Pair**: Pair C (Tools + Vision with Abhijit)  
**Role**: Computer Vision, Screen Understanding, Visual Automation & Code Diagnostics  

---

## 1. Overview

The `vision` module empowers Project Jarvis with autonomous visual perception and screen-level interactions:
- **Instant Screen Inspection**: High-resolution screen captures with automatic 1280px AI downsizing and active window cropping.
- **Multimodal Screen Intelligence**: Gemini first, with Groq vision failover when Gemini is unavailable or rate-limited.
- **Visual Error Diagnosis**: Automated error traceback detection, cause explanation, and actionable fixes.
- **Visual UI Control**: Visual button/control locating with high-DPI coordinate scaling and click dispatching.
- **Autonomous Look-Decide-Act Loop**: Multi-step visual task execution (`do_on_screen`) with safety kill-switch integration.
- **Live Code Explanation & Fixing**: Instant explanation and automated bug repair for code open on screen.
- **Ultra-low Latency Speed**: Sub-second follow-up response caching and active-window bounding.

All tools in this module subclass `BaseTool` (from `tools/base.py`) and export a `TOOLS` list in `vision/tools.py`. They are automatically discovered and loaded into `tools.registry.TOOL_REGISTRY` at runtime.

---

## 2. Implemented Tools & Functions (Complete Sprint Overview)

| Day / Milestone | Phase | Function / Tool | Description |
|-----------------|-------|-----------------|-------------|
| **Day 1 (18 Oct)** | Setup | `capture_hello_screenshot()` (`vision/hello_screenshot.py`) | Baseline verification capturing primary display with `mss`, saving to `temp_vision/hello.png`. |
| **Day 2 (19 Oct)** | Capture & Privacy | `take_screenshot()` (`vision/screen.py`)<br>`ScreenshotTool` (`vision/tools.py`) | Captures primary monitor or region, resizes to max 1280px wide (JPEG 70), retains 10 newest files, respects `VISION_PAUSED=1`. |
| **Day 3 (20 Oct)** | AI Description | `describe_screen()` (`vision/screen.py`)<br>`DescribeScreenTool` (`vision/tools.py`) | Multimodal desktop analysis using Gemini first, then Groq vision (`GROQ_VISION_MODEL`, default `qwen/qwen3.8-27b`) if Gemini is missing or fails. |
| **Day 4 (21 Oct)** | Error Diagnostics | `explain_screen_error()` (`vision/screen.py`)<br>`ExplainScreenErrorTool` (`vision/tools.py`) | Detects on-screen error dialogs/tracebacks, quotes error text, explains cause in 2 sentences, and provides a fix. Supports `region_hint` ('top half', 'bottom half', 'left half', 'right half'). |
| **Day 5 (22 Oct)** | Visual Click | `locate_element()` (`vision/screen.py`)<br>`ClickElementTool` (`vision/tools.py`) | Asks Gemini to locate UI elements as JSON, scales coordinates to real display pixels, and dispatches clicks through `tools.registry.execute_tool("click", ...)`. |
| **Day 6 (23 Oct)** | Look-Decide-Act | `do_on_screen()` (`vision/screen.py`)<br>`DoOnScreenTool` (`vision/tools.py`) | Autonomous visual loop repeating up to 5 steps toward a goal: screenshot $\to$ next action JSON $\to$ registry dispatch $\to$ 1s pause $\to$ stop on done or emergency kill switch (`tools.guard.is_stopped()`). |
| **Day 7 (24 Oct)** | Speed & Latency | `active_window=True`, screenshot reuse, timing logs | Optimizes capture by cropping to active foreground window (`pygetwindow`), reuses screenshots within 2 seconds for follow-up questions, and logs capture/prep/inference milliseconds. |
| **Day 8 (25 Oct)** | Code Intelligence | `explain_code_on_screen()` (`vision/screen.py`)<br>`ExplainCodeOnScreenTool` (`vision/tools.py`) | Reads visible code in editor/terminal. Explains logic line-by-line (`task='explain'`) or diagnoses syntax/logical bugs and outputs corrected code (`task='fix'`). |
| **Day 9 (26 Oct)** | Scaling Calibration | `run_scaling_test()` (`vision/test_scaling.py`) | Validates mouse coordinate landing accuracy at 100%, 125%, and 150% Windows DPI scaling across 5 screen calibration anchor points. |
| **Day 11 (28 Oct)** | Privacy & Hardening | Complete documentation & verification | Hardens privacy constraints, auto-cleans ephemeral cache, and validates security boundaries. |

---

## 3. Privacy, Security & Safety Controls

### 3.1 The `VISION_PAUSED` Privacy Switch
To protect sensitive user information (passwords, online banking, private conversations):
- Set the environment variable `VISION_PAUSED=1` in `.env` or the operating system.
- When active, every vision function (`take_screenshot`, `describe_screen`, `explain_screen_error`, `locate_element`, `do_on_screen`, `explain_code_on_screen`) immediately aborts with a `PermissionError`.
- All vision tools return a structured `ToolResult(success=False, message="Screen capture is currently paused by user privacy mode (VISION_PAUSED=1).")` without capturing or transmitting any screen data.

### 3.2 Privacy Notice
> **Important Privacy Notice**: Screenshots processed by multimodal vision functions are transmitted securely over TLS to Google Gemini or Groq, depending on which provider succeeds.
> - **Always minimize or close** banking portals, credential managers, confidential emails, and sensitive documents before requesting vision analysis.
> - Use `active_window=True` or `region_hint` to restrict the capture strictly to the intended application window.
> - Toggle `VISION_PAUSED=1` whenever confidential materials are present.

### 3.3 Ephemeral File Storage
- Captured images are temporarily stored in `temp_vision/`.
- `clean_temp_vision(keep_newest=10)` automatically trims older captures so that no more than 10 recent images remain on disk.
- `temp_vision/` and all image files (`*.jpg`, `*.png`) are strictly excluded in `.gitignore` to prevent any image data from being committed to Git.

### 3.4 Emergency Kill-Switch Integration
- The look-decide-act loop (`do_on_screen`) checks `tools.guard.is_stopped()` before every step.
- Pressing the global emergency hotkey (`Ctrl+Alt+Q`) immediately aborts the loop within 1 second.

---

## 4. High-DPI & Display Scaling Support

On Windows systems with display scaling (125%, 150%, 175%, 200%):
- At import time, `vision/screen.py` invokes `ctypes.windll.shcore.SetProcessDpiAwareness(2)` (Per-Monitor DPI Aware V2).
- Coordinates returned by Gemini on the resized image (max 1280px width) are scaled to real display pixels:
  $$\text{real\_x} = \text{monitor\_left} + \left\lfloor x_{\text{model}} \times \frac{\text{orig\_width}}{\text{image\_width}} \right\rfloor$$
  $$\text{real\_y} = \text{monitor\_top} + \left\lfloor y_{\text{model}} \times \frac{\text{orig\_height}}{\text{image\_height}} \right\rfloor$$
- To verify coordinate precision on your display, run:
  ```powershell
  python vision/test_scaling.py --auto
  ```

---

## 5. Usage Examples

### 5.1 Python API
```python
from vision.screen import (
    take_screenshot,
    describe_screen,
    explain_screen_error,
    locate_element,
    do_on_screen,
    explain_code_on_screen,
)

# 1. Capture screen cropped to active window
path = take_screenshot(active_window=True)
print("Saved to:", path)

# 2. Describe screen contents with Gemini
description = describe_screen("What application is open in the foreground?")
print("Jarvis Vision:", description)

# 3. Diagnose visible error
error_report = explain_screen_error()
print("Error Diagnosis:", error_report)

# 4. Locate and get coordinates of a button
btn_loc = locate_element("blue Submit button")
if btn_loc["found"]:
    print(f"Target found at: ({btn_loc['x']}, {btn_loc['y']})")

# 5. Autonomous look-decide-act loop
summary = do_on_screen("open the File menu in Notepad", max_steps=3)
print("Actions performed:\n", summary)

# 6. Read and fix visible code
code_fixes = explain_code_on_screen(task="fix")
print("Code Diagnosis & Fixes:\n", code_fixes)
```

### 5.2 Via Tool Registry Dispatch
```python
import tools.registry as registry

# 1. Click element
res_click = registry.execute_tool("click_element", {"description": "File menu in Notepad"})
print(res_click.message)

# 2. Autonomous screen goal
res_loop = registry.execute_tool("do_on_screen", {"goal": "scroll down the page", "max_steps": 2})
print(res_loop.message)

# 3. Code explanation
res_code = registry.execute_tool("explain_code_on_screen", {"task": "explain"})
print(res_code.message)
```

---

## 6. Troubleshooting Table

| Issue / Error | Likely Cause | Solution |
|---------------|--------------|----------|
| `PermissionError: Screen capture is currently paused...` | `VISION_PAUSED=1` is set in `.env` | Set `VISION_PAUSED=0` or unset it in `.env` to resume vision. |
| `GEMINI_API_KEY is missing or invalid and GROQ_API_KEY is missing or invalid` | No vision provider credentials | Add `GEMINI_API_KEY` or `GROQ_API_KEY` to `.env`; set `GROQ_VISION_MODEL` only if you need a different supported image model. |
| `ScreenShotError: BitBlt failed` | Thread desktop access restricted on Windows | `_ensure_desktop_access()` binds desktop handles automatically; ensure the Windows session is unlocked. |
| Click misses target on high-DPI display | Coordinate scaling mismatch | Run `python vision/test_scaling.py` to confirm calibration; ensure display scaling is set to standard 100%, 125%, or 150%. |
| `do_on_screen` stops early | Model reached goal or emergency stop triggered | Check the returned step log: model outputs `done` when goal is reached or halts if kill switch is triggered. |
