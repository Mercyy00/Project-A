"""Vision tools module for Project Jarvis (Aryan).

Implements ScreenshotTool, DescribeScreenTool, ExplainScreenErrorTool, ClickElementTool,
DoOnScreenTool, and ExplainCodeOnScreenTool compliant with BaseTool specification,
allowing automatic discovery and registration by the Jarvis Tool Registry.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Sequence

from tools.base import BaseTool, ToolResult
from vision.screen import (
    describe_screen,
    do_on_screen,
    explain_code_on_screen,
    explain_screen_error,
    locate_element,
    take_screenshot,
)

logger = logging.getLogger(__name__)


class ScreenshotTool(BaseTool):
    """Tool for capturing desktop screenshots for logging, user review, or inspection."""

    name: str = "take_screenshot"
    description: str = (
        "Captures a high-resolution screenshot of the user's primary monitor, active window, or a specific screen region. "
        "Saves the image into temp_vision/ and returns the file path. "
        "Useful for seeing the current state of apps, desktop, or errors."
    )

    def run(
        self,
        region: Optional[Sequence[int]] = None,
        region_hint: Optional[str] = None,
        active_window: bool = False,
        **kwargs: Any,
    ) -> ToolResult:
        """Capture a screenshot.

        Args:
            region: Optional bounding box [left, top, width, height] in pixels.
            region_hint: Optional descriptive region ('top half', 'bottom half', 'left half', 'right half').
            active_window: If True, crops capture to the currently active foreground window.
            **kwargs: Extra arguments (ignored).

        Returns:
            ToolResult containing the file path on success, or structured error message on failure.
        """
        try:
            if region is not None:
                if not isinstance(region, (list, tuple)) or len(region) != 4:
                    return ToolResult(
                        success=False,
                        data=None,
                        message="Invalid 'region' parameter: must be a list or tuple of 4 integers [left, top, width, height].",
                    )

            path = take_screenshot(region=region, region_hint=region_hint, active_window=active_window)
            return ToolResult(
                success=True,
                data={
                    "file_path": path,
                    "region": region,
                    "region_hint": region_hint,
                    "active_window": active_window,
                },
                message=f"Screenshot captured successfully and saved to: {path}",
            )
        except PermissionError as pe:
            return ToolResult(
                success=False,
                data=None,
                message=str(pe),
            )
        except ValueError as ve:
            return ToolResult(
                success=False,
                data=None,
                message=f"Invalid parameter: {ve}",
            )
        except Exception as exc:
            logger.exception("ScreenshotTool execution failed: %s", exc)
            return ToolResult(
                success=False,
                data=None,
                message=f"Failed to capture screenshot: {exc}",
            )

    def get_schema(self) -> Dict[str, Any]:
        """Returns JSON schema definition for LLM tool calling."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "region": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": "Optional [left, top, width, height] pixel coordinates to capture only a sub-region of the screen.",
                    },
                    "region_hint": {
                        "type": "string",
                        "description": "Optional region hint ('top half', 'bottom half', 'left half', 'right half') to crop the capture area.",
                    },
                    "active_window": {
                        "type": "boolean",
                        "description": "Optional boolean flag to crop specifically to the active window rectangle.",
                    },
                },
                "required": [],
            },
        }


class DescribeScreenTool(BaseTool):
    """Tool for analyzing desktop screen contents using Gemini Multimodal Vision."""

    name: str = "describe_screen"
    description: str = (
        "Inspects what is currently displayed on the desktop screen using AI vision. "
        "Answers questions about open applications, visible text, code errors, dialogs, or user interfaces."
    )

    def run(
        self,
        question: str = "What is currently visible on my screen?",
        screenshot_path: Optional[str] = None,
        region: Optional[Sequence[int]] = None,
        region_hint: Optional[str] = None,
        active_window: bool = False,
        is_followup: bool = False,
        **kwargs: Any,
    ) -> ToolResult:
        """Analyze desktop screen contents.

        Args:
            question: Question or analysis instructions for the AI vision model.
            screenshot_path: Optional path to an existing image file. If omitted, takes a live screenshot.
            region: Optional bounding box [left, top, width, height] to capture if screenshot_path is None.
            region_hint: Optional region hint ('top half', 'bottom half', 'left half', 'right half').
            active_window: If True, crops to active foreground window.
            is_followup: If True, reuses previous screenshot if under 2 seconds old.
            **kwargs: Extra arguments (ignored).

        Returns:
            ToolResult containing the visual analysis answer from Gemini.
        """
        try:
            if not question or not str(question).strip():
                return ToolResult(
                    success=False,
                    data=None,
                    message="Parameter 'question' is required and cannot be empty.",
                )

            answer = describe_screen(
                question=str(question).strip(),
                screenshot_path=screenshot_path,
                region=region,
                region_hint=region_hint,
                active_window=active_window,
                is_followup=is_followup,
            )

            return ToolResult(
                success=True,
                data={
                    "question": question,
                    "description": answer,
                    "screenshot_path": screenshot_path,
                    "region_hint": region_hint,
                    "active_window": active_window,
                    "is_followup": is_followup,
                },
                message=answer,
            )
        except PermissionError as pe:
            return ToolResult(
                success=False,
                data=None,
                message=str(pe),
            )
        except ValueError as ve:
            return ToolResult(
                success=False,
                data=None,
                message=f"Configuration error: {ve}",
            )
        except Exception as exc:
            logger.exception("DescribeScreenTool execution failed: %s", exc)
            return ToolResult(
                success=False,
                data=None,
                message=f"Failed to analyze screen: {exc}",
            )

    def get_schema(self) -> Dict[str, Any]:
        """Returns JSON schema definition for LLM tool calling."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "The specific question or instruction for analyzing the screen (e.g. 'What is on my screen?', 'Read the error dialog').",
                    },
                    "screenshot_path": {
                        "type": "string",
                        "description": "Optional file path to a previously saved screenshot. If omitted, captures current screen live.",
                    },
                    "region": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": "Optional [left, top, width, height] coordinates to limit capture to a specific screen area.",
                    },
                    "region_hint": {
                        "type": "string",
                        "description": "Optional region hint ('top half', 'bottom half', 'left half', 'right half') to crop the capture area.",
                    },
                    "active_window": {
                        "type": "boolean",
                        "description": "Optional boolean flag to crop specifically to the active foreground window.",
                    },
                    "is_followup": {
                        "type": "boolean",
                        "description": "Set to true for rapid follow-up questions to reuse recent screenshot (< 2s old) for ultra-low latency.",
                    },
                },
                "required": ["question"],
            },
        }


class ExplainScreenErrorTool(BaseTool):
    """Tool for inspecting desktop screen for errors and providing fixes."""

    name: str = "explain_screen_error"
    description: str = (
        "Inspects the desktop screen for error messages, stack traces, or exception dialogs. "
        "Quotes the error exactly, explains the cause in two short sentences, and suggests a fix."
    )

    def run(
        self,
        screenshot_path: Optional[str] = None,
        region: Optional[Sequence[int]] = None,
        region_hint: Optional[str] = None,
        active_window: bool = False,
        **kwargs: Any,
    ) -> ToolResult:
        """Inspect and explain visible errors on screen.

        Args:
            screenshot_path: Optional path to an existing image. If None, captures live screen.
            region: Optional [left, top, width, height] bounding box.
            region_hint: Optional region crop ('top half', 'bottom half', etc.).
            active_window: If True, crops capture to active window.
            **kwargs: Extra parameters (ignored).

        Returns:
            ToolResult containing the diagnosis and fix recommendations.
        """
        try:
            explanation = explain_screen_error(
                screenshot_path=screenshot_path,
                region=region,
                region_hint=region_hint,
                active_window=active_window,
            )

            return ToolResult(
                success=True,
                data={
                    "error_explanation": explanation,
                    "screenshot_path": screenshot_path,
                    "region_hint": region_hint,
                    "active_window": active_window,
                },
                message=explanation,
            )
        except PermissionError as pe:
            return ToolResult(
                success=False,
                data=None,
                message=str(pe),
            )
        except ValueError as ve:
            return ToolResult(
                success=False,
                data=None,
                message=f"Configuration error: {ve}",
            )
        except Exception as exc:
            logger.exception("ExplainScreenErrorTool execution failed: %s", exc)
            return ToolResult(
                success=False,
                data=None,
                message=f"Failed to explain screen error: {exc}",
            )

    def get_schema(self) -> Dict[str, Any]:
        """Returns JSON schema definition for LLM tool calling."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "screenshot_path": {
                        "type": "string",
                        "description": "Optional path to a previously saved screenshot file. If omitted, takes a live screenshot.",
                    },
                    "region": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": "Optional [left, top, width, height] screen region to inspect.",
                    },
                    "region_hint": {
                        "type": "string",
                        "description": "Optional region hint ('top half', 'bottom half', 'left half', 'right half').",
                    },
                    "active_window": {
                        "type": "boolean",
                        "description": "Optional boolean flag to crop capture to active window.",
                    },
                },
                "required": [],
            },
        }


class ClickElementTool(BaseTool):
    """Tool for visually finding a UI element or button on screen and clicking it."""

    name: str = "click_element"
    description: str = (
        "Locates a UI element, button, menu item, or icon on the screen by descriptive name "
        "using AI vision and clicks it using the system mouse control tool."
    )

    def run(
        self,
        description: str = "",
        button: str = "left",
        clicks: int = 1,
        **kwargs: Any,
    ) -> ToolResult:
        """Find a UI element by description and click it.

        Args:
            description: Description of the element to find and click (e.g., 'File menu', 'OK button').
            button: Mouse button ('left', 'right', 'middle'; default: 'left').
            clicks: Number of clicks (1 for single click, 2 for double click; default: 1).
            **kwargs: Extra arguments (ignored).

        Returns:
            ToolResult indicating click coordinates and execution status.
        """
        try:
            if not description or not str(description).strip():
                return ToolResult(
                    success=False,
                    data=None,
                    message="Parameter 'description' is required to locate and click a UI element.",
                )

            location = locate_element(description=str(description).strip())

            if not location.get("found", False):
                return ToolResult(
                    success=False,
                    data={"found": False, "description": description},
                    message=f"UI element '{description}' was not found on the screen.",
                )

            target_x = int(location["x"])
            target_y = int(location["y"])

            # Call Abhijit's registered click tool through tools.registry.execute_tool
            # As per project guidelines, we do not import his modules directly.
            import tools.registry as tool_registry

            click_args = {
                "x": target_x,
                "y": target_y,
                "button": button,
                "clicks": clicks,
            }

            click_res: ToolResult = tool_registry.execute_tool("click", click_args)

            if click_res.success:
                return ToolResult(
                    success=True,
                    data={
                        "found": True,
                        "description": description,
                        "x": target_x,
                        "y": target_y,
                        "button": button,
                        "clicks": clicks,
                        "action_result": click_res.data,
                    },
                    message=f"Successfully located '{description}' at ({target_x}, {target_y}) and clicked it.",
                )
            else:
                return ToolResult(
                    success=False,
                    data={
                        "found": True,
                        "description": description,
                        "x": target_x,
                        "y": target_y,
                    },
                    message=(
                        f"Located '{description}' at ({target_x}, {target_y}), "
                        f"but click action failed: {click_res.message}"
                    ),
                )

        except PermissionError as pe:
            return ToolResult(
                success=False,
                data=None,
                message=str(pe),
            )
        except ValueError as ve:
            return ToolResult(
                success=False,
                data=None,
                message=f"Configuration error: {ve}",
            )
        except Exception as exc:
            logger.exception("ClickElementTool execution failed: %s", exc)
            return ToolResult(
                success=False,
                data=None,
                message=f"Failed to find and click element '{description}': {exc}",
            )

    def get_schema(self) -> Dict[str, Any]:
        """Returns JSON schema definition for LLM tool calling."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "description": {
                        "type": "string",
                        "description": "Visual description of the button, menu item, or UI control to click (e.g. 'File menu in Notepad', 'blue Submit button').",
                    },
                    "button": {
                        "type": "string",
                        "enum": ["left", "right", "middle"],
                        "description": "Mouse button to click ('left', 'right', 'middle'; default: 'left').",
                    },
                    "clicks": {
                        "type": "integer",
                        "description": "Number of times to click (default: 1; use 2 for double-click).",
                    },
                },
                "required": ["description"],
            },
        }


class DoOnScreenTool(BaseTool):
    """Tool for running an autonomous look-decide-act visual loop on screen to achieve a goal."""

    name: str = "do_on_screen"
    description: str = (
        "Executes an autonomous visual look-decide-act loop up to 5 steps to accomplish a screen goal. "
        "Captures the screen, uses Gemini to determine the single next action (click, type, hotkey, scroll, or done), "
        "executes it through the system tool registry, and stops on completion or emergency kill switch."
    )

    def run(
        self,
        goal: str = "",
        max_steps: int = 5,
        **kwargs: Any,
    ) -> ToolResult:
        """Run autonomous look-decide-act loop on screen.

        Args:
            goal: Natural language goal (e.g. 'open the File menu in Notepad').
            max_steps: Maximum loop iterations (default: 5).
            **kwargs: Extra parameters (ignored).

        Returns:
            ToolResult containing summary of steps executed.
        """
        try:
            if not goal or not str(goal).strip():
                return ToolResult(
                    success=False,
                    data=None,
                    message="Parameter 'goal' is required and cannot be empty.",
                )

            summary = do_on_screen(goal=str(goal).strip(), max_steps=int(max_steps))
            return ToolResult(
                success=True,
                data={"goal": goal, "summary": summary, "max_steps": max_steps},
                message=summary,
            )
        except PermissionError as pe:
            return ToolResult(
                success=False,
                data=None,
                message=str(pe),
            )
        except ValueError as ve:
            return ToolResult(
                success=False,
                data=None,
                message=f"Configuration error: {ve}",
            )
        except Exception as exc:
            logger.exception("DoOnScreenTool execution failed: %s", exc)
            return ToolResult(
                success=False,
                data=None,
                message=f"Failed to execute look-decide-act loop: {exc}",
            )

    def get_schema(self) -> Dict[str, Any]:
        """Returns JSON schema definition for LLM tool calling."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "goal": {
                        "type": "string",
                        "description": "The goal or task to achieve on screen (e.g., 'open the File menu in Notepad', 'scroll down the page').",
                    },
                    "max_steps": {
                        "type": "integer",
                        "description": "Maximum number of steps to attempt toward the goal (default: 5).",
                    },
                },
                "required": ["goal"],
            },
        }


class ExplainCodeOnScreenTool(BaseTool):
    """Tool for reading visible code on screen, explaining its purpose or fixing errors."""

    name: str = "explain_code_on_screen"
    description: str = (
        "Reads visible code in an editor or terminal on screen. "
        "Can explain the code line-by-line in beginner-friendly English (task='explain') "
        "or detect bugs, syntax issues, and provide corrected code (task='fix')."
    )

    def run(
        self,
        task: str = "explain",
        active_window: bool = True,
        **kwargs: Any,
    ) -> ToolResult:
        """Explain or fix code visible on screen.

        Args:
            task: 'explain' to explain code or 'fix' to identify bugs and suggest corrected code.
            active_window: If True, crops to active editor window (default: True).
            **kwargs: Extra parameters (ignored).

        Returns:
            ToolResult containing the explanation or fix.
        """
        try:
            task_clean = str(task).strip().lower()
            if task_clean not in ("explain", "fix"):
                return ToolResult(
                    success=False,
                    data=None,
                    message="Parameter 'task' must be either 'explain' or 'fix'.",
                )

            result = explain_code_on_screen(task=task_clean, active_window=active_window)
            return ToolResult(
                success=True,
                data={"task": task_clean, "result": result, "active_window": active_window},
                message=result,
            )
        except PermissionError as pe:
            return ToolResult(
                success=False,
                data=None,
                message=str(pe),
            )
        except ValueError as ve:
            return ToolResult(
                success=False,
                data=None,
                message=f"Configuration error: {ve}",
            )
        except Exception as exc:
            logger.exception("ExplainCodeOnScreenTool execution failed: %s", exc)
            return ToolResult(
                success=False,
                data=None,
                message=f"Failed to explain or fix code on screen: {exc}",
            )

    def get_schema(self) -> Dict[str, Any]:
        """Returns JSON schema definition for LLM tool calling."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "task": {
                        "type": "string",
                        "enum": ["explain", "fix"],
                        "description": "Whether to 'explain' visible code in simple English or 'fix' bugs with corrected code.",
                    },
                    "active_window": {
                        "type": "boolean",
                        "description": "Whether to crop capture specifically to the active code editor window (default: true).",
                    },
                },
                "required": [],
            },
        }


# Expose TOOLS list for automatic auto-loading by tools/registry.py
TOOLS: List[BaseTool] = [
    ScreenshotTool(),
    DescribeScreenTool(),
    ExplainScreenErrorTool(),
    ClickElementTool(),
    DoOnScreenTool(),
    ExplainCodeOnScreenTool(),
]