# System tools and automation module (Abhijit)
from tools.base import BaseTool, ToolResult
from tools.safety import is_path_safe
from tools.file_tools import ReadFileTool, WriteFileTool
from tools.system_tools import (
    GetSystemStatsTool,
    OpenAppTool,
    OpenFileTool,
    ListDirectoryTool,
    OpenWebsiteTool,
    SearchWebTool,
)
from tools.control_tools import (
    TypeTextTool,
    PressKeysTool,
    ClickTool,
    ScrollTool,
    CONTROL_TOOLS,
)
from tools.whatsapp_tool import WhatsAppTool
from tools.youtube_tool import YouTubeControlTool
from tools.youtube_music_tool import YouTubeMusicTool
from tools.file_manager_tool import FileManagerTool
from tools.browser_tools import BrowserControlTool
from tools.skill_tool import SkillLearnerTool
from tools.dev_tools import DevAgentTool
from tools.antigravity_tools import AntigravityControlTool, AntigravityPromptTool
from tools.semantic_memory_tool import SemanticMemoryTool
from tools.guardian_tool import HardwareWatchdogTool
from vision.loop import GuiAgentTool
from tools.web_tools import WebResearchReportTool, WebScrapeTool
from tools.google_workspace_tool import GoogleCalendarTool, GmailTool
from tools.registry import (
    TOOL_REGISTRY,
    execute_tool,
    get_registered_tools,
    get_tools_schema,
    register_tool,
    auto_load_module_tools,
)

__all__ = [
    "BaseTool",
    "ToolResult",
    "is_path_safe",
    "ReadFileTool",
    "WriteFileTool",
    "GetSystemStatsTool",
    "OpenAppTool",
    "OpenFileTool",
    "ListDirectoryTool",
    "OpenWebsiteTool",
    "SearchWebTool",
    "TypeTextTool",
    "PressKeysTool",
    "ClickTool",
    "ScrollTool",
    "CONTROL_TOOLS",
    "TOOL_REGISTRY",
    "WhatsAppTool",
    "YouTubeControlTool",
    "YouTubeMusicTool",
    "FileManagerTool",
    "BrowserControlTool",
    "SkillLearnerTool",
    "DevAgentTool",
    "AntigravityControlTool",
    "AntigravityPromptTool",
    "SemanticMemoryTool",
    "HardwareWatchdogTool",
    "GuiAgentTool",
    "WebResearchReportTool",
    "WebScrapeTool",
    "GoogleCalendarTool",
    "GmailTool",
    "execute_tool",
    "get_registered_tools",
    "get_tools_schema",
    "register_tool",
    "auto_load_module_tools",
]
