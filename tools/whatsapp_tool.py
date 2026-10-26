"""
WhatsApp Desktop and Web Automation Tool.
Author: Abhijit (System & Automation Engineer)

Provides multi-step conversational WhatsApp control:
1. Open/Focus WhatsApp desktop application via Windows Search automation (Win -> 'WhatsApp' -> Enter).
2. Verify WhatsApp window presence and state before performing operations.
3. Search and open contact conversation via keyboard automation.
4. Message the searched contact or current chat with full Unicode support.
"""

import os
import re
import subprocess
import time
from typing import Any, Dict, Optional
import urllib.parse

from tools.base import BaseTool, ToolResult

# Safe PyAutoGUI and Pyperclip imports with graceful fallbacks
try:
    import pyautogui
    pyautogui.PAUSE = 0.1
    pyautogui.FAILSAFE = False
except ImportError:
    pyautogui = None  # type: ignore

try:
    import pyperclip
except ImportError:
    pyperclip = None  # type: ignore

try:
    from tools.guard import is_stopped, log_action
except ImportError:
    def is_stopped() -> bool:
        return False

    def log_action(tool_name: str, args: Any, result_summary: Any) -> None:
        pass


def _ensure_input_desktop() -> None:
    """Ensures the calling thread is attached to the active interactive input desktop on Windows."""
    if os.name != "nt":
        return
    try:
        import ctypes
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        # DESKTOP_ALL_ACCESS = 0x01FF
        h_desk = user32.OpenInputDesktop(0, False, 0x01FF)
        if h_desk:
            user32.SetThreadDesktop(h_desk)
    except Exception:
        pass


class WhatsAppTool(BaseTool):
    """Tool for automating WhatsApp desktop and web interactions."""
    name: str = "whatsapp_control"
    description: str = (
        "Automates WhatsApp interactions on Windows. "
        "Supports opening WhatsApp ('open'), searching a contact ('search'), "
        "and sending a message to a contact or the active chat ('send')."
    )

    # State tracking for conversational follow-ups
    _last_searched_contact: Optional[str] = None

    @classmethod
    def _find_whatsapp_window(cls) -> Optional[int]:
        """Finds and returns the HWND of an active or minimized WhatsApp application window on Windows.

        Returns:
            Optional[int]: HWND handle of the WhatsApp window if found, else None.
        """
        if os.name != "nt":
            return None

        _ensure_input_desktop()

        try:
            import ctypes
            from ctypes import wintypes
            import psutil

            user32 = ctypes.WinDLL("user32", use_last_error=True)

            found_hwnd: Optional[int] = None

            def _enum_cb(hwnd: int, _lparam: Any) -> bool:
                nonlocal found_hwnd
                if not user32.IsWindow(hwnd):
                    return True
                # Check visibility or minimized state
                if not (user32.IsWindowVisible(hwnd) or user32.IsIconic(hwnd)):
                    return True

                length = user32.GetWindowTextLengthW(hwnd)
                title = ""
                if length > 0:
                    buff = ctypes.create_unicode_buffer(length + 1)
                    user32.GetWindowTextW(hwnd, buff, length + 1)
                    title = buff.value.strip().lower()

                # Exclude developer tools, IDEs, editors, shells that might contain 'whatsapp' in the title
                ignore_kw = ("visual studio", "code", "pycharm", "sublime", "notepad", "terminal", "powershell", "cmd.exe", "test")
                if any(kw in title for kw in ignore_kw):
                    return True

                owner_pid = wintypes.DWORD()
                user32.GetWindowThreadProcessId(hwnd, ctypes.byref(owner_pid))
                proc_name = ""
                try:
                    proc = psutil.Process(owner_pid.value)
                    proc_name = (proc.name() or "").lower()
                except Exception:
                    pass

                is_wa_proc = "whatsapp" in proc_name
                is_wa_title = title == "whatsapp" or title.startswith("whatsapp") or title.endswith("whatsapp")

                if is_wa_proc or is_wa_title:
                    found_hwnd = hwnd
                    return False  # Found, stop enumeration
                return True

            WNDENUM = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
            user32.EnumWindows(WNDENUM(_enum_cb), 0)
            return found_hwnd
        except Exception:
            return None

    @classmethod
    def _is_whatsapp_window_open(cls) -> bool:
        """Checks if a valid WhatsApp window is open on the system."""
        return cls._find_whatsapp_window() is not None

    @classmethod
    def _raise_window(cls, hwnd: int) -> bool:
        """Restores and brings a window to the foreground with keyboard input focus."""
        if os.name != "nt" or not hwnd:
            return False
        try:
            import ctypes
            user32 = ctypes.WinDLL("user32", use_last_error=True)
            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            SW_RESTORE = 9

            if user32.IsIconic(hwnd):
                user32.ShowWindow(hwnd, SW_RESTORE)
            user32.BringWindowToTop(hwnd)
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

    @classmethod
    def _open_via_windows_search(cls) -> bool:
        """Opens WhatsApp via the Windows Start Search bar.

        Presses Windows key -> types 'WhatsApp' -> presses Enter.
        This provides 100% reliable discovery and launch across all Windows installations.
        """
        if pyautogui is None:
            return False
        try:
            _ensure_input_desktop()
            pyautogui.press("win")
            time.sleep(0.4)
            pyautogui.write("WhatsApp", interval=0.03)
            time.sleep(0.4)
            pyautogui.press("enter")
            time.sleep(1.2)
            return True
        except Exception:
            return False

    @classmethod
    def _wait_for_whatsapp_window(cls, timeout_seconds: float = 4.0) -> Optional[int]:
        """Polls until a WhatsApp window is detected or timeout expires."""
        deadline = time.time() + timeout_seconds
        while time.time() < deadline:
            hwnd = cls._find_whatsapp_window()
            if hwnd:
                return hwnd
            time.sleep(0.4)
        return None

    @classmethod
    def _focus_whatsapp_window(cls) -> bool:
        """Brings WhatsApp to the foreground, opening it via Windows Search if not already running.

        Returns True ONLY if a WhatsApp window is confirmed open and active.
        Returns False if WhatsApp could not be opened or verified.
        """
        if os.name != "nt":
            return False

        _ensure_input_desktop()

        # 1. If WhatsApp window already exists, restore and focus it
        hwnd = cls._find_whatsapp_window()
        if hwnd:
            cls._raise_window(hwnd)
            time.sleep(0.3)
            return True

        # 2. Open via Windows Search: Win key -> "WhatsApp" -> Enter
        cls._open_via_windows_search()
        hwnd = cls._wait_for_whatsapp_window(timeout_seconds=4.0)
        if hwnd:
            cls._raise_window(hwnd)
            time.sleep(0.4)
            return True

        # 3. Protocol launch fallback in case Start Menu search was delayed
        try:
            subprocess.Popen("cmd.exe /c start whatsapp:", shell=True)
            hwnd = cls._wait_for_whatsapp_window(timeout_seconds=2.5)
            if hwnd:
                cls._raise_window(hwnd)
                time.sleep(0.4)
                return True
        except Exception:
            pass

        return False

    def run(
        self,
        action: str = "open",
        contact: Optional[str] = None,
        message: Optional[str] = None,
        **kwargs: Any
    ) -> ToolResult:
        """Executes a WhatsApp automation command.

        Args:
            action: Action to perform ('open', 'search', or 'send'). Defaults to 'open'.
            contact: Name or phone number of the contact to search or message.
            message: Message text to type and send.
            **kwargs: Extra parameters.

        Returns:
            ToolResult: Execution outcome with status and details.
        """
        args_payload = {"action": action, "contact": contact, "message": message}
        try:
            if is_stopped():
                res = ToolResult(
                    success=False,
                    data=None,
                    message="Execution stopped: Kill switch is active."
                )
                log_action(self.name, args_payload, res.message)
                return res

            clean_action = str(action).strip().lower()

            if clean_action in ("open", "launch", "start", "focus"):
                res = self.open_whatsapp()
                log_action(self.name, args_payload, res.message)
                return res

            elif clean_action in ("search", "search_contact", "find", "find_contact"):
                target_contact = (contact or kwargs.get("name") or kwargs.get("query") or "").strip()
                if not target_contact:
                    return ToolResult(
                        success=False,
                        data=None,
                        message="Missing required parameter: 'contact' must be provided to search."
                    )
                res = self.search_contact(target_contact)
                log_action(self.name, args_payload, res.message)
                return res

            elif clean_action in ("send", "send_message", "message", "text"):
                target_msg = (message or kwargs.get("text") or kwargs.get("content") or "").strip()
                if not target_msg:
                    return ToolResult(
                        success=False,
                        data=None,
                        message="Missing required parameter: 'message' must be provided to send."
                    )
                target_contact = contact or kwargs.get("to") or kwargs.get("recipient")
                res = self.send_message(target_msg, contact=target_contact)
                log_action(self.name, args_payload, res.message)
                return res

            else:
                return ToolResult(
                    success=False,
                    data=None,
                    message=f"Unknown WhatsApp action '{action}'. Valid actions are 'open', 'search', and 'send'."
                )

        except Exception as exc:
            res = ToolResult(
                success=False,
                data={"error": str(exc)},
                message=f"Failed to execute WhatsApp action '{action}': {exc}"
            )
            log_action(self.name, args_payload, res.message)
            return res

    def open_whatsapp(self) -> ToolResult:
        """Opens or brings WhatsApp Desktop to the foreground using Windows Search automation.

        Verifies that the WhatsApp window is actually open and active before returning success.

        Returns:
            ToolResult: Status indicating whether WhatsApp was opened and verified.
        """
        try:
            if self._focus_whatsapp_window():
                return ToolResult(
                    success=True,
                    data={"target": "whatsapp", "method": "windows_search"},
                    message="WhatsApp opened and brought to focus."
                )
            else:
                return ToolResult(
                    success=False,
                    data={"target": "whatsapp", "error": "window_not_found"},
                    message="WhatsApp could not be opened on your machine. Please ensure WhatsApp desktop is installed and logged in."
                )
        except Exception as exc:
            return ToolResult(
                success=False,
                data={"error": str(exc)},
                message=f"Could not open WhatsApp: {exc}"
            )

    def search_contact(self, contact: str) -> ToolResult:
        """Searches for a contact in WhatsApp and opens their chat conversation.

        Args:
            contact: Name or phone number of the contact.

        Returns:
            ToolResult: Status indicating whether contact search was dispatched.
        """
        try:
            cleaned = contact.strip()
            if not cleaned:
                return ToolResult(
                    success=False,
                    data=None,
                    message="Missing required parameter: 'contact' must be provided to search."
                )

            # Ensure WhatsApp window is active and brought to foreground
            if not self._focus_whatsapp_window():
                return ToolResult(
                    success=False,
                    data={"contact": cleaned, "error": "whatsapp_not_open"},
                    message="WhatsApp is not open or could not be brought to the foreground. Please make sure WhatsApp is installed and running."
                )
            time.sleep(0.4)

            if pyautogui is None:
                return ToolResult(
                    success=False,
                    data=None,
                    message="pyautogui is required for keyboard search automation."
                )

            # 1. Clear any active dialog or in-chat search panel
            pyautogui.press("esc")
            time.sleep(0.1)
            pyautogui.press("esc")
            time.sleep(0.2)

            # 2. Focus search bar in WhatsApp via Ctrl+F shortcut
            pyautogui.hotkey("ctrl", "f")
            time.sleep(0.3)

            # 3. Clear existing search text
            pyautogui.hotkey("ctrl", "a")
            time.sleep(0.1)
            pyautogui.press("backspace")
            time.sleep(0.1)

            # 4. Enter contact name via clipboard paste (supports Unicode & special characters)
            if pyperclip is not None:
                pyperclip.copy(cleaned)
                time.sleep(0.1)
                pyautogui.hotkey("ctrl", "v")
            else:
                pyautogui.write(cleaned, interval=0.03)

            # 5. Wait for WhatsApp to filter contacts
            time.sleep(0.8)

            # 6. Press Enter to open the top matched conversation
            pyautogui.press("enter")
            time.sleep(0.5)

            WhatsAppTool._last_searched_contact = cleaned

            return ToolResult(
                success=True,
                data={"contact": cleaned},
                message=f"Searched for '{cleaned}' in WhatsApp and opened chat conversation."
            )
        except Exception as exc:
            return ToolResult(
                success=False,
                data={"contact": contact, "error": str(exc)},
                message=f"Failed to search contact '{contact}' in WhatsApp: {exc}"
            )

    def send_message(self, message: str, contact: Optional[str] = None) -> ToolResult:
        """Types and sends a message in WhatsApp.

        If contact is specified, searches the contact first. If omitted,
        sends to the currently active conversation or last searched contact.

        Args:
            message: Text to send.
            contact: Optional contact name.

        Returns:
            ToolResult: Status indicating whether message was dispatched.
        """
        try:
            clean_msg = message.strip()
            if not clean_msg:
                return ToolResult(
                    success=False,
                    data=None,
                    message="Missing required parameter: 'message' must be provided to send."
                )

            explicit_contact = (contact or "").strip()
            target_contact = explicit_contact or WhatsAppTool._last_searched_contact or ""

            # If contact is a direct phone number, use WhatsApp protocol URI
            digits_only = re.sub(r"[^\d+]", "", target_contact) if target_contact else ""
            if len(digits_only) >= 10 and digits_only.lstrip("+").isdigit():
                encoded_msg = urllib.parse.quote(clean_msg)
                phone_num = digits_only.lstrip("+")
                uri = f"whatsapp://send?phone={phone_num}&text={encoded_msg}"
                if os.name == "nt":
                    subprocess.Popen(f'cmd.exe /c start "{uri}"', shell=True)
                    time.sleep(1.0)
                    if not self._is_whatsapp_window_open():
                        self._open_via_windows_search()
                        hwnd = self._wait_for_whatsapp_window(timeout_seconds=3.0)
                        if hwnd:
                            self._raise_window(hwnd)
                    if not self._is_whatsapp_window_open():
                        return ToolResult(
                            success=False,
                            data={"contact": target_contact, "error": "whatsapp_not_open"},
                            message="WhatsApp is not open or could not be focused. Message was not sent."
                        )
                    if pyautogui is not None:
                        pyautogui.press("enter")
                    return ToolResult(
                        success=True,
                        data={"contact": target_contact, "message": clean_msg, "method": "protocol"},
                        message=f"Sent message to {target_contact} via WhatsApp direct protocol."
                    )

            # If explicit contact name is given and different from last searched, search and open first
            if explicit_contact and explicit_contact.lower() != (WhatsAppTool._last_searched_contact or "").lower():
                search_res = self.search_contact(explicit_contact)
                if not search_res.success:
                    return search_res
                time.sleep(0.5)
            else:
                # Target is currently open chat (or last searched contact)
                if not self._focus_whatsapp_window():
                    return ToolResult(
                        success=False,
                        data={"contact": target_contact, "error": "whatsapp_not_open"},
                        message="WhatsApp is not open or could not be focused. Message was not sent."
                    )
                time.sleep(0.4)

            if pyautogui is None:
                return ToolResult(
                    success=False,
                    data=None,
                    message="pyautogui is required for message automation."
                )

            # Paste message into active conversation input box
            if pyperclip is not None:
                pyperclip.copy(clean_msg)
                time.sleep(0.1)
                pyautogui.hotkey("ctrl", "v")
            else:
                pyautogui.write(clean_msg, interval=0.02)

            time.sleep(0.3)
            # Press Enter to transmit message
            pyautogui.press("enter")
            time.sleep(0.3)

            recipient_label = target_contact if target_contact else "active conversation"
            return ToolResult(
                success=True,
                data={"contact": recipient_label, "message": clean_msg},
                message=f"Message successfully sent to {recipient_label} in WhatsApp: '{clean_msg}'"
            )
        except Exception as exc:
            return ToolResult(
                success=False,
                data={"error": str(exc)},
                message=f"Failed to send WhatsApp message: {exc}"
            )

    def get_schema(self) -> Dict[str, Any]:
        """Returns JSON schema definition for LLM tool/function calling."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "description": "WhatsApp action to perform: 'open', 'search', or 'send'.",
                        "enum": ["open", "search", "send"]
                    },
                    "contact": {
                        "type": "string",
                        "description": "Name or phone number of the contact to search or message."
                    },
                    "message": {
                        "type": "string",
                        "description": "Text message content to type and send."
                    }
                },
                "required": ["action"]
            }
        }
