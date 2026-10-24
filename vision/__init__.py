"""Vision package for Project Jarvis (Aryan).

Handles screen capture, multimodal desktop understanding, visual error explanation,
UI element location, autonomous look-decide-act loop, code explanation/debugging,
and exposes vision tools for the Jarvis agentic tool registry.
"""

from vision.screen import (
    clean_temp_vision,
    describe_screen,
    do_on_screen,
    explain_code_on_screen,
    explain_screen_error,
    locate_element,
    parse_region_hint,
    take_screenshot,
)
from vision.tools import (
    ClickElementTool,
    DescribeScreenTool,
    DoOnScreenTool,
    ExplainCodeOnScreenTool,
    ExplainScreenErrorTool,
    ScreenshotTool,
    TOOLS,
)

__all__ = [
    "take_screenshot",
    "describe_screen",
    "explain_screen_error",
    "locate_element",
    "do_on_screen",
    "explain_code_on_screen",
    "clean_temp_vision",
    "parse_region_hint",
    "ScreenshotTool",
    "DescribeScreenTool",
    "ExplainScreenErrorTool",
    "ClickElementTool",
    "DoOnScreenTool",
    "ExplainCodeOnScreenTool",
    "TOOLS",
]
