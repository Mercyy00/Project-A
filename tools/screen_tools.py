"""
Screen Vision and Perception Tools for JARVIS.

Provides tools to:
- Capture the primary monitor or active window
- Extract text from screen via OCR
- Describe active screen state using multimodal vision
"""

from __future__ import annotations

import os
import sys
import time
import base64
from pathlib import Path
from typing import Any, Dict, Optional

from tools.base import BaseTool, ToolResult


class CaptureScreenTool(BaseTool):
    """Captures a snapshot of the active screen or window."""
    name: str = "capture_screen"
    description: str = "Captures the user's primary monitor or screen and saves it as a high-resolution image."

    def get_schema(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "save_path": {
                        "type": "string",
                        "description": "Optional file path to save the screenshot. Defaults to temp directory."
                    }
                },
                "required": []
            }
        }

    def run(self, save_path: Optional[str] = None, **kwargs) -> ToolResult:
        try:
            import mss
            from PIL import Image

            out_dir = Path("temp_vision")
            out_dir.mkdir(parents=True, exist_ok=True)
            target = Path(save_path) if save_path else out_dir / f"screenshot_{int(time.time())}.png"

            with mss.mss() as sct:
                monitor = sct.monitors[1] if len(sct.monitors) > 1 else sct.monitors[0]
                sct_img = sct.grab(monitor)
                img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
                img.save(target)

            return ToolResult(
                success=True,
                data={
                    "file_path": str(target.resolve()),
                    "width": sct_img.width,
                    "height": sct_img.height
                },
                message=f"Screen snapshot captured ({sct_img.width}x{sct_img.height}) at {target.name}"
            )
        except Exception as exc:
            return ToolResult(
                success=False,
                message=f"Failed to capture screen: {str(exc)}"
            )


class DescribeScreenTool(BaseTool):
    """Analyzes the current desktop screen using multimodal AI vision."""
    name: str = "describe_screen"
    description: str = (
        "Inspects what is currently displayed on the user's screen (open apps, documents, errors, code) "
        "and answers questions about it."
    )

    def get_schema(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "What to look for or question about the screen (e.g. 'What error is shown?', 'Summarize what I am viewing')."
                    }
                },
                "required": []
            }
        }

    def run(self, prompt: Optional[str] = None, **kwargs) -> ToolResult:
        query = prompt or "Describe what is currently visible on the user's screen in detail."
        try:
            import mss
            from PIL import Image
            import io

            with mss.mss() as sct:
                monitor = sct.monitors[1] if len(sct.monitors) > 1 else sct.monitors[0]
                sct_img = sct.grab(monitor)
                img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
                
                # Downscale slightly for rapid vision transfer
                img.thumbnail((1600, 1600))
                buf = io.BytesIO()
                img.save(buf, format="JPEG", quality=85)
                buf.seek(0)
                image_bytes = buf.getvalue()

            # Call Gemini Vision via Google GenAI SDK
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                return ToolResult(
                    success=False,
                    message="Screen captured, but GEMINI_API_KEY is not configured for vision analysis."
                )

            from google import genai
            from google.genai import types

            client = genai.Client(api_key=api_key)
            model_name = os.getenv("GEMINI_MODEL") or os.getenv("MODEL_NAME") or "gemini-3.5-flash-lite"
            
            response = client.models.generate_content(
                model=model_name,
                contents=[
                    types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"),
                    query
                ]
            )

            text_resp = response.text.strip() if response and response.text else "Unable to analyze screen contents."
            return ToolResult(
                success=True,
                data={"analysis": text_resp},
                message=text_resp
            )
        except Exception as exc:
            return ToolResult(
                success=False,
                message=f"Screen description failed: {str(exc)}"
            )
