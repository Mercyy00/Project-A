"""Vision tools module for Project Jarvis (Aryan).

Implements ScreenshotTool and DescribeScreenTool compliant with BaseTool
specification, allowing automatic discovery by the Jarvis Tool Registry.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Sequence

from tools.base import BaseTool, ToolResult
from vision.screen import describe_screen, take_screenshot

logger = logging.getLogger(__name__)


class ScreenshotTool(BaseTool):
    """Tool for capturing desktop screenshots for logging, user review, or inspection."""

    name: str = "take_screenshot"
    description: str = (
        "Captures a high-resolution screenshot of the user's primary monitor or a specific screen region. "
        "Saves the image into temp_vision/ and returns the file path. "
        "Useful for seeing the current state of apps, desktop, or errors."
    )

    def run(
        self,
        region: Optional[Sequence[int]] = None,
        **kwargs: Any,
    ) -> ToolResult:
        """Capture a screenshot.

        Args:
            region: Optional bounding box [left, top, width, height] in pixels.
            **kwargs: Extra arguments (ignored).

        Returns:
            ToolResult containing the file path on success, or structured error message on failure.
        """
        try:
            if region is not None:
                if not isinstance(region, (list, tuple)) or len(region) != 4:
                    return ToolResult(
                        success=False,
                        data=None,
                        message="Invalid 'region' parameter: must be a list or tuple of 4 integers [left, top, width, height].",
                    )

            path = take_screenshot(region=region)
            return ToolResult(
                success=True,
                data={"file_path": path, "region": region},
                message=f"Screenshot captured successfully and saved to: {path}",
            )
        except PermissionError as pe:
            return ToolResult(
                success=False,
                data=None,
                message=str(pe),
            )
        except ValueError as ve:
            return ToolResult(
                success=False,
                data=None,
                message=f"Invalid parameter: {ve}",
            )
        except Exception as exc:
            logger.exception("ScreenshotTool execution failed: %s", exc)
            return ToolResult(
                success=False,
                data=None,
                message=f"Failed to capture screenshot: {exc}",
            )

    def get_schema(self) -> Dict[str, Any]:
        """Returns JSON schema definition for LLM tool calling."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "region": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": "Optional [left, top, width, height] pixel coordinates to capture only a sub-region of the screen.",
                    }
                },
                "required": [],
            },
        }


class DescribeScreenTool(BaseTool):
    """Tool for analyzing desktop screen contents using Gemini Multimodal Vision."""

    name: str = "describe_screen"
    description: str = (
        "Inspects what is currently displayed on the desktop screen using AI vision. "
        "Answers questions about open applications, visible text, code errors, dialogs, or user interfaces."
    )

    def run(
        self,
        question: str = "What is currently visible on my screen?",
        screenshot_path: Optional[str] = None,
        region: Optional[Sequence[int]] = None,
        **kwargs: Any,
    ) -> ToolResult:
        """Analyze desktop screen contents.

        Args:
            question: Question or analysis instructions for the AI vision model.
            screenshot_path: Optional path to an existing image file. If omitted, takes a live screenshot.
            region: Optional bounding box [left, top, width, height] to capture if screenshot_path is None.
            **kwargs: Extra arguments (ignored).

        Returns:
            ToolResult containing the visual analysis answer from Gemini.
        """
        try:
            if not question or not str(question).strip():
                return ToolResult(
                    success=False,
                    data=None,
                    message="Parameter 'question' is required and cannot be empty.",
                )

            answer = describe_screen(
                question=str(question).strip(),
                screenshot_path=screenshot_path,
                region=region,
            )

            return ToolResult(
                success=True,
                data={
                    "question": question,
                    "description": answer,
                    "screenshot_path": screenshot_path,
                },
                message=answer,
            )
        except PermissionError as pe:
            return ToolResult(
                success=False,
                data=None,
                message=str(pe),
            )
        except ValueError as ve:
            return ToolResult(
                success=False,
                data=None,
                message=f"Configuration error: {ve}",
            )
        except Exception as exc:
            logger.exception("DescribeScreenTool execution failed: %s", exc)
            return ToolResult(
                success=False,
                data=None,
                message=f"Failed to analyze screen: {exc}",
            )

    def get_schema(self) -> Dict[str, Any]:
        """Returns JSON schema definition for LLM tool calling."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "The specific question or instruction for analyzing the screen (e.g. 'What is on my screen?', 'Read the error dialog').",
                    },
                    "screenshot_path": {
                        "type": "string",
                        "description": "Optional file path to a previously saved screenshot. If omitted, captures current screen live.",
                    },
                    "region": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": "Optional [left, top, width, height] coordinates to limit capture to a specific screen area.",
                    },
                },
                "required": ["question"],
            },
        }


# Expose TOOLS list for automatic auto-loading by tools/registry.py
TOOLS: List[BaseTool] = [
    ScreenshotTool(),
    DescribeScreenTool(),
]
