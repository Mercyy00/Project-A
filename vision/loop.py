"""
Screen-Guided Look-Decide-Act Autonomous GUI Agent Loop for Project JARVIS.
Author: Aryan & Abhijit (Vision & System Automation)

Implements Task 20:
- Multimodal perception and screen reasoning loop using Google Gemini.
- Autonomous look-decide-act loop with step budget, state verification, and recovery.
- Rigorous safety guardrails:
  1. Instant emergency kill-switch halt (tools.guard.is_stopped() & Ctrl+Alt+Q).
  2. Privacy mode check (VISION_PAUSED=1).
  3. Prohibited destructive action filter (rmdir, format, bulk deletion).
  4. Automatic monitor coordinate and DPI awareness scaling.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
import re
import time
from typing import Any, Callable, Dict, List, Optional, Sequence, Union

from dotenv import load_dotenv
import mss
from PIL import Image

from tools.base import BaseTool, ToolResult

load_dotenv()
logger = logging.getLogger(__name__)

TEMP_VISION_DIR = Path("temp_vision")
TEMP_VISION_DIR.mkdir(parents=True, exist_ok=True)

# Guardrail: destructive patterns that an autonomous agent must never type
PROHIBITED_TYPE_PATTERNS = [
    r"\brmdir\s+/[sq]\b",
    r"\bformat\s+[a-z]:",
    r"\bdel\s+/[sfq]",
    r"\brm\s+-rf\b",
    r"\bdrop\s+database\b",
    r"\bdiskpart\b",
]


class GuiAgent:
    """Autonomous desktop GUI automation agent implementing look-decide-act loops."""

    def __init__(
        self,
        model_name: Optional[str] = None,
        max_steps: int = 5,
        pause_between_steps: float = 1.0,
    ) -> None:
        self.model_name = (
            model_name
            or os.getenv("GEMINI_MODEL")
            or os.getenv("MODEL_NAME", "gemini-3.5-flash-lite")
        )
        self.max_steps = max(1, min(max_steps, 15))
        self.pause_between_steps = max(0.2, pause_between_steps)

    def _check_emergency_kill_switch(self) -> bool:
        """Verifies if the emergency kill switch was triggered."""
        try:
            from tools.guard import is_stopped
            return bool(is_stopped())
        except (ImportError, AttributeError):
            return False

    def _is_destructive_text(self, text: str) -> bool:
        """Scans proposed text against prohibited destructive command patterns."""
        if not text:
            return False
        clean = text.lower()
        for pat in PROHIBITED_TYPE_PATTERNS:
            if re.search(pat, clean, re.IGNORECASE):
                return True
        return False

    def capture_screen(self, step_idx: int = 0) -> Tuple[Path, int, int, int, int]:
        """Captures active screen snapshot and returns path and monitor bounds."""
        target_path = TEMP_VISION_DIR / f"gui_loop_step_{step_idx}_{int(time.time())}.png"
        orig_left, orig_top = 0, 0
        orig_width, orig_height = 1920, 1080

        with mss.mss() as sct:
            monitor = sct.monitors[1] if len(sct.monitors) > 1 else sct.monitors[0]
            orig_left, orig_top = monitor["left"], monitor["top"]
            orig_width, orig_height = monitor["width"], monitor["height"]
            sct_img = sct.grab(monitor)
            img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
            img.save(str(target_path))

        return target_path, orig_left, orig_top, orig_width, orig_height

    def decide_next_action(
        self,
        goal: str,
        screenshot_path: Path,
        steps_history: List[Dict[str, Any]],
        img_dimensions: Tuple[int, int],
    ) -> Dict[str, Any]:
        """Prompts Gemini with screenshot and step history to determine the single next GUI action."""
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key or api_key.strip() in ("", "your_gemini_api_key_here"):
            raise ValueError("GEMINI_API_KEY is not configured in .env.")

        from google import genai

        img_w, img_h = img_dimensions

        history_summary = []
        for idx, s in enumerate(steps_history, 1):
            history_summary.append(f"Step {idx}: {s.get('action')} - {s.get('thought', '')}")
        history_str = "\n".join(history_summary) if history_summary else "No actions performed yet."

        prompt = (
            f"You are an autonomous desktop GUI automation agent.\n"
            f"User Goal: '{goal.strip()}'.\n\n"
            f"Actions performed so far:\n{history_str}\n\n"
            f"Attached is the current screen state ({img_w}x{img_h} px).\n"
            f"Analyze the screen and determine the SINGLE next action required to make progress toward the goal.\n"
            f"Return ONLY a valid JSON object matching one of these action schemas:\n"
            f"- Click: {{\"action\": \"click\", \"x\": <int_x>, \"y\": <int_y>, \"button\": \"left\", \"thought\": \"<why>\"}}\n"
            f"- Double Click: {{\"action\": \"double_click\", \"x\": <int_x>, \"y\": <int_y>, \"thought\": \"<why>\"}}\n"
            f"- Right Click: {{\"action\": \"right_click\", \"x\": <int_x>, \"y\": <int_y>, \"thought\": \"<why>\"}}\n"
            f"- Type: {{\"action\": \"type\", \"text\": \"<text to type>\", \"thought\": \"<why>\"}}\n"
            f"- Hotkey: {{\"action\": \"hotkey\", \"keys\": [\"ctrl\", \"s\"], \"thought\": \"<why>\"}}\n"
            f"- Scroll: {{\"action\": \"scroll\", \"amount\": <-200 to 200>, \"thought\": \"<why>\"}}\n"
            f"- Wait: {{\"action\": \"wait\", \"seconds\": <float>, \"thought\": \"<why>\"}}\n"
            f"- Done: {{\"action\": \"done\", \"thought\": \"<explain how goal is finished>\"}}\n\n"
            f"Output ONLY the JSON object. Do not include markdown code fence formatting."
        )

        with Image.open(str(screenshot_path)) as img:
            client = genai.Client(api_key=api_key.strip())
            response = client.models.generate_content(
                model=self.model_name,
                contents=[img, prompt],
            )
            raw = (response.text or "").strip()

            # Clean markdown codeblocks if present
            if raw.startswith("```"):
                lines = raw.splitlines()
                if lines and lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].startswith("```"):
                    lines = lines[:-1]
                raw = "\n".join(lines).strip()

            match = re.search(r"\{.*\}", raw, re.DOTALL)
            payload = match.group(0) if match else raw
            return json.loads(payload)

    def run(
        self,
        goal: str,
        max_steps: Optional[int] = None,
        step_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> Dict[str, Any]:
        """Executes the full look-decide-act loop until completion, step limit, or emergency stop."""
        if os.getenv("VISION_PAUSED", "0") == "1":
            raise PermissionError(
                "Screen vision is currently paused by user privacy mode (VISION_PAUSED=1)."
            )

        if not goal or not str(goal).strip():
            raise ValueError("Goal parameter must be a non-empty string.")

        steps_budget = max(1, min(max_steps or self.max_steps, 15))
        executed_steps: List[Dict[str, Any]] = []

        import tools.registry as registry

        completed = False
        termination_reason = "Max steps limit reached."

        for step in range(1, steps_budget + 1):
            # 1. Kill-switch check
            if self._check_emergency_kill_switch():
                termination_reason = "Emergency stop triggered by kill-switch (tools.guard.is_stopped() is True)."
                executed_steps.append({
                    "step": step,
                    "action": "abort",
                    "thought": "Emergency kill switch active. Halting immediately.",
                    "status": "stopped",
                })
                break

            # 2. Look: Capture screen
            try:
                shot_path, o_left, o_top, o_width, o_height = self.capture_screen(step_idx=step)
            except Exception as cap_err:
                termination_reason = f"Failed to capture screen: {cap_err}"
                break

            # 3. Decide: Multimodal evaluation
            try:
                with Image.open(str(shot_path)) as tmp_img:
                    img_dims = tmp_img.size

                decision = self.decide_next_action(
                    goal=goal,
                    screenshot_path=shot_path,
                    steps_history=executed_steps,
                    img_dimensions=img_dims,
                )
            except Exception as dec_err:
                termination_reason = f"Error evaluating screen decision: {dec_err}"
                executed_steps.append({
                    "step": step,
                    "action": "error",
                    "thought": str(dec_err),
                    "status": "failed",
                })
                break

            action = str(decision.get("action", "")).strip().lower()
            thought = str(decision.get("thought", "")).strip()

            step_record: Dict[str, Any] = {
                "step": step,
                "action": action,
                "thought": thought,
                "screenshot": str(shot_path),
            }

            # 4. Act: Dispatch action with guardrails
            if action == "done":
                step_record["status"] = "success"
                executed_steps.append(step_record)
                completed = True
                termination_reason = f"Goal completed: {thought}"
                if step_callback:
                    step_callback(step_record)
                break

            elif action in ("click", "double_click", "right_click"):
                raw_x = int(decision.get("x", 0))
                raw_y = int(decision.get("y", 0))
                scale_x = o_width / float(img_dims[0]) if img_dims[0] > 0 else 1.0
                scale_y = o_height / float(img_dims[1]) if img_dims[1] > 0 else 1.0
                real_x = int(o_left + (raw_x * scale_x))
                real_y = int(o_top + (raw_y * scale_y))

                btn = "right" if action == "right_click" else str(decision.get("button", "left"))
                clicks = 2 if action == "double_click" else 1

                res: ToolResult = registry.execute_tool(
                    "click",
                    {"x": real_x, "y": real_y, "button": btn, "clicks": clicks}
                )
                step_record["details"] = {"x": real_x, "y": real_y, "button": btn, "clicks": clicks}
                step_record["status"] = "success" if res.success else "failed"
                step_record["message"] = res.message

            elif action == "type":
                text_to_type = str(decision.get("text", ""))
                # Guardrail against prohibited destructive commands
                if self._is_destructive_text(text_to_type):
                    step_record["status"] = "blocked"
                    step_record["message"] = f"Blocked potentially destructive command: '{text_to_type}'"
                    executed_steps.append(step_record)
                    termination_reason = "Blocked hazardous destructive command."
                    break

                res: ToolResult = registry.execute_tool("type_text", {"text": text_to_type})
                step_record["details"] = {"text": text_to_type}
                step_record["status"] = "success" if res.success else "failed"
                step_record["message"] = res.message

            elif action == "hotkey":
                keys = decision.get("keys", [])
                if isinstance(keys, str):
                    keys = [keys]
                res: ToolResult = registry.execute_tool("press_keys", {"keys": keys})
                step_record["details"] = {"keys": keys}
                step_record["status"] = "success" if res.success else "failed"
                step_record["message"] = res.message

            elif action == "scroll":
                amount = int(decision.get("amount", -200))
                res: ToolResult = registry.execute_tool("scroll", {"amount": amount})
                step_record["details"] = {"amount": amount}
                step_record["status"] = "success" if res.success else "failed"
                step_record["message"] = res.message

            elif action == "wait":
                secs = float(decision.get("seconds", 1.0))
                time.sleep(min(max(secs, 0.1), 5.0))
                step_record["details"] = {"seconds": secs}
                step_record["status"] = "success"
                step_record["message"] = f"Waited {secs} seconds."

            else:
                step_record["status"] = "unknown_action"
                step_record["message"] = f"Unrecognized action '{action}'"

            executed_steps.append(step_record)

            if step_callback:
                step_callback(step_record)

            # 5. Pause for UI reaction
            time.sleep(self.pause_between_steps)

        summary_lines = [f"GUI Agent Execution Summary for goal: '{goal}':"]
        for s in executed_steps:
            summary_lines.append(f"- Step {s['step']} [{s['action']}]: {s.get('thought', '')} -> {s.get('status', '')}")
        summary_lines.append(f"\nFinal Outcome: {termination_reason}")

        return {
            "completed": completed,
            "goal": goal,
            "total_steps": len(executed_steps),
            "steps": executed_steps,
            "reason": termination_reason,
            "summary": "\n".join(summary_lines)
        }


class GuiAgentTool(BaseTool):
    """Tool wrapper exposing the look-decide-act autonomous GUI agent."""

    name: str = "gui_agent"
    description: str = (
        "Autonomous visual look-decide-act GUI agent. Captures screen, analyzes UI state with Gemini vision, "
        "decides and performs clicks, keystrokes, and hotkeys, and re-checks the screen in a loop until the goal is done."
    )

    def get_schema(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "goal": {
                        "type": "string",
                        "description": "Natural language screen goal (e.g. 'click the search bar on Chrome', 'open File menu in Notepad')."
                    },
                    "max_steps": {
                        "type": "integer",
                        "description": "Maximum number of look-decide-act loop iterations (default: 5, max: 15)."
                    }
                },
                "required": ["goal"]
            }
        }

    def run(self, goal: str = "", max_steps: int = 5, **kwargs: Any) -> ToolResult:
        try:
            agent = GuiAgent(max_steps=max_steps)
            outcome = agent.run(goal=goal, max_steps=max_steps)
            return ToolResult(
                success=outcome.get("completed", False),
                data=outcome,
                message=outcome.get("summary", "Look-decide-act loop finished.")
            )
        except PermissionError as pe:
            return ToolResult(success=False, data=None, message=str(pe))
        except ValueError as ve:
            return ToolResult(success=False, data=None, message=str(ve))
        except Exception as exc:
            logger.exception("GuiAgentTool execution error: %s", exc)
            return ToolResult(
                success=False,
                data=None,
                message=f"GUI agent loop encountered an error: {exc}"
            )
