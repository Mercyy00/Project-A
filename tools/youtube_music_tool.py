"""
YouTube Music Automation Tool for JARVIS.
Author: Abhijit (System & Automation Engineer)

Provides complete automation and playback control over YouTube Music (https://music.youtube.com):
1. Song Playback: Search and play specific songs, artists, or albums directly.
2. Playback Controls: Pause, resume, toggle play/pause.
3. Track Navigation: Next track ('j' / 'Shift+N'), previous track ('k' / 'Shift+P').
4. Lyrics: Open/toggle the lyrics panel ('e').
5. Tab Management: Reload music tab ('Ctrl+R' / 'F5'), open YouTube Music home/search.
6. Audio & Queue: Volume up ('='), volume down ('-'), mute ('m'), shuffle ('s'), repeat ('r').
7. Reactions & Seek: Like ('+'), dislike ('_'), seek forward ('l'), seek backward ('h').
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
    from tools.guard import is_stopped, log_action
except ImportError:
    def is_stopped() -> bool:
        return False

    def log_action(tool_name: str, args: Any, result_summary: Any) -> None:
        pass


class YouTubeMusicTool(BaseTool):
    """Controls YouTube Music playback, track navigation, lyrics, and tab state."""
    name: str = "youtube_music_control"
    description: str = (
        "Controls YouTube Music (music.youtube.com): play songs, pause/resume, "
        "play next song, play previous song, open lyrics section, reload music tab, "
        "search songs, adjust volume, seek, like/dislike, shuffle, and repeat."
    )

    _last_played_song: str = ""
    _last_played_url: str = ""

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
                            "play",
                            "pause",
                            "resume",
                            "toggle_play",
                            "next_song",
                            "prev_song",
                            "lyrics",
                            "reload",
                            "search",
                            "open",
                            "volume_up",
                            "volume_down",
                            "mute",
                            "shuffle",
                            "repeat",
                            "like",
                            "dislike",
                            "seek_forward",
                            "seek_backward",
                        ],
                        "description": "YouTube Music action to perform.",
                    },
                    "query": {
                        "type": "string",
                        "description": "Song title, artist, or album name to search or play.",
                    },
                    "video_id": {
                        "type": "string",
                        "description": "Specific 11-character YouTube video/music ID to stream.",
                    },
                    "volume_step": {
                        "type": "integer",
                        "description": "Number of volume steps to increase or decrease (default 2).",
                    },
                    "seek_seconds": {
                        "type": "integer",
                        "description": "Seconds to seek forward or backward (default 10).",
                    },
                },
                "required": ["action"],
            },
        }

    # -------------------------------------------------------------------------
    # Window Management & Focusing
    # -------------------------------------------------------------------------

    @classmethod
    def _focus_music_window(cls) -> bool:
        """Finds and foregrounds the YouTube Music window or active browser tab."""
        # 1. Native Windows API
        try:
            import ctypes
            from ctypes import wintypes
            user32 = ctypes.windll.user32

            def _raise(h: int) -> bool:
                try:
                    if user32.IsIconic(h):
                        user32.ShowWindow(h, 9)  # SW_RESTORE
                    ours = ctypes.windll.kernel32.GetCurrentThreadId()
                    their = user32.GetWindowThreadProcessId(h, None)
                    if ours != their:
                        user32.AttachThreadInput(ours, their, True)
                    try:
                        user32.BringWindowToTop(h)
                        user32.SetForegroundWindow(h)
                        user32.SetFocus(h)
                        return True
                    finally:
                        if ours != their:
                            user32.AttachThreadInput(ours, their, False)
                    return False
                except Exception:
                    return False

            music_hwnds: List[int] = []
            browser_hwnds: List[int] = []

            def _enum_cb(hwnd: int, _lparam: Any) -> bool:
                if user32.IsWindow(hwnd) and user32.IsWindowVisible(hwnd):
                    length = user32.GetWindowTextLengthW(hwnd)
                    if length > 0:
                        buff = ctypes.create_unicode_buffer(length + 1)
                        user32.GetWindowTextW(hwnd, buff, length + 1)
                        title = buff.value.lower()
                        if "youtube music" in title or "music.youtube" in title:
                            music_hwnds.append(hwnd)
                        elif "youtube" in title or any(b in title for b in ("chrome", "edge", "brave", "firefox", "opera")):
                            browser_hwnds.append(hwnd)
                return True

            WNDENUM = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
            user32.EnumWindows(WNDENUM(_enum_cb), 0)

            # Prioritize dedicated YouTube Music window, then browser
            for h in music_hwnds + browser_hwnds:
                if _raise(h):
                    time.sleep(0.15)
                    return True

        except Exception as exc:
            logger.debug("Win32 window focus failed: %s", exc)

        # 2. PyGetWindow fallback
        if gw is not None:
            try:
                for w in gw.getAllWindows():
                    t = getattr(w, "title", "").lower()
                    if ("youtube music" in t or "music.youtube" in t) and getattr(w, "visible", True):
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
                    if ("youtube" in t or any(b in t for b in ("chrome", "edge", "brave", "firefox"))) and getattr(w, "visible", True):
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
    def _send_hotkey(cls, *keys: str) -> bool:
        """Sends hotkey to the currently focused YouTube Music window."""
        if pyautogui is None:
            return False
        try:
            pyautogui.hotkey(*keys)
            return True
        except Exception as exc:
            logger.debug("Failed sending hotkey %s: %s", keys, exc)
            return False

    @classmethod
    def _send_key(cls, key: str, presses: int = 1) -> bool:
        """Presses a single key one or multiple times."""
        if pyautogui is None:
            return False
        try:
            for _ in range(presses):
                pyautogui.press(key)
                time.sleep(0.05)
            return True
        except Exception as exc:
            logger.debug("Failed pressing key %s: %s", key, exc)
            return False

    # -------------------------------------------------------------------------
    # Execution Dispatcher
    # -------------------------------------------------------------------------

    def run(self, **kwargs: Any) -> ToolResult:
        """Executes YouTube Music commands synchronously."""
        return self._execute_sync(**kwargs)

    async def execute(self, **kwargs: Any) -> ToolResult:
        """Executes YouTube Music commands asynchronously."""
        return self._execute_sync(**kwargs)

    def _execute_sync(self, **kwargs: Any) -> ToolResult:
        """Executes YouTube Music commands safely."""
        if is_stopped():
            return ToolResult(success=False, message="Action aborted: Emergency stop is active.")

        action = (kwargs.get("action") or "").lower().strip()
        query = (kwargs.get("query") or "").strip()
        video_id = (kwargs.get("video_id") or "").strip()
        volume_step = kwargs.get("volume_step", 2)
        seek_seconds = kwargs.get("seek_seconds", 10)

        logger.info("Executing YouTube Music action '%s' with query='%s'", action, query)

        try:
            if action in ("play", "start"):
                return self._action_play(query, video_id)
            elif action == "search":
                return self._action_search(query)
            elif action in ("pause", "stop"):
                return self._action_pause()
            elif action == "resume":
                return self._action_resume()
            elif action == "toggle_play":
                return self._action_toggle_play()
            elif action in ("next_song", "next_track", "skip", "next"):
                return self._action_next_song()
            elif action in ("prev_song", "prev_track", "previous_song", "previous", "prev"):
                return self._action_prev_song()
            elif action in ("lyrics", "show_lyrics", "open_lyrics", "lyrics_section"):
                return self._action_lyrics()
            elif action in ("reload", "refresh", "reload_tab"):
                return self._action_reload()
            elif action in ("open", "open_music", "home"):
                return self._action_open_home()
            elif action == "volume_up":
                return self._action_volume_up(volume_step)
            elif action == "volume_down":
                return self._action_volume_down(volume_step)
            elif action in ("mute", "unmute"):
                return self._action_mute()
            elif action == "shuffle":
                return self._action_shuffle()
            elif action == "repeat":
                return self._action_repeat()
            elif action == "like":
                return self._action_like()
            elif action == "dislike":
                return self._action_dislike()
            elif action == "seek_forward":
                return self._action_seek(forward=True, seconds=seek_seconds)
            elif action == "seek_backward":
                return self._action_seek(forward=False, seconds=seek_seconds)
            else:
                return ToolResult(
                    success=False,
                    message=f"Unknown YouTube Music action '{action}'. Valid actions include: "
                            "play, search, pause, resume, toggle_play, next_song, prev_song, "
                            "lyrics, reload, volume_up, volume_down, mute, shuffle, repeat, like, dislike.",
                )
        except Exception as exc:
            logger.exception("YouTube Music execution error for action '%s': %s", action, exc)
            return ToolResult(
                success=False,
                message=f"YouTube Music control error: {str(exc)}",
                data={"action": action, "error": str(exc)},
            )

    # -------------------------------------------------------------------------
    # Core Actions
    # -------------------------------------------------------------------------

    def _action_play(self, query: str, video_id: str) -> ToolResult:
        """Plays a song directly on YouTube Music."""
        # 1. Direct video ID
        if video_id:
            clean_id = re.sub(r"[^a-zA-Z0-9_-]", "", video_id)
            url = f"https://music.youtube.com/watch?v={clean_id}"
            webbrowser.open(url)
            self._last_played_song = video_id
            self._last_played_url = url
            return ToolResult(
                success=True,
                message=f"Playing video ID '{clean_id}' on YouTube Music.",
                data={"action": "play", "url": url, "video_id": clean_id},
            )

        # 2. If query provided: scrape top video or open music search
        if query:
            clean_q = re.sub(r"^(?:play|listen\s+to|stream|youtube\s+music|yt\s+music)\s+", "", query, flags=re.IGNORECASE).strip()
            clean_q = re.sub(r"\s+(?:on|in)\s+(?:youtube\s+music|yt\s+music)$", "", clean_q, flags=re.IGNORECASE).strip()
            if clean_q.lower() in ("song", "songs", "some songs", "music", "some music", "a song", "tracks", "play"):
                clean_q = "top hit songs"

            top_video_id: Optional[str] = None
            song_title = clean_q

            # Scrape top YouTube ID (fully valid on music.youtube.com)
            try:
                from tools.youtube_tool import YouTubeControlTool
                results = YouTubeControlTool.scrape_youtube_videos(f"{clean_q} song", max_results=3)
                if not results:
                    results = YouTubeControlTool.scrape_youtube_videos(clean_q, max_results=3)
                if results:
                    top_video_id = results[0].get("id") or results[0].get("video_id")
                    song_title = results[0].get("title", clean_q)
            except Exception as exc:
                logger.debug("Scraping for YT Music query '%s' failed: %s", clean_q, exc)

            if top_video_id:
                url = f"https://music.youtube.com/watch?v={top_video_id}"
                webbrowser.open(url)
                self._last_played_song = song_title
                self._last_played_url = url
                time.sleep(0.3)
                self._focus_music_window()
                return ToolResult(
                    success=True,
                    message=f"Playing '{song_title}' on YouTube Music.",
                    data={"action": "play", "title": song_title, "url": url, "video_id": top_video_id},
                )
            else:
                # Direct YouTube Music search URL
                search_url = f"https://music.youtube.com/search?q={urllib.parse.quote_plus(clean_q)}"
                webbrowser.open(search_url)
                self._last_played_song = clean_q
                self._last_played_url = search_url
                time.sleep(0.3)
                self._focus_music_window()
                return ToolResult(
                    success=True,
                    message=f"Searching for '{clean_q}' on YouTube Music.",
                    data={"action": "search", "query": clean_q, "url": search_url},
                )

        # 3. If no query or ID: resume existing music in active window
        self._focus_music_window()
        self._send_key("space")
        return ToolResult(
            success=True,
            message="Resumed YouTube Music playback.",
            data={"action": "resume"},
        )

    def _action_search(self, query: str) -> ToolResult:
        """Performs a search on YouTube Music."""
        if not query:
            url = "https://music.youtube.com"
            webbrowser.open(url)
            return ToolResult(success=True, message="Opened YouTube Music home page.", data={"url": url})

        clean_q = re.sub(r"^(?:search|look\s+for|find)\s+", "", query, flags=re.IGNORECASE).strip()
        clean_q = re.sub(r"\s+(?:on|in)\s+(?:youtube\s+music|yt\s+music)$", "", clean_q, flags=re.IGNORECASE).strip()

        url = f"https://music.youtube.com/search?q={urllib.parse.quote_plus(clean_q)}"
        webbrowser.open(url)
        time.sleep(0.3)
        self._focus_music_window()
        return ToolResult(
            success=True,
            message=f"Searching YouTube Music for '{clean_q}'.",
            data={"action": "search", "query": clean_q, "url": url},
        )

    def _action_pause(self) -> ToolResult:
        """Pauses YouTube Music playback."""
        self._focus_music_window()
        self._send_key("space")
        return ToolResult(success=True, message="Paused YouTube Music playback.", data={"action": "pause"})

    def _action_resume(self) -> ToolResult:
        """Resumes YouTube Music playback."""
        self._focus_music_window()
        self._send_key("space")
        return ToolResult(success=True, message="Resumed YouTube Music playback.", data={"action": "resume"})

    def _action_toggle_play(self) -> ToolResult:
        """Toggles YouTube Music playback between play and pause."""
        self._focus_music_window()
        self._send_key("space")
        return ToolResult(success=True, message="Toggled YouTube Music playback.", data={"action": "toggle_play"})

    def _action_next_song(self) -> ToolResult:
        """Plays the next song in queue ('j' or 'Shift+N')."""
        self._focus_music_window()
        # YouTube Music shortcut 'j' jumps to next track; Shift+N is YouTube standard
        self._send_key("j")
        time.sleep(0.05)
        self._send_hotkey("shift", "n")
        return ToolResult(success=True, message="Skipped to next song on YouTube Music.", data={"action": "next_song"})

    def _action_prev_song(self) -> ToolResult:
        """Plays the previous song in queue ('k' or 'Shift+P')."""
        self._focus_music_window()
        # YouTube Music shortcut 'k' goes to previous track; Shift+P is YouTube standard
        self._send_key("k")
        time.sleep(0.05)
        self._send_hotkey("shift", "p")
        return ToolResult(success=True, message="Playing previous song on YouTube Music.", data={"action": "prev_song"})

    def _action_lyrics(self) -> ToolResult:
        """Toggles the lyrics section in YouTube Music ('e' or clicking lyrics tab)."""
        self._focus_music_window()
        # YouTube Music web keyboard shortcut 'e' or clicking the lyrics tab opens lyrics
        self._send_key("e")
        return ToolResult(
            success=True,
            message="Opened/toggled lyrics section on YouTube Music.",
            data={"action": "lyrics"},
        )

    def _action_reload(self) -> ToolResult:
        """Reloads the YouTube Music browser tab ('Ctrl+R')."""
        self._focus_music_window()
        self._send_hotkey("ctrl", "r")
        return ToolResult(success=True, message="Reloaded YouTube Music tab.", data={"action": "reload"})

    def _action_open_home(self) -> ToolResult:
        """Opens YouTube Music homepage."""
        url = "https://music.youtube.com"
        webbrowser.open(url)
        return ToolResult(success=True, message="Opened YouTube Music.", data={"action": "open", "url": url})

    def _action_volume_up(self, steps: int = 2) -> ToolResult:
        """Increases YouTube Music volume ('=')."""
        self._focus_music_window()
        # YouTube Music uses '=' for volume up
        self._send_key("=", presses=max(1, steps))
        return ToolResult(
            success=True,
            message=f"Increased YouTube Music volume by {steps} steps.",
            data={"action": "volume_up", "steps": steps},
        )

    def _action_volume_down(self, steps: int = 2) -> ToolResult:
        """Decreases YouTube Music volume ('-')."""
        self._focus_music_window()
        # YouTube Music uses '-' for volume down
        self._send_key("-", presses=max(1, steps))
        return ToolResult(
            success=True,
            message=f"Decreased YouTube Music volume by {steps} steps.",
            data={"action": "volume_down", "steps": steps},
        )

    def _action_mute(self) -> ToolResult:
        """Toggles mute on YouTube Music ('m')."""
        self._focus_music_window()
        self._send_key("m")
        return ToolResult(success=True, message="Toggled mute on YouTube Music.", data={"action": "mute"})

    def _action_shuffle(self) -> ToolResult:
        """Toggles shuffle mode on YouTube Music ('s')."""
        self._focus_music_window()
        self._send_key("s")
        return ToolResult(success=True, message="Toggled shuffle mode on YouTube Music.", data={"action": "shuffle"})

    def _action_repeat(self) -> ToolResult:
        """Cycles repeat mode on YouTube Music ('r')."""
        self._focus_music_window()
        self._send_key("r")
        return ToolResult(success=True, message="Cycled repeat mode on YouTube Music.", data={"action": "repeat"})

    def _action_like(self) -> ToolResult:
        """Likes current song on YouTube Music ('+')."""
        self._focus_music_window()
        self._send_key("+")
        return ToolResult(success=True, message="Liked current song on YouTube Music.", data={"action": "like"})

    def _action_dislike(self) -> ToolResult:
        """Dislikes current song on YouTube Music ('_')."""
        self._focus_music_window()
        self._send_key("_")
        return ToolResult(success=True, message="Disliked current song on YouTube Music.", data={"action": "dislike"})

    def _action_seek(self, forward: bool, seconds: int = 10) -> ToolResult:
        """Seeks playback forward ('l') or backward ('h')."""
        self._focus_music_window()
        key = "l" if forward else "h"
        presses = max(1, seconds // 10)
        self._send_key(key, presses=presses)
        dir_text = "forward" if forward else "backward"
        return ToolResult(
            success=True,
            message=f"Seeked {dir_text} by {presses * 10}s on YouTube Music.",
            data={"action": "seek", "direction": dir_text, "seconds": presses * 10},
        )
