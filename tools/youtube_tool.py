"""
YouTube Automation and Playback Control Tool for JARVIS.
Author: Abhijit (System & Automation Engineer)

Provides complete, robust control over YouTube:
1. Play: Search and directly stream/open the top video (or specified URL).
2. Playback: Pause, resume, toggle play/pause via native hotkeys ('k' / space).
3. Display: Fullscreen ('f'), exit fullscreen ('f' / Esc), theater mode ('t'), miniplayer ('i').
4. Navigation: Scroll down, scroll up, click and open video (by index or screen coordinate).
5. Audio: Mute/unmute ('m'), volume up (Up), volume down (Down).
6. Seek: Skip forward 10s ('l'), rewind 10s ('j'), next video (Shift+N), restart ('0').
7. Captions & Speed: Toggle subtitles ('c'), speed up (Shift+.), slow down (Shift+,).
"""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
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
    import requests
    _REQUESTS_OK = True
except ImportError:
    _REQUESTS_OK = False

try:
    from tools.guard import is_stopped, log_action
except ImportError:
    def is_stopped() -> bool:
        return False

    def log_action(tool_name: str, args: Any, result_summary: Any) -> None:
        pass


class YouTubeControlTool(BaseTool):
    """Tool for controlling YouTube video playback, navigation, and window states."""
    name: str = "youtube_control"
    description: str = (
        "Controls YouTube video playback and navigation: play videos, pause/resume, "
        "fullscreen/exit fullscreen, scroll down/up, click and open video, mute, volume, "
        "seek, next/prev video, captions, and playback speed."
    )

    # Cache for recent search results to enable follow-up commands like "open video 2"
    _last_search_results: List[Dict[str, str]] = []
    _last_played_query: str = ""

    def get_schema(self) -> Dict[str, Any]:
        """Returns JSON schema definition for LLM function calling."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": [
                            "play",
                            "pause",
                            "resume",
                            "toggle_play",
                            "fullscreen",
                            "exit_fullscreen",
                            "scroll_down",
                            "scroll_up",
                            "click_video",
                            "mute",
                            "volume_up",
                            "volume_down",
                            "skip_forward",
                            "skip_backward",
                            "next",
                            "prev",
                            "captions",
                            "speed_up",
                            "slow_down",
                            "restart",
                            "theater_mode",
                            "miniplayer",
                            "search",
                        ],
                        "description": (
                            "Action to perform: 'play', 'pause', 'resume', 'toggle_play', 'fullscreen', "
                            "'exit_fullscreen', 'scroll_down', 'scroll_up', 'click_video', 'mute', "
                            "'volume_up', 'volume_down', 'skip_forward', 'skip_backward', 'next', 'prev', "
                            "'captions', 'speed_up', 'slow_down', 'restart', 'theater_mode', 'miniplayer', or 'search'."
                        ),
                    },
                    "query": {
                        "type": "string",
                        "description": "Video search query, song name, or topic to play or search on YouTube.",
                    },
                    "url": {
                        "type": "string",
                        "description": "Optional direct YouTube video URL to open and play.",
                    },
                    "index": {
                        "type": "integer",
                        "description": "Video result number (1 for first video, 2 for second, etc.) when clicking/opening a video.",
                        "default": 1,
                    },
                    "scroll_amount": {
                        "type": "integer",
                        "description": "Number of scroll clicks or distance when scrolling up or down (default: 6).",
                        "default": 6,
                    },
                },
                "required": ["action"],
            },
        }

    @classmethod
    def _focus_youtube_window(cls) -> bool:
        """Brings the YouTube or active browser window to the foreground with keyboard input focus."""
        if os.name != "nt":
            return False

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

            youtube_hwnds: List[int] = []
            browser_hwnds: List[int] = []

            def _enum_cb(hwnd: int, _lparam: Any) -> bool:
                if user32.IsWindow(hwnd) and user32.IsWindowVisible(hwnd):
                    length = user32.GetWindowTextLengthW(hwnd)
                    if length > 0:
                        buff = ctypes.create_unicode_buffer(length + 1)
                        user32.GetWindowTextW(hwnd, buff, length + 1)
                        title = buff.value.lower()
                        if "youtube" in title:
                            youtube_hwnds.append(hwnd)
                        elif any(b in title for b in ("chrome", "edge", "brave", "firefox", "opera")):
                            browser_hwnds.append(hwnd)
                return True

            WNDENUM = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
            user32.EnumWindows(WNDENUM(_enum_cb), 0)

            # Prioritize YouTube window, then active browser
            for h in youtube_hwnds + browser_hwnds:
                if _raise(h):
                    time.sleep(0.15)
                    return True

        except Exception as exc:
            logger.debug("Win32 window focus failed: %s", exc)

        # Fallback to pygetwindow
        if gw is not None:
            try:
                for w in gw.getAllWindows():
                    t = getattr(w, "title", "").lower()
                    if "youtube" in t and getattr(w, "visible", True):
                        try:
                            if getattr(w, "isMinimized", False):
                                w.restore()
                            w.activate()
                            time.sleep(0.15)
                            return True
                        except Exception:
                            pass
                for w in gw.getAllWindows():
                    t = getattr(w, "title", "").lower()
                    if any(b in t for b in ("chrome", "edge", "brave", "firefox")) and getattr(w, "visible", True):
                        try:
                            if getattr(w, "isMinimized", False):
                                w.restore()
                            w.activate()
                            time.sleep(0.15)
                            return True
                        except Exception:
                            pass
            except Exception:
                pass

        return False

    @classmethod
    def _get_youtube_window_rect(cls) -> Optional[Tuple[int, int, int, int]]:
        """Returns (left, top, width, height) of the YouTube window if visible."""
        if gw is not None:
            try:
                for w in gw.getAllWindows():
                    t = getattr(w, "title", "").lower()
                    if ("youtube" in t or any(b in t for b in ("chrome", "edge", "brave", "firefox"))) and getattr(w, "visible", True):
                        return (w.left, w.top, w.width, w.height)
            except Exception:
                pass
        return None

    @classmethod
    def scrape_youtube_videos(cls, query: str, max_results: int = 5) -> List[Dict[str, str]]:
        """Scrapes YouTube search results to extract clean video titles and watch URLs."""
        clean_q = (query or "").strip()
        if not clean_q or not _REQUESTS_OK:
            return []

        search_url = (
            f"https://www.youtube.com/results"
            f"?search_query={urllib.parse.quote_plus(clean_q)}"
            f"&sp=EgIQAQ%3D%3D"
        )
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "en-US,en;q=0.9",
        }

        results: List[Dict[str, str]] = []
        try:
            resp = requests.get(search_url, headers=headers, timeout=8)
            html = resp.text

            # 1. Parse ytInitialData JSON
            data = None
            idx = html.find("var ytInitialData = ")
            if idx != -1:
                start = idx + len("var ytInitialData = ")
                end = html.find(";</script>", start)
                if end != -1:
                    try:
                        data = json.loads(html[start:end])
                    except Exception:
                        pass
            if not data:
                m = re.search(r"var ytInitialData\s*=\s*({.+?});\s*</script>", html, re.DOTALL)
                if m:
                    try:
                        data = json.loads(m.group(1))
                    except Exception:
                        pass

            if data:
                try:
                    sections = (
                        data.get("contents", {})
                        .get("twoColumnSearchResultsRenderer", {})
                        .get("primaryContents", {})
                        .get("sectionListRenderer", {})
                        .get("contents", [])
                    )
                    for sec in sections:
                        for item in sec.get("itemSectionRenderer", {}).get("contents", []):
                            if "videoRenderer" in item:
                                vr = item["videoRenderer"]
                                vid = vr.get("videoId")
                                title_runs = vr.get("title", {}).get("runs", [])
                                title = title_runs[0].get("text", "") if title_runs else clean_q
                                if vid:
                                    results.append({
                                        "id": vid,
                                        "video_id": vid,
                                        "title": title,
                                        "url": f"https://www.youtube.com/watch?v={vid}",
                                    })
                                    if len(results) >= max_results:
                                        break
                        if len(results) >= max_results:
                            break
                except Exception:
                    pass

            # 2. Fallback regex if JSON parser was empty
            if not results:
                vids = list(dict.fromkeys(re.findall(r"watch\?v=([a-zA-Z0-9_-]{11})", html)))
                for vid in vids[:max_results]:
                    results.append({
                        "id": vid,
                        "video_id": vid,
                        "title": clean_q,
                        "url": f"https://www.youtube.com/watch?v={vid}",
                    })

        except Exception as exc:
            logger.warning("YouTube video search scrape failed: %s", exc)

        return results

    def run(
        self,
        action: str = "play",
        query: Optional[str] = None,
        url: Optional[str] = None,
        index: int = 1,
        scroll_amount: int = 6,
        **kwargs: Any,
    ) -> ToolResult:
        """Executes a YouTube control action.

        Args:
            action: Command to perform (e.g. 'play', 'pause', 'fullscreen', 'scroll_down', etc.).
            query: Search query or song title when playing or searching.
            url: Direct YouTube video URL to open.
            index: Video result index (1-based) to click or open.
            scroll_amount: Number of scroll notches or intensity.

        Returns:
            ToolResult containing execution success status, metadata, and human message.
        """
        args_payload = {
            "action": action,
            "query": query,
            "url": url,
            "index": index,
            "scroll_amount": scroll_amount,
        }

        if is_stopped():
            res = ToolResult(success=False, message="Execution stopped: Kill switch is active.")
            log_action(self.name, args_payload, res.message)
            return res

        act = (action or "play").lower().strip()

        try:
            # ─────────────────────────────────────────────────────────────
            # 1. PLAY / OPEN VIDEO
            # ─────────────────────────────────────────────────────────────
            if act in ("play", "open_video", "start"):
                # Case A: Direct URL given
                if url and ("youtube.com" in url or "youtu.be" in url):
                    webbrowser.open_new_tab(url)
                    res = ToolResult(
                        success=True,
                        data={"url": url, "action": act},
                        message=f"Opening and playing YouTube video: {url}",
                    )
                    log_action(self.name, args_payload, res.message)
                    return res

                # Case B: Search query given
                clean_q = (query or "").strip()
                # Clean up conversational prefixes like "play ... on youtube"
                clean_q = re.sub(r"\b(?:on\s+youtube|in\s+youtube|from\s+youtube)\b", "", clean_q, flags=re.I).strip()

                if clean_q:
                    self.__class__._last_played_query = clean_q
                    scraped = self.scrape_youtube_videos(clean_q, max_results=5)
                    if scraped:
                        self.__class__._last_search_results = scraped
                        target = scraped[0]
                        target_url = target["url"]
                        webbrowser.open_new_tab(target_url)
                        res = ToolResult(
                            success=True,
                            data={"title": target["title"], "url": target_url, "video_id": target["id"]},
                            message=f"Playing '{target['title']}' on YouTube.",
                        )
                        log_action(self.name, args_payload, res.message)
                        return res
                    else:
                        # Fallback to YouTube filtered search URL
                        search_url = f"https://www.youtube.com/results?search_query={urllib.parse.quote_plus(clean_q)}"
                        webbrowser.open_new_tab(search_url)
                        res = ToolResult(
                            success=True,
                            data={"query": clean_q, "url": search_url},
                            message=f"Opened YouTube search for '{clean_q}'.",
                        )
                        log_action(self.name, args_payload, res.message)
                        return res

                # Case C: No query or URL given -> resume or open YouTube homepage
                focused = self._focus_youtube_window()
                if focused and pyautogui is not None:
                    pyautogui.press("k")
                    res = ToolResult(
                        success=True,
                        data={"action": "resume"},
                        message="Resumed YouTube video playback.",
                    )
                else:
                    webbrowser.open_new_tab("https://www.youtube.com")
                    res = ToolResult(
                        success=True,
                        data={"action": "open_home"},
                        message="Opened YouTube in browser.",
                    )
                log_action(self.name, args_payload, res.message)
                return res

            # ─────────────────────────────────────────────────────────────
            # 2. PAUSE / RESUME / TOGGLE
            # ─────────────────────────────────────────────────────────────
            elif act in ("pause", "stop_video"):
                self._focus_youtube_window()
                if pyautogui is not None:
                    pyautogui.press("k")
                res = ToolResult(success=True, data={"action": act}, message="Paused the YouTube video.")
                log_action(self.name, args_payload, res.message)
                return res

            elif act in ("resume", "unpause"):
                self._focus_youtube_window()
                if pyautogui is not None:
                    pyautogui.press("k")
                res = ToolResult(success=True, data={"action": act}, message="Resumed playing the YouTube video.")
                log_action(self.name, args_payload, res.message)
                return res

            elif act in ("toggle_play", "play_pause"):
                self._focus_youtube_window()
                if pyautogui is not None:
                    pyautogui.press("k")
                res = ToolResult(success=True, data={"action": act}, message="Toggled YouTube playback.")
                log_action(self.name, args_payload, res.message)
                return res

            # ─────────────────────────────────────────────────────────────
            # 3. FULLSCREEN / EXIT FULLSCREEN
            # ─────────────────────────────────────────────────────────────
            elif act in ("fullscreen", "enter_fullscreen", "maximize_video", "full_screen"):
                self._focus_youtube_window()
                if pyautogui is not None:
                    pyautogui.press("f")
                res = ToolResult(success=True, data={"action": act}, message="Switched YouTube to fullscreen.")
                log_action(self.name, args_payload, res.message)
                return res

            elif act in ("exit_fullscreen", "out_fullscreen", "out_full_screen", "leave_fullscreen", "minimize_video", "unfullscreen"):
                self._focus_youtube_window()
                if pyautogui is not None:
                    # 'f' or 'escape' reliably exits fullscreen on YouTube
                    pyautogui.press("f")
                res = ToolResult(success=True, data={"action": act}, message="Exited fullscreen mode.")
                log_action(self.name, args_payload, res.message)
                return res

            # ─────────────────────────────────────────────────────────────
            # 4. SCROLL YOUTUBE
            # ─────────────────────────────────────────────────────────────
            elif act in ("scroll_down", "scroll"):
                self._focus_youtube_window()
                rect = self._get_youtube_window_rect()
                amt = max(1, scroll_amount or 6)
                if pyautogui is not None:
                    if rect:
                        pyautogui.moveTo(rect[0] + rect[2] // 2, rect[1] + rect[3] // 2)
                    pyautogui.scroll(-int(amt * 120))
                res = ToolResult(
                    success=True,
                    data={"action": "scroll_down", "amount": amt},
                    message=f"Scrolled YouTube down by {amt} units.",
                )
                log_action(self.name, args_payload, res.message)
                return res

            elif act == "scroll_up":
                self._focus_youtube_window()
                rect = self._get_youtube_window_rect()
                amt = max(1, scroll_amount or 6)
                if pyautogui is not None:
                    if rect:
                        pyautogui.moveTo(rect[0] + rect[2] // 2, rect[1] + rect[3] // 2)
                    pyautogui.scroll(int(amt * 120))
                res = ToolResult(
                    success=True,
                    data={"action": "scroll_up", "amount": amt},
                    message=f"Scrolled YouTube up by {amt} units.",
                )
                log_action(self.name, args_payload, res.message)
                return res

            # ─────────────────────────────────────────────────────────────
            # 5. CLICK AND OPEN VIDEO
            # ─────────────────────────────────────────────────────────────
            elif act in ("click_video", "open_result", "select_video", "click"):
                idx = max(1, int(index or 1))
                # If cached search results exist, open the Nth video URL directly
                if self.__class__._last_search_results and len(self.__class__._last_search_results) >= idx:
                    target = self.__class__._last_search_results[idx - 1]
                    webbrowser.open_new_tab(target["url"])
                    res = ToolResult(
                        success=True,
                        data={"index": idx, "title": target["title"], "url": target["url"]},
                        message=f"Opened video {idx}: '{target['title']}' on YouTube.",
                    )
                    log_action(self.name, args_payload, res.message)
                    return res

                # Otherwise visually click the video card in the active YouTube window
                self._focus_youtube_window()
                rect = self._get_youtube_window_rect()
                if pyautogui is not None:
                    if rect:
                        # Video card 1 is typically ~35% from left and ~38% from top of browser content
                        click_x = rect[0] + int(rect[2] * 0.35)
                        click_y = rect[1] + int(rect[3] * 0.38)
                        pyautogui.click(click_x, click_y)
                    else:
                        pyautogui.click()
                res = ToolResult(
                    success=True,
                    data={"action": "click_video", "index": idx},
                    message=f"Clicked and opened video {idx} on YouTube.",
                )
                log_action(self.name, args_payload, res.message)
                return res

            # ─────────────────────────────────────────────────────────────
            # 6. AUDIO & VOLUME CONTROLS
            # ─────────────────────────────────────────────────────────────
            elif act in ("mute", "unmute", "toggle_mute"):
                self._focus_youtube_window()
                if pyautogui is not None:
                    pyautogui.press("m")
                res = ToolResult(success=True, data={"action": act}, message="Toggled YouTube mute.")
                log_action(self.name, args_payload, res.message)
                return res

            elif act == "volume_up":
                self._focus_youtube_window()
                if pyautogui is not None:
                    pyautogui.press("up", presses=3, interval=0.05)
                res = ToolResult(success=True, data={"action": act}, message="Increased YouTube volume.")
                log_action(self.name, args_payload, res.message)
                return res

            elif act == "volume_down":
                self._focus_youtube_window()
                if pyautogui is not None:
                    pyautogui.press("down", presses=3, interval=0.05)
                res = ToolResult(success=True, data={"action": act}, message="Decreased YouTube volume.")
                log_action(self.name, args_payload, res.message)
                return res

            # ─────────────────────────────────────────────────────────────
            # 7. SEEK / SKIP / NEXT / PREV
            # ─────────────────────────────────────────────────────────────
            elif act in ("skip_forward", "forward", "fast_forward"):
                self._focus_youtube_window()
                if pyautogui is not None:
                    pyautogui.press("l")  # YouTube +10 seconds
                res = ToolResult(success=True, data={"action": act}, message="Skipped forward 10 seconds.")
                log_action(self.name, args_payload, res.message)
                return res

            elif act in ("skip_backward", "rewind", "back"):
                self._focus_youtube_window()
                if pyautogui is not None:
                    pyautogui.press("j")  # YouTube -10 seconds
                res = ToolResult(success=True, data={"action": act}, message="Skipped backward 10 seconds.")
                log_action(self.name, args_payload, res.message)
                return res

            elif act in ("next", "next_video"):
                self._focus_youtube_window()
                if pyautogui is not None:
                    pyautogui.hotkey("shift", "n")
                res = ToolResult(success=True, data={"action": act}, message="Playing next YouTube video.")
                log_action(self.name, args_payload, res.message)
                return res

            elif act in ("prev", "previous", "previous_video"):
                self._focus_youtube_window()
                if pyautogui is not None:
                    pyautogui.hotkey("shift", "p")
                res = ToolResult(success=True, data={"action": act}, message="Playing previous YouTube video.")
                log_action(self.name, args_payload, res.message)
                return res

            elif act in ("restart", "replay"):
                self._focus_youtube_window()
                if pyautogui is not None:
                    pyautogui.press("0")
                res = ToolResult(success=True, data={"action": act}, message="Restarted YouTube video from the beginning.")
                log_action(self.name, args_payload, res.message)
                return res

            # ─────────────────────────────────────────────────────────────
            # 8. CAPTIONS / SPEED / THEATER / MINIPLAYER
            # ─────────────────────────────────────────────────────────────
            elif act in ("captions", "subtitles"):
                self._focus_youtube_window()
                if pyautogui is not None:
                    pyautogui.press("c")
                res = ToolResult(success=True, data={"action": act}, message="Toggled closed captions/subtitles on YouTube.")
                log_action(self.name, args_payload, res.message)
                return res

            elif act in ("speed_up", "faster"):
                self._focus_youtube_window()
                if pyautogui is not None:
                    pyautogui.hotkey("shift", ".")
                res = ToolResult(success=True, data={"action": act}, message="Increased YouTube playback speed.")
                log_action(self.name, args_payload, res.message)
                return res

            elif act in ("slow_down", "slower"):
                self._focus_youtube_window()
                if pyautogui is not None:
                    pyautogui.hotkey("shift", ",")
                res = ToolResult(success=True, data={"action": act}, message="Decreased YouTube playback speed.")
                log_action(self.name, args_payload, res.message)
                return res

            elif act == "theater_mode":
                self._focus_youtube_window()
                if pyautogui is not None:
                    pyautogui.press("t")
                res = ToolResult(success=True, data={"action": act}, message="Toggled YouTube theater mode.")
                log_action(self.name, args_payload, res.message)
                return res

            elif act == "miniplayer":
                self._focus_youtube_window()
                if pyautogui is not None:
                    pyautogui.press("i")
                res = ToolResult(success=True, data={"action": act}, message="Toggled YouTube miniplayer.")
                log_action(self.name, args_payload, res.message)
                return res

            elif act == "search":
                clean_q = (query or "").strip()
                if not clean_q:
                    webbrowser.open_new_tab("https://www.youtube.com")
                    res = ToolResult(success=True, message="Opened YouTube home.")
                else:
                    scraped = self.scrape_youtube_videos(clean_q, max_results=5)
                    self.__class__._last_search_results = scraped
                    search_url = f"https://www.youtube.com/results?search_query={urllib.parse.quote_plus(clean_q)}"
                    webbrowser.open_new_tab(search_url)
                    res = ToolResult(
                        success=True,
                        data={"query": clean_q, "results_count": len(scraped), "url": search_url},
                        message=f"Searched YouTube for '{clean_q}'.",
                    )
                log_action(self.name, args_payload, res.message)
                return res

            else:
                res = ToolResult(
                    success=False,
                    message=f"Unsupported YouTube action '{action}'. Valid actions: play, pause, resume, fullscreen, exit_fullscreen, scroll_down, scroll_up, click_video, mute, volume_up, volume_down, skip_forward, skip_backward, next, prev, captions, speed_up, slow_down, restart, search.",
                )
                log_action(self.name, args_payload, res.message)
                return res

        except Exception as exc:
            logger.exception("YouTube control error: %s", exc)
            res = ToolResult(success=False, message=f"YouTube control failed: {str(exc)}")
            log_action(self.name, args_payload, res.message)
            return res
