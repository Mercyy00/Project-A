"""
Browser Automation Tools for JARVIS.

Provides reliable, universal browser interactions across Chrome, Edge, Brave, and Firefox:
- Tabs: open, new_tab, close_tab, next_tab (tab ahead), prev_tab (tab behind), switch_tab, reopen_tab
- Navigation: navigate to URL, search_web, back, forward, reload, hard_reload
- Page control: scroll down, scroll up, scroll top, scroll bottom, zoom in, zoom out, zoom reset
- Link interaction: click link / element by text or screen position
- Windows & Views: new_window, incognito window, fullscreen (F11), bookmark, history, downloads, close_browser

Combines direct process dispatch with native OS keystrokes and window focusing
for 100% universal reliability.
"""

from __future__ import annotations

import logging
import os
import re
import subprocess
import sys
import time
import urllib.parse
import webbrowser
from typing import Any, Dict, List, Optional, Tuple

from tools.base import BaseTool, ToolResult

logger = logging.getLogger(__name__)

# Safe PyAutoGUI import with graceful fallback
try:
    import pyautogui
    pyautogui.PAUSE = 0.1
    pyautogui.FAILSAFE = False
except ImportError:
    pyautogui = None  # type: ignore

try:
    import pygetwindow as gw
except ImportError:
    gw = None  # type: ignore

try:
    from tools.guard import is_stopped, log_action
except ImportError:
    def is_stopped() -> bool:
        return False

    def log_action(tool_name: str, args: Any, result_summary: Any) -> None:
        pass


class BrowserControlTool(BaseTool):
    """Universal browser controller supporting full tab management, scrolling, navigation, and page interaction."""
    name: str = "browser_control"
    description: str = (
        "Controls web browsers with complete automation: open URLs, manage tabs (new tab, close tab, "
        "next tab / tab ahead, previous tab / tab behind, switch tab, reopen tab), scroll webpage, "
        "reload, navigate back/forward, zoom, click links, and toggle fullscreen."
    )

    def get_schema(self) -> Dict[str, Any]:
        """Returns JSON schema definition for LLM tool calling."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": [
                            "open",
                            "new_tab",
                            "close_tab",
                            "close_browser",
                            "navigate",
                            "search",
                            "next_tab",
                            "prev_tab",
                            "switch_tab",
                            "reopen_tab",
                            "scroll_down",
                            "scroll_up",
                            "scroll_top",
                            "scroll_bottom",
                            "reload",
                            "hard_reload",
                            "back",
                            "forward",
                            "zoom_in",
                            "zoom_out",
                            "zoom_reset",
                            "fullscreen",
                            "new_window",
                            "incognito",
                            "bookmark",
                            "find_in_page",
                            "history",
                            "downloads",
                            "click_link",
                        ],
                        "description": (
                            "Action to perform: 'open', 'new_tab', 'close_tab', 'close_browser', 'navigate', 'search', "
                            "'next_tab' (tab ahead), 'prev_tab' (tab behind), 'switch_tab', 'reopen_tab', "
                            "'scroll_down', 'scroll_up', 'scroll_top', 'scroll_bottom', 'reload', 'hard_reload', "
                            "'back', 'forward', 'zoom_in', 'zoom_out', 'zoom_reset', 'fullscreen', 'new_window', "
                            "'incognito', 'bookmark', 'find_in_page', 'history', 'downloads', or 'click_link'."
                        ),
                    },
                    "url": {
                        "type": "string",
                        "description": "Optional URL to open or navigate to (e.g. 'https://github.com', 'https://google.com').",
                    },
                    "query": {
                        "type": "string",
                        "description": "Search query or search text when action is 'search' or 'find_in_page'.",
                    },
                    "browser": {
                        "type": "string",
                        "description": "Optional target browser name ('chrome', 'msedge', 'firefox', 'brave', or 'default').",
                    },
                    "tab_index": {
                        "type": "integer",
                        "description": "1-based tab number (1 to 8, or 9 for the last tab) when action is 'switch_tab'.",
                        "default": 1,
                    },
                    "scroll_amount": {
                        "type": "integer",
                        "description": "Number of scroll notches or intensity when scrolling (default: 6).",
                        "default": 6,
                    },
                    "link_text": {
                        "type": "string",
                        "description": "Optional visible link text or element description to click when action is 'click_link'.",
                    },
                },
                "required": ["action"],
            },
        }

    @classmethod
    def _focus_browser_window(cls, browser: Optional[str] = None) -> bool:
        """Brings the active or target browser window to the foreground with keyboard input focus."""
        if os.name != "nt":
            return False

        target_browser = (browser or "").lower().strip()
        browser_names = ["chrome", "edge", "msedge", "brave", "firefox", "opera", "vivaldi"]
        if target_browser and target_browser != "default":
            browser_names = [target_browser] + [b for b in browser_names if b != target_browser]

        try:
            import ctypes
            from ctypes import wintypes

            user32 = ctypes.WinDLL("user32", use_last_error=True)
            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            SW_RESTORE = 9

            def _raise(hwnd: int) -> bool:
                try:
                    if user32.IsIconic(hwnd):
                        user32.ShowWindow(hwnd, SW_RESTORE)
                    if user32.SetForegroundWindow(hwnd):
                        return True

                    fore = user32.GetForegroundWindow()
                    if not fore:
                        return False
                    their = user32.GetWindowThreadProcessId(fore, None)
                    ours = kernel32.GetCurrentThreadId()
                    if their != ours and user32.AttachThreadInput(ours, their, True):
                        try:
                            user32.BringWindowToTop(hwnd)
                            user32.ShowWindow(hwnd, SW_RESTORE)
                            return bool(user32.SetForegroundWindow(hwnd))
                        finally:
                            user32.AttachThreadInput(ours, their, False)
                    return False
                except Exception:
                    return False

            candidate_hwnds: List[int] = []

            def _enum_cb(hwnd: int, _lparam: Any) -> bool:
                if user32.IsWindow(hwnd) and user32.IsWindowVisible(hwnd):
                    length = user32.GetWindowTextLengthW(hwnd)
                    if length > 0:
                        buff = ctypes.create_unicode_buffer(length + 1)
                        user32.GetWindowTextW(hwnd, buff, length + 1)
                        title = buff.value.lower()
                        if any(b in title for b in browser_names):
                            candidate_hwnds.append(hwnd)
                return True

            WNDENUM = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
            user32.EnumWindows(WNDENUM(_enum_cb), 0)

            for h in candidate_hwnds:
                if _raise(h):
                    time.sleep(0.12)
                    return True

        except Exception as exc:
            logger.debug("Win32 browser window focus failed: %s", exc)

        # Fallback to pygetwindow
        if gw is not None:
            try:
                for w in gw.getAllWindows():
                    t = getattr(w, "title", "").lower()
                    if any(b in t for b in browser_names) and getattr(w, "visible", True):
                        try:
                            if getattr(w, "isMinimized", False):
                                w.restore()
                            w.activate()
                            time.sleep(0.12)
                            return True
                        except Exception:
                            pass
            except Exception:
                pass

        return False

    @classmethod
    def _get_browser_window_rect(cls) -> Optional[Tuple[int, int, int, int]]:
        """Returns (left, top, width, height) of the browser window if visible."""
        if gw is not None:
            try:
                for w in gw.getAllWindows():
                    t = getattr(w, "title", "").lower()
                    if any(b in t for b in ("chrome", "edge", "brave", "firefox", "opera")) and getattr(w, "visible", True):
                        return (w.left, w.top, w.width, w.height)
            except Exception:
                pass
        return None

    def run(
        self,
        action: str = "open",
        url: Optional[str] = None,
        query: Optional[str] = None,
        browser: Optional[str] = None,
        tab_index: int = 1,
        scroll_amount: int = 6,
        link_text: Optional[str] = None,
        **kwargs: Any,
    ) -> ToolResult:
        """Executes a browser automation action."""
        act = (action or "open").lower().strip()
        args_payload = {
            "action": action,
            "url": url,
            "query": query,
            "browser": browser,
            "tab_index": tab_index,
            "scroll_amount": scroll_amount,
            "link_text": link_text,
        }

        if is_stopped():
            res = ToolResult(success=False, message="Execution stopped: Kill switch is active.")
            log_action(self.name, args_payload, res.message)
            return res

        try:
            # ─────────────────────────────────────────────────────────────
            # 1. OPEN / LAUNCH BROWSER
            # ─────────────────────────────────────────────────────────────
            if act in ("open", "open_browser"):
                target_url = url or "https://www.google.com"
                if not target_url.startswith(("http://", "https://")):
                    target_url = "https://" + target_url

                if browser and browser.lower() != "default":
                    launched = self._launch_specific_browser(browser.lower(), target_url)
                    if launched:
                        res = ToolResult(
                            success=True,
                            data={"browser": browser, "url": target_url, "action": act},
                            message=f"Opened {browser} to {target_url}",
                        )
                        log_action(self.name, args_payload, res.message)
                        return res

                webbrowser.open(target_url, new=1)
                res = ToolResult(
                    success=True,
                    data={"url": target_url, "action": act},
                    message=f"Browser opened to {target_url}",
                )
                log_action(self.name, args_payload, res.message)
                return res

            # ─────────────────────────────────────────────────────────────
            # 2. TAB CONTROLS (NEW, CLOSE, NEXT, PREV, SWITCH, REOPEN)
            # ─────────────────────────────────────────────────────────────
            elif act == "new_tab":
                target_url = url or ""
                if target_url:
                    if not target_url.startswith(("http://", "https://")):
                        target_url = "https://" + target_url
                    webbrowser.open_new_tab(target_url)
                    res = ToolResult(
                        success=True,
                        data={"url": target_url, "action": act},
                        message=f"Opened new tab navigating to {target_url}",
                    )
                else:
                    self._focus_browser_window(browser)
                    success = self._send_hotkey(["ctrl", "t"])
                    if not success:
                        webbrowser.open_new_tab("https://www.google.com")
                    res = ToolResult(
                        success=True,
                        data={"action": act},
                        message="Opened a new browser tab.",
                    )
                log_action(self.name, args_payload, res.message)
                return res

            elif act in ("close_tab", "close_current_tab"):
                self._focus_browser_window(browser)
                success = self._send_hotkey(["ctrl", "w"])
                res = ToolResult(
                    success=success,
                    data={"action": act},
                    message="Active browser tab closed." if success else "Failed to dispatch close tab command.",
                )
                log_action(self.name, args_payload, res.message)
                return res

            elif act in ("next_tab", "tab_ahead", "switch_next_tab"):
                # Ctrl+Tab moves to the next tab (ahead of current active tab)
                self._focus_browser_window(browser)
                success = self._send_hotkey(["ctrl", "tab"])
                res = ToolResult(
                    success=success,
                    data={"action": "next_tab"},
                    message="Switched to next tab (tab ahead).",
                )
                log_action(self.name, args_payload, res.message)
                return res

            elif act in ("prev_tab", "previous_tab", "tab_behind", "switch_prev_tab"):
                # Ctrl+Shift+Tab moves to the previous tab (behind current active tab)
                self._focus_browser_window(browser)
                success = self._send_hotkey(["ctrl", "shift", "tab"])
                res = ToolResult(
                    success=success,
                    data={"action": "prev_tab"},
                    message="Switched to previous tab (tab behind).",
                )
                log_action(self.name, args_payload, res.message)
                return res

            elif act in ("switch_tab", "go_to_tab"):
                idx = max(1, min(9, int(tab_index or 1)))
                self._focus_browser_window(browser)
                success = self._send_hotkey(["ctrl", str(idx)])
                target_desc = f"tab {idx}" if idx < 9 else "last tab"
                res = ToolResult(
                    success=success,
                    data={"action": "switch_tab", "tab_index": idx},
                    message=f"Switched browser focus to {target_desc}.",
                )
                log_action(self.name, args_payload, res.message)
                return res

            elif act in ("reopen_tab", "undo_close_tab", "restore_tab"):
                # Ctrl+Shift+T reopens the last closed tab
                self._focus_browser_window(browser)
                success = self._send_hotkey(["ctrl", "shift", "t"])
                res = ToolResult(
                    success=success,
                    data={"action": "reopen_tab"},
                    message="Reopened previously closed tab.",
                )
                log_action(self.name, args_payload, res.message)
                return res

            # ─────────────────────────────────────────────────────────────
            # 3. PAGE SCROLLING
            # ─────────────────────────────────────────────────────────────
            elif act in ("scroll_down", "scroll"):
                self._focus_browser_window(browser)
                rect = self._get_browser_window_rect()
                amt = max(1, int(scroll_amount or 6))
                if pyautogui is not None:
                    if rect:
                        pyautogui.moveTo(rect[0] + rect[2] // 2, rect[1] + rect[3] // 2)
                    pyautogui.scroll(-int(amt * 120))
                res = ToolResult(
                    success=True,
                    data={"action": "scroll_down", "amount": amt},
                    message=f"Scrolled browser page down by {amt} units.",
                )
                log_action(self.name, args_payload, res.message)
                return res

            elif act == "scroll_up":
                self._focus_browser_window(browser)
                rect = self._get_browser_window_rect()
                amt = max(1, int(scroll_amount or 6))
                if pyautogui is not None:
                    if rect:
                        pyautogui.moveTo(rect[0] + rect[2] // 2, rect[1] + rect[3] // 2)
                    pyautogui.scroll(int(amt * 120))
                res = ToolResult(
                    success=True,
                    data={"action": "scroll_up", "amount": amt},
                    message=f"Scrolled browser page up by {amt} units.",
                )
                log_action(self.name, args_payload, res.message)
                return res

            elif act in ("scroll_top", "top_of_page"):
                self._focus_browser_window(browser)
                if pyautogui is not None:
                    pyautogui.press("home")
                res = ToolResult(success=True, data={"action": act}, message="Scrolled to top of webpage.")
                log_action(self.name, args_payload, res.message)
                return res

            elif act in ("scroll_bottom", "bottom_of_page"):
                self._focus_browser_window(browser)
                if pyautogui is not None:
                    pyautogui.press("end")
                res = ToolResult(success=True, data={"action": act}, message="Scrolled to bottom of webpage.")
                log_action(self.name, args_payload, res.message)
                return res

            # ─────────────────────────────────────────────────────────────
            # 4. NAVIGATION (RELOAD, BACK, FORWARD, NAVIGATE, SEARCH)
            # ─────────────────────────────────────────────────────────────
            elif act in ("reload", "refresh"):
                self._focus_browser_window(browser)
                success = self._send_hotkey(["f5"]) or self._send_hotkey(["ctrl", "r"])
                res = ToolResult(success=success, data={"action": "reload"}, message="Reloaded active browser tab.")
                log_action(self.name, args_payload, res.message)
                return res

            elif act in ("hard_reload", "force_reload"):
                self._focus_browser_window(browser)
                success = self._send_hotkey(["ctrl", "f5"]) or self._send_hotkey(["ctrl", "shift", "r"])
                res = ToolResult(success=success, data={"action": "hard_reload"}, message="Hard-reloaded browser tab (cache cleared).")
                log_action(self.name, args_payload, res.message)
                return res

            elif act in ("back", "go_back"):
                self._focus_browser_window(browser)
                success = self._send_hotkey(["alt", "left"])
                res = ToolResult(success=success, data={"action": "back"}, message="Navigated back to previous page.")
                log_action(self.name, args_payload, res.message)
                return res

            elif act in ("forward", "go_forward"):
                self._focus_browser_window(browser)
                success = self._send_hotkey(["alt", "right"])
                res = ToolResult(success=success, data={"action": "forward"}, message="Navigated forward to next page.")
                log_action(self.name, args_payload, res.message)
                return res

            elif act == "navigate":
                if not url:
                    return ToolResult(success=False, message="URL is required for navigation.")
                target_url = url
                if not target_url.startswith(("http://", "https://")):
                    target_url = "https://" + target_url
                webbrowser.open_new_tab(target_url)
                res = ToolResult(
                    success=True,
                    data={"url": target_url, "action": act},
                    message=f"Navigated to {target_url}",
                )
                log_action(self.name, args_payload, res.message)
                return res

            elif act == "search":
                q = query or url or ""
                if not q:
                    return ToolResult(success=False, message="Query is required for search action.")
                search_url = f"https://www.google.com/search?q={urllib.parse.quote_plus(q)}"
                if browser and browser.lower() != "default":
                    if not self._launch_specific_browser(browser.lower(), search_url):
                        return ToolResult(
                            success=False,
                            data={"query": q, "browser": browser},
                            message=f"Could not find or launch {browser} to search for '{q}'.",
                        )
                else:
                    webbrowser.open_new_tab(search_url)
                res = ToolResult(
                    success=True,
                    data={"query": q, "url": search_url, "action": act, "browser": browser or "default"},
                    message=f"Opened Google search for '{q}' in {browser or 'the default browser'}.",
                )
                log_action(self.name, args_payload, res.message)
                return res

            # ─────────────────────────────────────────────────────────────
            # 5. ZOOM & DISPLAY MODES
            # ─────────────────────────────────────────────────────────────
            elif act in ("zoom_in", "zoom_plus"):
                self._focus_browser_window(browser)
                success = self._send_hotkey(["ctrl", "+"]) or self._send_hotkey(["ctrl", "="])
                res = ToolResult(success=success, data={"action": "zoom_in"}, message="Zoomed in on webpage.")
                log_action(self.name, args_payload, res.message)
                return res

            elif act in ("zoom_out", "zoom_minus"):
                self._focus_browser_window(browser)
                success = self._send_hotkey(["ctrl", "-"])
                res = ToolResult(success=success, data={"action": "zoom_out"}, message="Zoomed out on webpage.")
                log_action(self.name, args_payload, res.message)
                return res

            elif act in ("zoom_reset", "reset_zoom"):
                self._focus_browser_window(browser)
                success = self._send_hotkey(["ctrl", "0"])
                res = ToolResult(success=success, data={"action": "zoom_reset"}, message="Reset webpage zoom to 100%.")
                log_action(self.name, args_payload, res.message)
                return res

            elif act in ("fullscreen", "toggle_fullscreen"):
                self._focus_browser_window(browser)
                if pyautogui is not None:
                    pyautogui.press("f11")
                res = ToolResult(success=True, data={"action": "fullscreen"}, message="Toggled browser fullscreen (F11).")
                log_action(self.name, args_payload, res.message)
                return res

            # ─────────────────────────────────────────────────────────────
            # 6. WINDOWS & UTILITIES (NEW WINDOW, INCOGNITO, BOOKMARK, ETC.)
            # ─────────────────────────────────────────────────────────────
            elif act == "new_window":
                self._focus_browser_window(browser)
                success = self._send_hotkey(["ctrl", "n"])
                res = ToolResult(success=success, data={"action": "new_window"}, message="Opened a new browser window.")
                log_action(self.name, args_payload, res.message)
                return res

            elif act in ("incognito", "private_window", "private_tab"):
                self._focus_browser_window(browser)
                success = self._send_hotkey(["ctrl", "shift", "n"])
                if not success:
                    success = self._send_hotkey(["ctrl", "shift", "p"])
                res = ToolResult(success=success, data={"action": "incognito"}, message="Opened private/incognito browser window.")
                log_action(self.name, args_payload, res.message)
                return res

            elif act == "bookmark":
                self._focus_browser_window(browser)
                success = self._send_hotkey(["ctrl", "d"])
                res = ToolResult(success=success, data={"action": "bookmark"}, message="Opened bookmark prompt for current page.")
                log_action(self.name, args_payload, res.message)
                return res

            elif act in ("find_in_page", "find"):
                self._focus_browser_window(browser)
                self._send_hotkey(["ctrl", "f"])
                if query and pyautogui is not None:
                    time.sleep(0.15)
                    pyautogui.typewrite(query, interval=0.02)
                res = ToolResult(
                    success=True,
                    data={"action": "find_in_page", "query": query},
                    message=f"Opened Find in Page{' for ' + repr(query) if query else ''}.",
                )
                log_action(self.name, args_payload, res.message)
                return res

            elif act == "history":
                self._focus_browser_window(browser)
                success = self._send_hotkey(["ctrl", "h"])
                res = ToolResult(success=success, data={"action": "history"}, message="Opened browser history.")
                log_action(self.name, args_payload, res.message)
                return res

            elif act == "downloads":
                self._focus_browser_window(browser)
                success = self._send_hotkey(["ctrl", "j"])
                res = ToolResult(success=success, data={"action": "downloads"}, message="Opened browser downloads.")
                log_action(self.name, args_payload, res.message)
                return res

            elif act in ("click_link", "click_element"):
                self._focus_browser_window(browser)
                rect = self._get_browser_window_rect()
                target_text = link_text or query or ""
                # If target link text provided, search for it in page, then press enter
                if target_text and pyautogui is not None:
                    self._send_hotkey(["ctrl", "f"])
                    time.sleep(0.1)
                    pyautogui.typewrite(target_text, interval=0.02)
                    time.sleep(0.1)
                    pyautogui.press("escape")
                    time.sleep(0.05)
                    pyautogui.press("enter")
                    res = ToolResult(
                        success=True,
                        data={"action": "click_link", "target": target_text},
                        message=f"Focused and clicked link matching '{target_text}'.",
                    )
                else:
                    if pyautogui is not None:
                        if rect:
                            pyautogui.click(rect[0] + rect[2] // 2, rect[1] + rect[3] // 2)
                        else:
                            pyautogui.click()
                    res = ToolResult(
                        success=True,
                        data={"action": "click_link"},
                        message="Clicked on the active webpage.",
                    )
                log_action(self.name, args_payload, res.message)
                return res

            elif act in ("close_browser", "close_window"):
                self._focus_browser_window(browser)
                success = self._send_hotkey(["alt", "f4"])
                res = ToolResult(
                    success=success,
                    data={"action": act},
                    message="Browser window closed." if success else "Failed to dispatch close browser command.",
                )
                log_action(self.name, args_payload, res.message)
                return res

            else:
                res = ToolResult(
                    success=False,
                    message=(
                        f"Unsupported browser action '{action}'. Valid actions include: 'open', 'new_tab', 'close_tab', "
                        "'next_tab', 'prev_tab', 'switch_tab', 'reopen_tab', 'scroll_down', 'scroll_up', 'reload', "
                        "'back', 'forward', 'zoom_in', 'zoom_out', 'fullscreen', 'search', 'click_link', 'close_browser'."
                    ),
                )
                log_action(self.name, args_payload, res.message)
                return res

        except Exception as exc:
            logger.exception("Browser control error: %s", exc)
            res = ToolResult(success=False, message=f"Browser control failed: {str(exc)}")
            log_action(self.name, args_payload, res.message)
            return res

    def _send_hotkey(self, keys: List[str]) -> bool:
        """Dispatches native hotkey via pyautogui or pywin32."""
        if pyautogui is None:
            return False
        try:
            pyautogui.hotkey(*keys)
            return True
        except Exception as exc:
            logger.debug("Hotkey %s failed: %s", keys, exc)
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
                os.path.expandvars(r"%ProgramFiles%\BraveSoftware\Brave-Browser\Application\brave.exe"),
                os.path.expandvars(r"%LocalAppData%\BraveSoftware\Brave-Browser\Application\brave.exe"),
            ],
            "firefox": [
                os.path.expandvars(r"%ProgramFiles%\Mozilla Firefox\firefox.exe"),
                os.path.expandvars(r"%ProgramFiles(x86)%\Mozilla Firefox\firefox.exe"),
            ],
        }
        for candidate in known_paths.get(name, []):
            if os.path.isfile(candidate):
                try:
                    subprocess.Popen([candidate, url])
                    return True
                except Exception:
                    pass

        try:
            subprocess.Popen([name, url], shell=True)
            return True
        except Exception:
            return False
