"""

Jarvis Tool Registry.



Registers all available system tools and provides safe execution dispatching.

Supports dynamic auto-loading of plugin modules from other team members.

"""



import importlib

import logging

from typing import Any, Dict, List, Optional

from tools.base import BaseTool, ToolResult

from tools.system_tools import (

    GetSystemStatsTool,

    OpenAppTool,

    OpenFileTool,

    ListDirectoryTool,

    OpenWebsiteTool,

    SearchWebTool,
    OpenSettingsPageTool,

    ClipboardReadTool,

    ClipboardWriteTool,

    SetVolumeTool,

    SetBrightnessTool,

    LockScreenTool,

    BatteryTool,

)

from tools.window_tools import (

    ListWindowsTool,

    FocusWindowTool,

    MinimizeWindowTool,

)

from tools.file_tools import ReadFileTool, WriteFileTool

from tools.control_tools import (

    TypeTextTool,

    PressKeysTool,

    ClickTool,

    ScrollTool,

)

from tools.browser_tools import BrowserControlTool
from tools.screen_tools import CaptureScreenTool, DescribeScreenTool
from tools.desktop_tools import OrganizeDesktopTool, SetWallpaperTool, ComputerSettingsTool
from tools.dev_tools import DevAgentTool
from tools.weather_tool import WeatherReportTool
from tools.whatsapp_tool import WhatsAppTool
from tools.youtube_tool import YouTubeControlTool
from tools.youtube_music_tool import YouTubeMusicTool
from tools.file_manager_tool import FileManagerTool
from tools.skill_tool import SkillLearnerTool
from tools.antigravity_tools import AntigravityPromptTool, AntigravityControlTool
from tools.code_tools import (

    RunCommandTool,

    EditFileTool,

    RunPythonTool,

)



logger = logging.getLogger(__name__)





class ToolRegistry(dict):

    """Dictionary holding registered tools with case-insensitive and class-name lookup."""



    def __getitem__(self, key: str) -> BaseTool:

        if super().__contains__(key):

            return super().__getitem__(key)

        norm_key = key.lower()

        if super().__contains__(norm_key):

            return super().__getitem__(norm_key)

        for k, v in self.items():

            if k.lower() == norm_key or v.__class__.__name__.lower() == norm_key:

                return v

        return super().__getitem__(key)



    def get(self, key: str, default: Any = None) -> Any:

        """Retrieves a tool by name or class name with a default fallback."""

        try:

            return self[key]

        except KeyError:

            return default



    def __contains__(self, key: object) -> bool:

        if not isinstance(key, str):

            return False

        if super().__contains__(key):

            return True

        norm_key = key.lower()

        if super().__contains__(norm_key):

            return True

        for k, v in self.items():

            if k.lower() == norm_key or v.__class__.__name__.lower() == norm_key:

                return True

        return False





# Register primary tool instances by their canonical names

TOOL_REGISTRY: Dict[str, BaseTool] = ToolRegistry({

    "get_system_stats": GetSystemStatsTool(),

    "open_app": OpenAppTool(),

    "open_file": OpenFileTool(),

    "list_directory": ListDirectoryTool(),

    "open_website": OpenWebsiteTool(),

    "search_web": SearchWebTool(),

    "read_file": ReadFileTool(),

    "write_file": WriteFileTool(),

    "type_text": TypeTextTool(),

    "press_keys": PressKeysTool(),

    "click": ClickTool(),

    "scroll": ScrollTool(),

    "run_command": RunCommandTool(),

    "edit_file": EditFileTool(),

    "run_python": RunPythonTool(),

    "list_windows": ListWindowsTool(),

    "focus_window": FocusWindowTool(),

    "minimize_window": MinimizeWindowTool(),

    "clipboard_read": ClipboardReadTool(),

    "clipboard_write": ClipboardWriteTool(),

    "set_volume": SetVolumeTool(),

    "set_brightness": SetBrightnessTool(),

    "lock_screen": LockScreenTool(),

    "battery": BatteryTool(),
    "open_settings_page": OpenSettingsPageTool(),
    "browser_control": BrowserControlTool(),
    "capture_screen": CaptureScreenTool(),
    "describe_screen": DescribeScreenTool(),
    "organize_desktop": OrganizeDesktopTool(),
    "set_wallpaper": SetWallpaperTool(),
    "computer_settings": ComputerSettingsTool(),
    "dev_agent": DevAgentTool(),
    "coding_agent": DevAgentTool(),
    "weather_report": WeatherReportTool(),
    "antigravity_control": AntigravityControlTool(),
    "antigravity": AntigravityControlTool(),
    "antigravity_prompt": AntigravityPromptTool(),
    "whatsapp_control": WhatsAppTool(),
    "whatsapp": WhatsAppTool(),
    "youtube_control": YouTubeControlTool(),
    "youtube": YouTubeControlTool(),
    "youtube_music_control": YouTubeMusicTool(),
    "youtube_music": YouTubeMusicTool(),
    "file_manager_control": FileManagerTool(),
    "file_manager": FileManagerTool(),
    "skill_learner": SkillLearnerTool(),
    "learn_skill": SkillLearnerTool(),

})



# Registry aliases

REGISTRY: Dict[str, BaseTool] = TOOL_REGISTRY

registry: Dict[str, BaseTool] = TOOL_REGISTRY

TOOLS: Dict[str, BaseTool] = TOOL_REGISTRY

tools: Dict[str, BaseTool] = TOOL_REGISTRY





def register_tool(tool: BaseTool) -> None:

    """Registers a BaseTool instance in the registry by name.



    Args:

        tool: An instance of BaseTool to register.



    Raises:

        TypeError: If tool is not an instance of BaseTool.

        ValueError: If tool.name is empty or invalid.

    """

    if not isinstance(tool, BaseTool):

        raise TypeError(f"Expected BaseTool instance, got {type(tool).__name__}")

    if not getattr(tool, "name", None) or not isinstance(tool.name, str) or not tool.name.strip():

        raise ValueError("Tool name must be a non-empty string.")



    TOOL_REGISTRY[tool.name] = tool





def get_registered_tools() -> List[BaseTool]:

    """Returns a list of all unique registered tool instances.



    Returns:

        List[BaseTool]: Registered tool instances.

    """

    seen: set[int] = set()

    registered: List[BaseTool] = []

    for tool in TOOL_REGISTRY.values():

        if isinstance(tool, BaseTool) and id(tool) not in seen:

            seen.add(id(tool))

            registered.append(tool)

    return registered





def get_tools_schema() -> List[Dict[str, Any]]:

    """Returns JSON schemas for all registered tools for LLM tool calling.



    Returns:

        List[Dict[str, Any]]: List of schema definitions.

    """

    return [tool.get_schema() for tool in get_registered_tools()]





def execute_tool(name: str, args: Optional[Dict[str, Any]] = None) -> ToolResult:

    """Executes a registered tool safely and catches unknown tool errors.



    Args:

        name: The name or identifier of the tool to execute.

        args: Dictionary of keyword arguments to pass to the tool (defaults to empty dict).



    Returns:

        ToolResult: Result of the tool execution, or failure ToolResult on error.

    """

    try:

        if not name or not isinstance(name, str):

            return ToolResult(

                success=False,

                data=None,

                message="Tool name must be a non-empty string."

            )



        tool = TOOL_REGISTRY.get(name)

        if not tool:

            available_tools = ", ".join(sorted(k for k in TOOL_REGISTRY.keys()))

            return ToolResult(

                success=False,

                data=None,

                message=f"Unknown tool '{name}'. Available tools: {available_tools}."

            )



        call_args = args if args is not None else {}

        if not isinstance(call_args, dict):

            return ToolResult(

                success=False,

                data=None,

                message=f"Arguments for tool '{name}' must be provided as a dictionary."

            )



        return tool.run(**call_args)



    except TypeError as te:

        return ToolResult(

            success=False,

            data=None,

            message=f"Invalid arguments for tool '{name}': {str(te)}"

        )

    except Exception as e:

        return ToolResult(

            success=False,

            data=None,

            message=f"Unexpected error executing tool '{name}': {str(e)}"

        )





# Alias execute to execute_tool for ARCHITECTURE.md contract compatibility

execute = execute_tool





def auto_load_module_tools() -> None:

    """Auto-loads TOOLS from vision.tools, creator.tools, messaging.tools, and memory.tools.



    At import time, for module_name in ['vision.tools', 'creator.tools', 'messaging.tools', 'memory.tools']:

    try importlib.import_module(module_name); for every tool in module.TOOLS call register_tool(tool).

    Ignore only ModuleNotFoundError for that module; log any other exception and continue.

    """

    modules_to_load: List[str] = [

        "vision.tools",

        "creator.tools",

        "messaging.tools",

        "memory.tools",

    ]

    for module_name in modules_to_load:

        try:

            mod = importlib.import_module(module_name)

            tools_list = getattr(mod, "TOOLS", None)

            if tools_list:

                for tool in tools_list:

                    if isinstance(tool, BaseTool):

                        register_tool(tool)

        except ModuleNotFoundError:

            # Ignore only ModuleNotFoundError for that module

            continue

        except Exception as e:

            logger.exception("Error loading tools from module '%s': %s", module_name, e)

            continue





# Auto-load registered tools from external modules at import time

auto_load_module_tools()

