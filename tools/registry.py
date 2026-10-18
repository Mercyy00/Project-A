"""
Jarvis Tool Registry.

Registers all available system tools and provides safe execution dispatching.
"""

from typing import Any, Dict, List, Optional
from tools.base import BaseTool, ToolResult
from tools.system_tools import (
    GetSystemStatsTool,
    OpenAppTool,
    ListDirectoryTool,
    OpenWebsiteTool,
    SearchWebTool,
)


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
    "list_directory": ListDirectoryTool(),
    "open_website": OpenWebsiteTool(),
    "search_web": SearchWebTool(),
})

# Registry aliases
REGISTRY: Dict[str, BaseTool] = TOOL_REGISTRY
registry: Dict[str, BaseTool] = TOOL_REGISTRY
TOOLS: Dict[str, BaseTool] = TOOL_REGISTRY
tools: Dict[str, BaseTool] = TOOL_REGISTRY


def get_registered_tools() -> List[BaseTool]:
    """Returns a list of all registered tool instances.

    Returns:
        List[BaseTool]: Registered tool instances.
    """
    return [
        TOOL_REGISTRY["get_system_stats"],
        TOOL_REGISTRY["open_app"],
        TOOL_REGISTRY["list_directory"],
        TOOL_REGISTRY["open_website"],
        TOOL_REGISTRY["search_web"],
    ]


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
