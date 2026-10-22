"""
Window Management Tools for Jarvis.

Provides tools to inspect, focus, and minimize application windows on Windows hosts
using pygetwindow and native Windows APIs.
"""

import logging
from typing import Any, Dict, List, Optional
import ctypes

from tools.base import BaseTool, ToolResult

logger = logging.getLogger(__name__)

try:
    import pygetwindow as gw
except ImportError:
    gw = None


class ListWindowsTool(BaseTool):
    """Tool that enumerates open and visible windows on the desktop."""
    name: str = "list_windows"
    description: str = (
        "Lists all visible and active application windows on the desktop. "
        "Useful for discovering window titles before focusing or minimizing them."
    )

    def run(self, include_empty: bool = False, **kwargs: Any) -> ToolResult:
        """Enumerate application windows.

        Args:
            include_empty: If True, include windows with empty title strings.
            **kwargs: Extra keyword arguments.

        Returns:
            ToolResult: List of window details including title, position, and status.
        """
        try:
            if gw is None:
                return ToolResult(
                    success=False,
                    data=None,
                    message="pygetwindow module is not installed."
                )

            windows = gw.getAllWindows()
            result_list: List[Dict[str, Any]] = []

            for w in windows:
                raw_title = getattr(w, "title", "")
                title = raw_title.strip() if isinstance(raw_title, str) else ""

                if not title and not include_empty:
                    continue

                # Filter out invisible or 0-dimension helper windows if not requested
                width = getattr(w, "width", 0)
                height = getattr(w, "height", 0)
                is_visible = getattr(w, "visible", True)

                # Skip completely offscreen/zero-sized non-titled windows
                if width <= 0 or height <= 0:
                    if not include_empty:
                        continue

                result_list.append({
                    "title": title or "(Untitled)",
                    "is_active": getattr(w, "isActive", False),
                    "is_minimized": getattr(w, "isMinimized", False),
                    "is_maximized": getattr(w, "isMaximized", False),
                    "is_visible": is_visible,
                    "rect": {
                        "left": getattr(w, "left", 0),
                        "top": getattr(w, "top", 0),
                        "width": width,
                        "height": height,
                    }
                })

            return ToolResult(
                success=True,
                data=result_list,
                message=f"Retrieved {len(result_list)} open application windows."
            )
        except Exception as e:
            logger.exception("Failed to list application windows: %s", e)
            return ToolResult(
                success=False,
                data=None,
                message=f"Failed to list windows: {str(e)}"
            )

    def get_schema(self) -> Dict[str, Any]:
        """Returns JSON schema definition for LLM tool calling."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "include_empty": {
                        "type": "boolean",
                        "description": "Whether to include unnamed or hidden windows. Defaults to False.",
                        "default": False
                    }
                },
                "required": []
            }
        }


class FocusWindowTool(BaseTool):
    """Tool that brings a target window into foreground focus."""
    name: str = "focus_window"
    description: str = (
        "Brings an open application window to the foreground and focuses it "
        "by matching the title (case-insensitive substring)."
    )

    def run(self, title: str, **kwargs: Any) -> ToolResult:
        """Focus an open window matching the given title query.

        Args:
            title: Window title or substring to search for.
            **kwargs: Extra keyword arguments.

        Returns:
            ToolResult: Execution outcome with matched window details.
        """
        try:
            if not title or not isinstance(title, str) or not title.strip():
                return ToolResult(
                    success=False,
                    data=None,
                    message="title must be a non-empty string."
                )

            if gw is None:
                return ToolResult(
                    success=False,
                    data=None,
                    message="pygetwindow module is not installed."
                )

            query = title.strip().lower()
            all_windows = gw.getAllWindows()
            matched_window = None

            # First pass: look for exact title match (case-insensitive)
            for w in all_windows:
                w_title = getattr(w, "title", "")
                if w_title and w_title.strip().lower() == query:
                    matched_window = w
                    break

            # Second pass: substring match
            if not matched_window:
                for w in all_windows:
                    w_title = getattr(w, "title", "")
                    if w_title and query in w_title.strip().lower():
                        matched_window = w
                        break

            if not matched_window:
                available_titles = [
                    w.title.strip() for w in all_windows
                    if getattr(w, "title", "").strip()
                ]
                return ToolResult(
                    success=False,
                    data={"available_windows": available_titles[:15]},
                    message=f"No open window found matching '{title}'."
                )

            # Restore window if minimized
            try:
                if getattr(matched_window, "isMinimized", False):
                    matched_window.restore()
            except Exception as e:
                logger.debug("Could not restore window before activate: %s", e)

            # Activate window
            try:
                matched_window.activate()
            except Exception:
                # Windows foreground lock workaround using native Win32 API
                hwnd = getattr(matched_window, "_hWnd", None)
                if hwnd:
                    ctypes.windll.user32.ShowWindow(hwnd, 9)  # SW_RESTORE
                    ctypes.windll.user32.SetForegroundWindow(hwnd)

            return ToolResult(
                success=True,
                data={
                    "title": matched_window.title,
                    "is_active": getattr(matched_window, "isActive", True)
                },
                message=f"Window '{matched_window.title}' focused successfully."
            )
        except Exception as e:
            logger.exception("Error focusing window '%s': %s", title, e)
            return ToolResult(
                success=False,
                data=None,
                message=f"Failed to focus window matching '{title}': {str(e)}"
            )

    def get_schema(self) -> Dict[str, Any]:
        """Returns JSON schema definition for LLM tool calling."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Window title or part of title to focus (e.g. 'Notepad', 'Chrome')."
                    }
                },
                "required": ["title"]
            }
        }


class MinimizeWindowTool(BaseTool):
    """Tool that minimizes a target window to the taskbar."""
    name: str = "minimize_window"
    description: str = (
        "Minimizes an open application window to the taskbar "
        "by matching the title (case-insensitive substring)."
    )

    def run(self, title: str, **kwargs: Any) -> ToolResult:
        """Minimize an open window matching the given title query.

        Args:
            title: Window title or substring to search for.
            **kwargs: Extra keyword arguments.

        Returns:
            ToolResult: Execution outcome with minimized window details.
        """
        try:
            if not title or not isinstance(title, str) or not title.strip():
                return ToolResult(
                    success=False,
                    data=None,
                    message="title must be a non-empty string."
                )

            if gw is None:
                return ToolResult(
                    success=False,
                    data=None,
                    message="pygetwindow module is not installed."
                )

            query = title.strip().lower()
            all_windows = gw.getAllWindows()
            matched_window = None

            # First pass: exact title match
            for w in all_windows:
                w_title = getattr(w, "title", "")
                if w_title and w_title.strip().lower() == query:
                    matched_window = w
                    break

            # Second pass: substring match
            if not matched_window:
                for w in all_windows:
                    w_title = getattr(w, "title", "")
                    if w_title and query in w_title.strip().lower():
                        matched_window = w
                        break

            if not matched_window:
                available_titles = [
                    w.title.strip() for w in all_windows
                    if getattr(w, "title", "").strip()
                ]
                return ToolResult(
                    success=False,
                    data={"available_windows": available_titles[:15]},
                    message=f"No open window found matching '{title}'."
                )

            # Minimize window
            try:
                matched_window.minimize()
            except Exception:
                hwnd = getattr(matched_window, "_hWnd", None)
                if hwnd:
                    ctypes.windll.user32.ShowWindow(hwnd, 6)  # SW_MINIMIZE

            return ToolResult(
                success=True,
                data={"title": matched_window.title, "is_minimized": True},
                message=f"Window '{matched_window.title}' minimized successfully."
            )
        except Exception as e:
            logger.exception("Error minimizing window '%s': %s", title, e)
            return ToolResult(
                success=False,
                data=None,
                message=f"Failed to minimize window matching '{title}': {str(e)}"
            )

    def get_schema(self) -> Dict[str, Any]:
        """Returns JSON schema definition for LLM tool calling."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Window title or part of title to minimize."
                    }
                },
                "required": ["title"]
            }
        }
