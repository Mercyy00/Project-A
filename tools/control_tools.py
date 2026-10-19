"""
GUI and OS Control tools for keyboard and mouse automation.
Author: Abhijit (System & Automation Engineer)
"""

from typing import Any, Dict, List, Optional, Union
import pyautogui

from tools.base import BaseTool, ToolResult

# Configure PyAutoGUI safety and timing settings
# 0.3 s pause between PyAutoGUI actions as specified in the plan
pyautogui.PAUSE = 0.3
# Fail-safe corner: moving mouse cursor to any screen corner raises FailSafeException
pyautogui.FAILSAFE = True


class TypeTextTool(BaseTool):
    """Tool for automated keyboard typing simulation."""
    name: str = "type_text"
    description: str = (
        "Types a given text string using automated keyboard simulation. "
        "Supports optional keystroke delay and pressing Enter upon completion."
    )

    def run(
        self,
        text: str = "",
        interval: float = 0.01,
        press_enter: bool = False,
        **kwargs: Any
    ) -> ToolResult:
        """Types text using keyboard simulation.

        Args:
            text: The text string to type.
            interval: Time interval in seconds between individual keystrokes (default: 0.01).
            press_enter: Whether to press Enter after typing finishes (default: False).
            **kwargs: Extra parameters (ignored).

        Returns:
            ToolResult: Execution outcome with character count on success.
        """
        try:
            if not isinstance(text, str):
                return ToolResult(
                    success=False,
                    data=None,
                    message="Invalid parameter: 'text' must be a string."
                )

            pyautogui.write(text, interval=interval)
            if press_enter:
                pyautogui.press("enter")

            return ToolResult(
                success=True,
                data={
                    "chars_typed": len(text),
                    "pressed_enter": press_enter
                },
                message=f"Successfully typed {len(text)} characters."
            )

        except pyautogui.FailSafeException:
            return ToolResult(
                success=False,
                data=None,
                message="Execution stopped: PyAutoGUI fail-safe corner triggered by user."
            )
        except Exception as e:
            return ToolResult(
                success=False,
                data=None,
                message=f"Failed to type text: {str(e)}"
            )

    def get_schema(self) -> Dict[str, Any]:
        """Returns JSON schema definition for LLM tool calling."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "The text string to type out."
                    },
                    "interval": {
                        "type": "number",
                        "description": "Interval in seconds between individual keystrokes (default: 0.01)."
                    },
                    "press_enter": {
                        "type": "boolean",
                        "description": "Whether to simulate pressing the Enter key after typing text."
                    }
                },
                "required": ["text"]
            }
        }


class PressKeysTool(BaseTool):
    """Tool for pressing individual keys or shortcut combinations (hotkeys)."""
    name: str = "press_keys"
    description: str = (
        "Simulates pressing individual keys (e.g. 'enter', 'esc', 'tab') or shortcut "
        "combinations / hotkeys (e.g. ['ctrl', 'c'], 'ctrl+v', ['alt', 'tab'])."
    )

    def run(
        self,
        keys: Optional[Union[List[str], str]] = None,
        key: Optional[str] = None,
        hotkey: Optional[str] = None,
        presses: int = 1,
        interval: float = 0.1,
        **kwargs: Any
    ) -> ToolResult:
        """Simulates pressing keys or shortcut combinations.

        Args:
            keys: List of key names or single string (can be '+'-separated like 'ctrl+c').
            key: Single key alias.
            hotkey: Hotkey alias.
            presses: Number of times to press the key (single key only).
            interval: Interval between repeated presses in seconds.
            **kwargs: Extra parameters (ignored).

        Returns:
            ToolResult: Execution outcome with keys pressed.
        """
        try:
            target = keys if keys is not None else (hotkey or key)
            if target is None:
                return ToolResult(
                    success=False,
                    data=None,
                    message="Missing required parameter: 'keys' must be provided."
                )

            # Normalize keys to a list of strings
            key_list: List[str] = []
            if isinstance(target, str):
                cleaned = target.strip()
                if not cleaned:
                    return ToolResult(
                        success=False,
                        data=None,
                        message="'keys' cannot be an empty string."
                    )
                if "+" in cleaned:
                    key_list = [k.strip().lower() for k in cleaned.split("+") if k.strip()]
                elif "," in cleaned:
                    key_list = [k.strip().lower() for k in cleaned.split(",") if k.strip()]
                else:
                    key_list = [cleaned.lower()]
            elif isinstance(target, (list, tuple)):
                key_list = [str(k).strip().lower() for k in target if str(k).strip()]
            else:
                return ToolResult(
                    success=False,
                    data=None,
                    message="'keys' must be a string or a list of key names."
                )

            if not key_list:
                return ToolResult(
                    success=False,
                    data=None,
                    message="No valid keys provided to press."
                )

            # Perform key press or hotkey execution
            if len(key_list) == 1:
                pyautogui.press(key_list[0], presses=max(1, presses), interval=interval)
            else:
                for _ in range(max(1, presses)):
                    pyautogui.hotkey(*key_list)
                    if presses > 1:
                        pyautogui.sleep(interval)

            formatted_keys = "+".join(key_list)
            return ToolResult(
                success=True,
                data={
                    "keys": key_list,
                    "presses": presses
                },
                message=f"Successfully pressed key(s): '{formatted_keys}'."
            )

        except pyautogui.FailSafeException:
            return ToolResult(
                success=False,
                data=None,
                message="Execution stopped: PyAutoGUI fail-safe corner triggered by user."
            )
        except Exception as e:
            return ToolResult(
                success=False,
                data=None,
                message=f"Failed to press keys: {str(e)}"
            )

    def get_schema(self) -> Dict[str, Any]:
        """Returns JSON schema definition for LLM tool calling."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "keys": {
                        "type": ["array", "string"],
                        "items": {"type": "string"},
                        "description": "Key name (e.g. 'enter') or list/hotkey combination (e.g. ['ctrl', 'c'] or 'ctrl+s')."
                    },
                    "presses": {
                        "type": "integer",
                        "description": "Number of times to press the key (default: 1)."
                    },
                    "interval": {
                        "type": "number",
                        "description": "Interval between repeated presses in seconds (default: 0.1)."
                    }
                },
                "required": ["keys"]
            }
        }


class ClickTool(BaseTool):
    """Tool for simulating mouse clicks at specific coordinates or current position."""
    name: str = "click"
    description: str = (
        "Simulates a mouse click at specific coordinates (x, y) or at the current cursor position. "
        "Supports left, right, and middle mouse buttons as well as double clicks."
    )

    def run(
        self,
        x: Optional[int] = None,
        y: Optional[int] = None,
        clicks: int = 1,
        button: str = "left",
        interval: float = 0.1,
        **kwargs: Any
    ) -> ToolResult:
        """Performs a mouse click.

        Args:
            x: Target screen X coordinate (optional, defaults to current cursor position).
            y: Target screen Y coordinate (optional, defaults to current cursor position).
            clicks: Number of clicks to perform (default: 1; use 2 for double click).
            button: Mouse button to click ('left', 'right', 'middle'; default: 'left').
            interval: Delay in seconds between clicks if clicks > 1 (default: 0.1).
            **kwargs: Extra parameters (ignored).

        Returns:
            ToolResult: Execution outcome with click position and button.
        """
        try:
            btn = button.lower().strip()
            if btn not in ("left", "right", "middle", "primary", "secondary"):
                return ToolResult(
                    success=False,
                    data=None,
                    message=f"Invalid mouse button '{button}'. Must be 'left', 'right', or 'middle'."
                )

            # Determine coordinates
            if x is not None and y is not None:
                click_x, click_y = int(x), int(y)
                if click_x < 0 or click_y < 0:
                    return ToolResult(
                        success=False,
                        data=None,
                        message=f"Coordinates cannot be negative: ({x}, {y})."
                    )
                pyautogui.click(x=click_x, y=click_y, clicks=clicks, interval=interval, button=btn)
            else:
                curr_pos = pyautogui.position()
                click_x, click_y = curr_pos.x, curr_pos.y
                pyautogui.click(clicks=clicks, interval=interval, button=btn)

            return ToolResult(
                success=True,
                data={
                    "x": click_x,
                    "y": click_y,
                    "clicks": clicks,
                    "button": btn
                },
                message=f"Successfully clicked {btn} button {clicks} time(s) at ({click_x}, {click_y})."
            )

        except pyautogui.FailSafeException:
            return ToolResult(
                success=False,
                data=None,
                message="Execution stopped: PyAutoGUI fail-safe corner triggered by user."
            )
        except Exception as e:
            return ToolResult(
                success=False,
                data=None,
                message=f"Failed to perform click: {str(e)}"
            )

    def get_schema(self) -> Dict[str, Any]:
        """Returns JSON schema definition for LLM tool calling."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "x": {
                        "type": "integer",
                        "description": "Screen X coordinate to click (optional; if omitted, clicks current cursor position)."
                    },
                    "y": {
                        "type": "integer",
                        "description": "Screen Y coordinate to click (optional; if omitted, clicks current cursor position)."
                    },
                    "clicks": {
                        "type": "integer",
                        "description": "Number of clicks to perform (1 for single click, 2 for double click; default: 1)."
                    },
                    "button": {
                        "type": "string",
                        "enum": ["left", "right", "middle"],
                        "description": "Mouse button to click (default: 'left')."
                    },
                    "interval": {
                        "type": "number",
                        "description": "Interval between multiple clicks in seconds (default: 0.1)."
                    }
                },
                "required": []
            }
        }


class ScrollTool(BaseTool):
    """Tool for simulating mouse scroll wheel actions."""
    name: str = "scroll"
    description: str = (
        "Simulates scrolling the mouse wheel vertically. "
        "Positive values scroll up, negative values scroll down."
    )

    def run(
        self,
        clicks: int = 0,
        amount: Optional[int] = None,
        x: Optional[int] = None,
        y: Optional[int] = None,
        **kwargs: Any
    ) -> ToolResult:
        """Scrolls the mouse wheel.

        Args:
            clicks: Number of scroll increments (positive = up, negative = down).
            amount: Alias for clicks.
            x: Optional screen X coordinate at which to scroll.
            y: Optional screen Y coordinate at which to scroll.
            **kwargs: Extra parameters (ignored).

        Returns:
            ToolResult: Execution outcome with scroll clicks performed.
        """
        try:
            scroll_clicks = clicks if clicks != 0 else (amount if amount is not None else 0)
            if scroll_clicks == 0:
                return ToolResult(
                    success=False,
                    data=None,
                    message="Invalid scroll amount: 'clicks' must be a non-zero integer."
                )

            if x is not None and y is not None:
                pyautogui.scroll(int(scroll_clicks), x=int(x), y=int(y))
            else:
                pyautogui.scroll(int(scroll_clicks))

            direction = "up" if scroll_clicks > 0 else "down"
            return ToolResult(
                success=True,
                data={
                    "clicks": scroll_clicks,
                    "direction": direction,
                    "x": x,
                    "y": y
                },
                message=f"Successfully scrolled {direction} by {abs(scroll_clicks)} click(s)."
            )

        except pyautogui.FailSafeException:
            return ToolResult(
                success=False,
                data=None,
                message="Execution stopped: PyAutoGUI fail-safe corner triggered by user."
            )
        except Exception as e:
            return ToolResult(
                success=False,
                data=None,
                message=f"Failed to scroll: {str(e)}"
            )

    def get_schema(self) -> Dict[str, Any]:
        """Returns JSON schema definition for LLM tool calling."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "clicks": {
                        "type": "integer",
                        "description": "Scroll wheel increments. Positive numbers scroll up, negative numbers scroll down."
                    },
                    "x": {
                        "type": "integer",
                        "description": "Screen X coordinate at which to perform the scroll (optional)."
                    },
                    "y": {
                        "type": "integer",
                        "description": "Screen Y coordinate at which to perform the scroll (optional)."
                    }
                },
                "required": ["clicks"]
            }
        }


# Export collection of control tools
CONTROL_TOOLS: List[BaseTool] = [
    TypeTextTool(),
    PressKeysTool(),
    ClickTool(),
    ScrollTool(),
]

TOOLS: List[BaseTool] = CONTROL_TOOLS
