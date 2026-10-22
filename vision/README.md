# Vision Module — Project Jarvis

**Owner**: Aryan (`feature/aryan-vision`)  
**Pair**: Pair C (Tools + Vision with Abhijit)  
**Role**: Computer Vision, Screen Understanding & Visual Automation  

---

## 1. Overview

The `vision` module provides Project Jarvis with the ability to see and understand the user's desktop, diagnose on-screen errors, locate UI buttons and menu items visually, and trigger mouse clicks through the system tool registry.

All tools in this module subclass `BaseTool` (from `tools/base.py`) and export a `TOOLS` list in `vision/tools.py`. They are automatically discovered and loaded into `tools.registry.TOOL_REGISTRY` at runtime.

---

## 2. Implemented Tools & Functions (Up to 22 October 2026)

| Date | Phase | Function / Tool | Description |
|------|-------|-----------------|-------------|
| **18 Oct (Day 1)** | Setup | `capture_hello_screenshot()` (`vision/hello_screenshot.py`) | Baseline verification capturing primary display with `mss`, saving to `temp_vision/hello.png`. |
| **19 Oct (Day 2)** | Capture & Privacy | `take_screenshot()` (`vision/screen.py`)<br>`ScreenshotTool` (`vision/tools.py`) | Captures primary monitor or region, resizes to max 1280px wide (JPEG 70), retains 10 newest files, respects `VISION_PAUSED=1`. |
| **20 Oct (Day 3)** | AI Description | `describe_screen()` (`vision/screen.py`)<br>`DescribeScreenTool` (`vision/tools.py`) | Multimodal desktop analysis using Google Gemini (`gemini-2.5-flash`), answering questions about open windows, code, or dialogs. |
| **21 Oct (Day 4)** | Error Diagnostics | `explain_screen_error()` (`vision/screen.py`)<br>`ExplainScreenErrorTool` (`vision/tools.py`) | Captures the screen, detects traceback/error dialogs, quotes the error exactly, explains cause in 2 sentences, and suggests a fix. Supports `region_hint` ('top half', 'bottom half', 'left half', 'right half'). |
| **22 Oct (Day 5)** | Visual Click | `locate_element()` (`vision/screen.py`)<br>`ClickElementTool` (`vision/tools.py`) | Prompts Gemini to detect UI element coordinates as JSON, scales coordinates back to native display pixels, and executes Abhijit's `click` tool via `tools.registry.execute_tool`. |

---

## 3. Privacy & Safety Controls

### 3.1 The `VISION_PAUSED` Privacy Switch
To protect sensitive user information (passwords, online banking, personal chat logs):
- Set the environment variable `VISION_PAUSED=1` in `.env` or system environment.
- When active, all vision functions (`take_screenshot`, `describe_screen`, `explain_screen_error`, `locate_element`) immediately raise a `PermissionError` and all vision tools return a safe error `ToolResult` without capturing or transmitting any images.

### 3.2 Privacy Advisory
> **Warning**: Screenshots analyzed by `describe_screen`, `explain_screen_error`, or `locate_element` are transmitted over TLS to the Google Gemini multimodal API for inference.
> - Always close banking tabs, credential managers, and sensitive documents before requesting screen analysis.
> - Set `VISION_PAUSED=1` when working with confidential materials.

### 3.3 Ephemeral File Storage
- Captured screenshots are stored in `temp_vision/`.
- `clean_temp_vision(keep_newest=10)` automatically deletes older screenshots to conserve disk space and prevent sensitive visual data accumulation.
- `temp_vision/` is ignored in Git (`.gitignore`).

---

## 4. High-DPI & Display Scaling Support

On Windows, high-DPI displays (125%, 150%, 200% scaling) can cause mismatches between mouse automation coordinates and pixel buffers.
- At module import time in `vision/screen.py`, `ctypes.windll.shcore.SetProcessDpiAwareness(2)` (Per-Monitor DPI Aware V2) is invoked.
- Coordinates returned by Gemini on the resized image (max 1280px width) are scaled back to native monitor pixels in `locate_element`:
  $$\text{real\_x} = \text{monitor\_left} + \left\lfloor x_{\text{model}} \times \frac{\text{orig\_width}}{\text{image\_width}} \right\rfloor$$
  $$\text{real\_y} = \text{monitor\_top} + \left\lfloor y_{\text{model}} \times \frac{\text{orig\_height}}{\text{image\_height}} \right\rfloor$$

---

## 5. Usage Examples

### 5.1 Python API
```python
from vision.screen import take_screenshot, describe_screen, explain_screen_error, locate_element

# 1. Capture screen
path = take_screenshot(region_hint="top half")
print("Saved to:", path)

# 2. Describe screen with Gemini
answer = describe_screen("What application is open in the foreground?")
print("Jarvis Vision:", answer)

# 3. Diagnose visible error
error_report = explain_screen_error()
print("Error Diagnosis:", error_report)

# 4. Locate button
loc = locate_element("blue Submit button")
if loc["found"]:
    print(f"Element at: ({loc['x']}, {loc['y']})")
```

### 5.2 Via Tool Registry
```python
import tools.registry as registry

# Execute through dynamic registry
res = registry.execute_tool("click_element", {"description": "File menu in Notepad"})
print(res.message)
```

---

## 6. Troubleshooting Table

| Issue / Error | Likely Cause | Solution |
|---------------|--------------|----------|
| `PermissionError: Screen capture is currently paused...` | `VISION_PAUSED=1` is set in `.env` | Set `VISION_PAUSED=0` or remove it from `.env` to resume vision. |
| `ValueError: GEMINI_API_KEY is missing or invalid` | No valid API key provided | Add a valid Google Gemini API key to `.env` as `GEMINI_API_KEY=AIzaSy...` |
| `ScreenShotError: BitBlt failed` | Thread desktop access restricted on Windows | `_ensure_desktop_access()` handles desktop binding automatically; ensure user session is active (not locked). |
| Click misses target on high-DPI display | Non-aware process coordinate offset | Ensure Windows DPI awareness call ran; test scaling with `test_scaling.py`. |
| `Could not find UI element: '...'` | Element off-screen or description vague | Make description more specific (e.g., 'upper-left File menu' instead of 'File'). |
