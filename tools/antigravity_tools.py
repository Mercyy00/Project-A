"""
Google Antigravity Desktop Agent and IDE Automation Tool for JARVIS.
Author: Abhijit (System & Automation Engineer)

Provides full automation over the Google Antigravity desktop application (Antigravity.lnk):
1. Launch & Focus: Launches Antigravity via Desktop shortcut (C:\\Users\\Perfect\\Desktop\\Antigravity.lnk) or executable and brings it to foreground.
2. Open Folders: Opens any folder or project directly in Antigravity.
3. New Chats: Opens new conversations/chats in Antigravity (Ctrl+L / Ctrl+Shift+L).
4. Prompt Formulation: Writes prompts with model selection, effort/priority directives (e.g. Gemini 3.8 Flash (High)), and media/file attachments (@file).
5. Send Prompt: Pastes and sends prompts into Antigravity chat automatically with hotkey execution (Ctrl+V -> Enter).
"""

from __future__ import annotations

import logging
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from tools.base import BaseTool, ToolResult

logger = logging.getLogger(__name__)

try:
    import pyautogui
    pyautogui.PAUSE = 0.1
    pyautogui.FAILSAFE = False
except ImportError:
    pyautogui = None  # type: ignore

try:
    import pyperclip
    _PYPERCLIP_OK = True
except ImportError:
    _PYPERCLIP_OK = False

ANTIGRAVITY_SHORTCUT = os.path.expanduser(r"~\Desktop\Antigravity.lnk")
ANTIGRAVITY_EXE = os.path.expanduser(r"~\AppData\Local\Programs\antigravity\Antigravity.exe")
ANTIGRAVITY_START_LNK = os.path.expanduser(r"~\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Antigravity.lnk")


def get_antigravity_launch_target() -> Optional[str]:
    """Finds the best path or shortcut to launch Google Antigravity."""
    for p in (ANTIGRAVITY_SHORTCUT, ANTIGRAVITY_EXE, ANTIGRAVITY_START_LNK):
        if os.path.exists(p):
            return p
    return None


def focus_antigravity_window() -> bool:
    """Finds and foregrounds the Google Antigravity IDE window."""
    if sys.platform != "win32":
        return False
    try:
        import ctypes
        from ctypes import wintypes
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32

        def _raise(hwnd: int) -> bool:
            try:
                if user32.IsIconic(hwnd):
                    user32.ShowWindow(hwnd, 9)  # SW_RESTORE
                ours = kernel32.GetCurrentThreadId()
                their = user32.GetWindowThreadProcessId(hwnd, None)
                if ours != their:
                    user32.AttachThreadInput(ours, their, True)
                try:
                    user32.BringWindowToTop(hwnd)
                    user32.SetForegroundWindow(hwnd)
                    user32.SetFocus(hwnd)
                    return True
                finally:
                    if ours != their:
                        user32.AttachThreadInput(ours, their, False)
            except Exception:
                return False
            return False

        antigravity_hwnds: List[int] = []

        def _enum_cb(hwnd: int, _lparam: Any) -> bool:
            if user32.IsWindow(hwnd) and user32.IsWindowVisible(hwnd):
                length = user32.GetWindowTextLengthW(hwnd)
                if length > 0:
                    buff = ctypes.create_unicode_buffer(length + 1)
                    user32.GetWindowTextW(hwnd, buff, length + 1)
                    title = buff.value.lower()
                    if "antigravity" in title:
                        antigravity_hwnds.append(hwnd)
            return True

        WNDENUM = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        user32.EnumWindows(WNDENUM(_enum_cb), 0)

        for h in antigravity_hwnds:
            if _raise(h):
                time.sleep(0.15)
                return True
    except Exception as exc:
        logger.debug("Win32 Antigravity window focus failed: %s", exc)

    return False


class AntigravityControlTool(BaseTool):
    """Automates the Google Antigravity desktop IDE, chat prompts, model selection, and folders."""
    name: str = "antigravity_control"
    description: str = (
        "Controls Google Antigravity desktop IDE (Antigravity.lnk): launch or focus the application, "
        "open folders/workspaces, start new chats, select models (e.g. Gemini 3.8 Flash High) and effort, "
        "attach files or media, write prompts, and send them directly into the Antigravity chat."
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
                        "enum": [
                            "launch",
                            "focus",
                            "open_folder",
                            "new_chat",
                            "send_prompt",
                            "write_prompt",
                            "choose_model",
                        ],
                        "description": "Antigravity action to execute.",
                    },
                    "prompt": {
                        "type": "string",
                        "description": "Coding prompt or task description to send or write.",
                    },
                    "task": {
                        "type": "string",
                        "description": "Alias for prompt.",
                    },
                    "folder_path": {
                        "type": "string",
                        "description": "Directory path to open in Antigravity.",
                    },
                    "model": {
                        "type": "string",
                        "description": "AI model to select (e.g. 'Gemini 3.8 Flash', 'Gemini 3.8 Pro').",
                        "default": "Gemini 3.8 Flash",
                    },
                    "effort": {
                        "type": "string",
                        "enum": ["High", "Medium", "Default"],
                        "description": "Model effort level / thinking budget (e.g. 'High').",
                        "default": "High",
                    },
                    "priority": {
                        "type": "string",
                        "description": "Priority level for the task.",
                        "default": "High",
                    },
                    "attachment": {
                        "type": "string",
                        "description": "File or media path to attach to the prompt.",
                    },
                    "context": {
                        "type": "string",
                        "description": "Additional context or invariants.",
                    },
                },
                "required": ["action"],
            },
        }

    def run(
        self,
        action: str = "write_prompt",
        prompt: Optional[str] = None,
        task: Optional[str] = None,
        folder_path: Optional[str] = None,
        model: str = "Gemini 3.8 Flash",
        effort: str = "High",
        priority: str = "High",
        attachment: Optional[str] = None,
        context: Optional[str] = None,
        **kwargs: Any,
    ) -> ToolResult:
        act = (action or "write_prompt").lower().strip()
        user_prompt = (prompt or task or "").strip()

        try:
            # 1. Launch Antigravity
            if act in ("launch", "start", "open") and not task and not prompt:
                return self._action_launch()

            # 2. Focus Window
            elif act == "focus":
                focused = focus_antigravity_window()
                return ToolResult(
                    success=focused,
                    message="Focused Google Antigravity window." if focused else "Could not find Antigravity window.",
                    data={"focused": focused},
                )

            # 3. Open Folder
            elif act in ("open_folder", "folder", "workspace"):
                return self._action_open_folder(folder_path or user_prompt)

            # 4. Open New Chat
            elif act in ("new_chat", "chat", "new_conversation"):
                return self._action_new_chat()

            # 5. Send Prompt directly into Antigravity
            elif act in ("send_prompt", "send"):
                return self._action_send_prompt(
                    prompt=user_prompt,
                    model=model,
                    effort=effort,
                    priority=priority,
                    attachment=attachment,
                    context=context,
                )

            # 6. Write Prompt to file & clipboard (classic mode)
            elif act in ("write_prompt", "formulate_prompt", "launch"):
                return self._action_write_prompt(
                    task=user_prompt,
                    model=model,
                    effort=effort,
                    priority=priority,
                    attachment=attachment,
                    context=context,
                )

            # 7. Choose Model Directive
            elif act in ("choose_model", "model", "set_model"):
                return self._action_choose_model(model=model, effort=effort)

            return ToolResult(
                success=False,
                message=f"Unknown Antigravity action '{action}'. Valid actions include: "
                        "launch, focus, open_folder, new_chat, send_prompt, write_prompt, choose_model.",
            )

        except Exception as exc:
            logger.exception("AntigravityControl error for action '%s': %s", action, exc)
            return ToolResult(
                success=False,
                message=f"Antigravity control error: {str(exc)}",
                data={"error": str(exc)},
            )

    # -------------------------------------------------------------------------
    # Core Actions
    # -------------------------------------------------------------------------

    def _action_launch(self) -> ToolResult:
        """Launches Google Antigravity via shortcut or executable."""
        # Check if already running and focused
        if focus_antigravity_window():
            return ToolResult(
                success=True,
                message="Google Antigravity is already running and has been brought to the foreground.",
                data={"status": "already_running_focused"},
            )

        target = get_antigravity_launch_target()
        if not target:
            return ToolResult(
                success=False,
                message="Google Antigravity shortcut (Antigravity.lnk) or executable was not found on this system.",
            )

        try:
            if target.endswith(".lnk"):
                os.startfile(target)
            else:
                subprocess.Popen([target], shell=True)

            time.sleep(1.0)
            focus_antigravity_window()
            return ToolResult(
                success=True,
                message=f"Launched Google Antigravity via '{os.path.basename(target)}'.",
                data={"launch_target": target},
            )
        except Exception as exc:
            return ToolResult(
                success=False,
                message=f"Failed to launch Antigravity: {str(exc)}",
                data={"error": str(exc)},
            )

    def _action_open_folder(self, folder_path: Optional[str]) -> ToolResult:
        """Opens a folder in Google Antigravity."""
        folder = (folder_path or ".").strip()
        resolved_folder = os.path.abspath(folder)

        if not os.path.exists(resolved_folder):
            os.makedirs(resolved_folder, exist_ok=True)

        target = get_antigravity_launch_target()
        try:
            if target and target.endswith(".exe"):
                # Spawn Antigravity with folder path argument
                subprocess.Popen([target, resolved_folder], shell=True)
            elif target:
                os.startfile(target)
                time.sleep(1.0)

            time.sleep(0.8)
            focus_antigravity_window()

            # Hotkey fallback to open folder: Ctrl+K Ctrl+O
            if pyautogui:
                pyautogui.hotkey("ctrl", "k")
                time.sleep(0.1)
                pyautogui.hotkey("ctrl", "o")
                time.sleep(0.3)
                if _PYPERCLIP_OK:
                    pyperclip.copy(resolved_folder)
                    pyautogui.hotkey("ctrl", "v")
                    time.sleep(0.1)
                    pyautogui.press("enter")

            return ToolResult(
                success=True,
                message=f"Opened folder '{resolved_folder}' in Google Antigravity.",
                data={"folder": resolved_folder},
            )
        except Exception as exc:
            return ToolResult(
                success=False,
                message=f"Failed to open folder '{resolved_folder}' in Antigravity: {str(exc)}",
            )

    def _action_new_chat(self) -> ToolResult:
        """Opens a new conversation or chat input in Google Antigravity (Ctrl+L / Ctrl+Shift+L)."""
        self._action_launch()
        focus_antigravity_window()

        if pyautogui:
            time.sleep(0.3)
            # Standard chat trigger in AI IDEs: Ctrl+L or Ctrl+Shift+L
            pyautogui.hotkey("ctrl", "l")
            time.sleep(0.2)

        return ToolResult(
            success=True,
            message="Opened new chat session and focused prompt input in Google Antigravity.",
            data={"action": "new_chat"},
        )

    def _action_send_prompt(
        self,
        prompt: str,
        model: str = "Gemini 3.8 Flash",
        effort: str = "High",
        priority: str = "High",
        attachment: Optional[str] = None,
        context: Optional[str] = None,
    ) -> ToolResult:
        """Sends a formulated prompt directly into the Antigravity chat input."""
        if not prompt:
            return ToolResult(success=False, message="Prompt text must be provided.")

        # Ensure Antigravity is online and chat is focused
        self._action_launch()
        focus_antigravity_window()

        # Build full optimized directive
        formatted_prompt = self._build_directive(
            prompt=prompt,
            model=model,
            effort=effort,
            priority=priority,
            attachment=attachment,
            context=context,
        )

        # Copy to clipboard
        if _PYPERCLIP_OK:
            pyperclip.copy(formatted_prompt)

        # Focus chat input and paste
        if pyautogui:
            time.sleep(0.3)
            pyautogui.hotkey("ctrl", "l")
            time.sleep(0.2)
            pyautogui.hotkey("ctrl", "v")
            time.sleep(0.2)
            pyautogui.press("enter")

        return ToolResult(
            success=True,
            message=(
                f"Dispatched prompt to Google Antigravity [Model: {model} ({effort} effort)]. "
                f"Attachment: {attachment or 'None'}."
            ),
            data={
                "action": "send_prompt",
                "model": model,
                "effort": effort,
                "priority": priority,
                "attachment": attachment,
                "prompt_snippet": prompt[:200],
            },
        )

    def _action_write_prompt(
        self,
        task: str,
        model: str = "Gemini 3.8 Flash",
        effort: str = "High",
        priority: str = "High",
        attachment: Optional[str] = None,
        context: Optional[str] = None,
    ) -> ToolResult:
        """Formulates prompt, writes to disk and clipboard, and focuses Antigravity."""
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        sanitized_title = "_".join(task.split()[:5]).lower()
        sanitized_title = "".join(c for c in sanitized_title if c.isalnum() or c == "_")
        filename = f"{sanitized_title}_{ts}.md"

        prompts_dir = Path.home() / "Desktop" / "Antigravity_Prompts"
        prompts_dir.mkdir(parents=True, exist_ok=True)
        prompt_file = prompts_dir / filename

        formatted_prompt = self._build_directive(
            prompt=task,
            model=model,
            effort=effort,
            priority=priority,
            attachment=attachment,
            context=context,
        )

        prompt_file.write_text(formatted_prompt, encoding="utf-8")

        if _PYPERCLIP_OK:
            pyperclip.copy(formatted_prompt)

        focus_antigravity_window()

        return ToolResult(
            success=True,
            message=f"Antigravity directive saved to '{prompt_file.name}' and copied to clipboard.",
            data={"prompt_file": str(prompt_file.resolve())},
        )

    def _action_choose_model(self, model: str, effort: str) -> ToolResult:
        """Generates model selection instruction for Antigravity."""
        directive = f"/model {model} (Effort: {effort})"
        if _PYPERCLIP_OK:
            pyperclip.copy(directive)
        focus_antigravity_window()

        if pyautogui:
            time.sleep(0.2)
            pyautogui.hotkey("ctrl", "l")
            time.sleep(0.1)
            pyautogui.hotkey("ctrl", "v")
            time.sleep(0.1)
            pyautogui.press("enter")

        return ToolResult(
            success=True,
            message=f"Model set to '{model}' with '{effort}' effort in Google Antigravity.",
            data={"model": model, "effort": effort},
        )

    def _build_directive(
        self,
        prompt: str,
        model: str,
        effort: str,
        priority: str,
        attachment: Optional[str],
        context: Optional[str],
    ) -> str:
        """Constructs a clean prompt directive."""
        attachment_str = f"\n\n**Attachment / Context File**: `@{attachment}`" if attachment else ""
        ctx_str = f"\n\n**Constraints & Invariants**:\n{context}" if context else ""

        return (
            f"<!-- [Model Selection: {model} ({effort} Effort) | Priority: {priority}] -->\n"
            f"{prompt}{attachment_str}{ctx_str}"
        )


# Backward-compatibility alias
AntigravityPromptTool = AntigravityControlTool
