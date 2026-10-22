"""Vision package for Project Jarvis (Aryan).

Handles screen capture, multimodal desktop understanding, visual error explanation,
UI element location, and exposes vision tools for the Jarvis agentic tool registry.
"""

from vision.screen import (
    clean_temp_vision,
    describe_screen,
    explain_screen_error,
    locate_element,
    parse_region_hint,
    take_screenshot,
)
from vision.tools import (
    ClickElementTool,
    DescribeScreenTool,
    ExplainScreenErrorTool,
    ScreenshotTool,
    TOOLS,
)

__all__ = [
    "take_screenshot",
    "describe_screen",
    "explain_screen_error",
    "locate_element",
    "clean_temp_vision",
    "parse_region_hint",
    "ScreenshotTool",
    "DescribeScreenTool",
    "ExplainScreenErrorTool",
    "ClickElementTool",
    "TOOLS",
]
