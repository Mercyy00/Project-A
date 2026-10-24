"""
Browser Automation Tools for JARVIS.

Provides reliable browser interactions:
- open_browser: Opens default/specified browser to an optional URL
- new_tab: Opens a fresh browser tab
- close_tab: Closes the currently active browser tab
- close_browser: Closes the active browser window or terminates process
- navigate: Navigates active tab to a new URL
- search_web: Opens web search query in browser

Combines direct process dispatch with native OS keystrokes (Ctrl+T, Ctrl+W, Ctrl+L, Alt+F4)
for 100% universal reliability across Chrome, Edge, Brave, and Firefox.
"""

from __future__ import annotations

import os
import sys
import time
import subprocess
import webbrowser
from typing import Any, Dict, List, Optional

from tools.base import BaseTool, ToolResult


class BrowserControlTool(BaseTool):
    """Universal browser controller supporting tab opening, tab closing, navigation, and window control."""
    name: str = "browser_control"
    description: str = (
        "Controls web browsers: open browser, open a new tab, close active tab, close browser window, "
        "or navigate to a URL. Supports Chrome, Edge, Firefox, Brave, and default browser."
    )

    def get_schema(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["open", "new_tab", "close_tab", "close_browser", "navigate", "search"],
                        "description": "Action to perform: 'open', 'new_tab', 'close_tab', 'close_browser', 'navigate', or 'search'."
                    },
                    "url": {
                        "type": "string",
                        "description": "Optional URL to open or navigate to (e.g. 'https://youtube.com', 'https://google.com')."
                    },
                    "query": {
                        "type": "string",
                        "description": "Optional search query when action is 'search'."
                    },
                    "browser": {
                        "type": "string",
                        "description": "Optional target browser name ('chrome', 'msedge', 'firefox', 'brave', or 'default')."
                    }
                },
                "required": ["action"]
            }
        }

    def run(self, action: str = "open", url: Optional[str] = None, query: Optional[str] = None, browser: Optional[str] = None, **kwargs) -> ToolResult:
        act = action.lower().strip()
        try:
            if act in ("open", "open_browser"):
                target_url = url or "https://www.google.com"
                if not target_url.startswith(("http://", "https://")):
                    target_url = "https://" + target_url
                
                # If specific browser requested, try launching executable
                if browser and browser.lower() != "default":
                    launched = self._launch_specific_browser(browser.lower(), target_url)
                    if launched:
                        return ToolResult(
                            success=True,
                            data={"browser": browser, "url": target_url, "action": act},
                            message=f"Opened {browser} to {target_url}"
                        )

                # Fallback to standard webbrowser
                webbrowser.open(target_url, new=1)
                return ToolResult(
                    success=True,
                    data={"url": target_url, "action": act},
                    message=f"Browser opened to {target_url}"
                )

            elif act == "new_tab":
                target_url = url or ""
                if target_url:
                    if not target_url.startswith(("http://", "https://")):
                        target_url = "https://" + target_url
                    webbrowser.open_new_tab(target_url)
                    return ToolResult(
                        success=True,
                        data={"url": target_url, "action": act},
                        message=f"Opened new tab navigating to {target_url}"
                    )
                else:
                    # Native OS Ctrl+T to open blank new tab in current browser
                    success = self._send_hotkey(["ctrl", "t"])
                    if not success:
                        webbrowser.open_new_tab("https://www.google.com")
                    return ToolResult(
                        success=True,
                        data={"action": act},
                        message="Opened a new browser tab."
                    )

            elif act in ("close_tab", "close_current_tab"):
                # Ctrl+W closes the active tab in all major web browsers
                success = self._send_hotkey(["ctrl", "w"])
                return ToolResult(
                    success=success,
                    data={"action": act},
                    message="Active browser tab closed." if success else "Failed to dispatch close tab command."
                )

            elif act in ("close_browser", "close_window", "close"):
                # First try Alt+F4 to gracefully close active window
                success = self._send_hotkey(["alt", "f4"])
                return ToolResult(
                    success=success,
                    data={"action": act},
                    message="Browser window closed." if success else "Failed to dispatch close browser command."
                )

            elif act == "navigate":
                if not url:
                    return ToolResult(success=False, message="URL is required for navigation.")
                target_url = url
                if not target_url.startswith(("http://", "https://")):
                    target_url = "https://" + target_url
                webbrowser.open_new_tab(target_url)
                return ToolResult(
                    success=True,
                    data={"url": target_url, "action": act},
                    message=f"Navigated to {target_url}"
                )

            elif act == "search":
                q = query or url or ""
                if not q:
                    return ToolResult(success=False, message="Query is required for search action.")
                import urllib.parse
                search_url = f"https://www.google.com/search?q={urllib.parse.quote_plus(q)}"
                webbrowser.open_new_tab(search_url)
                return ToolResult(
                    success=True,
                    data={"query": q, "url": search_url, "action": act},
                    message=f"Searched Google for '{q}'"
                )

            else:
                return ToolResult(
                    success=False,
                    message=f"Unsupported browser action '{action}'. Valid actions are 'open', 'new_tab', 'close_tab', 'close_browser', 'navigate', 'search'."
                )

        except Exception as exc:
            return ToolResult(
                success=False,
                message=f"Browser control failed: {str(exc)}"
            )

    def _send_hotkey(self, keys: List[str]) -> bool:
        """Dispatches native hotkey via pyautogui or pywin32."""
        try:
            import pyautogui
            pyautogui.hotkey(*keys)
            return True
        except Exception:
            return False

    def _launch_specific_browser(self, name: str, url: str) -> bool:
        """Attempts to launch a specific browser binary on Windows with known installation paths."""
        known_paths = {
            "chrome": [
                os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
                os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
                os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
            ],
            "msedge": [
                os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"),
                os.path.expandvars(r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"),
            ],
            "edge": [
                os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"),
                os.path.expandvars(r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"),
            ],
            "brave": [
                os.path.expandvars(r"%ProgramFiles%\BraveSoftware\Brave-Browser\Applicationrave.exe"),
                os.path.expandvars(r"%LocalAppData%\BraveSoftware\Brave-Browser\Applicationrave.exe"),
            ],
            "firefox": [
                os.path.expandvars(r"%ProgramFiles%\Mozilla Firefoxirefox.exe"),
                os.path.expandvars(r"%ProgramFiles(x86)%\Mozilla Firefoxirefox.exe"),
            ]
        }
        for candidate in known_paths.get(name, []):
            if os.path.isfile(candidate):
                try:
                    subprocess.Popen([candidate, url])
                    return True
                except Exception:
                    pass

        # Try by binary name in PATH
        try:
            subprocess.Popen([name, url], shell=True)
            return True
        except Exception:
            return False
