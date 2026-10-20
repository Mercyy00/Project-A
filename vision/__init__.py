"""Vision package for Project Jarvis (Aryan).

Handles screen capture, multimodal desktop understanding, visual context,
and exposes vision tools for the Jarvis agentic tool registry.
"""

from vision.screen import describe_screen, take_screenshot
from vision.tools import DescribeScreenTool, ScreenshotTool, TOOLS

__all__ = [
    "take_screenshot",
    "describe_screen",
    "ScreenshotTool",
    "DescribeScreenTool",
    "TOOLS",
]
