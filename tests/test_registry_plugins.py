"""
Unit tests for dynamic plugin auto-loading and tool registration.
Tests Section 7 requirements: register_tool, module.TOOLS auto-loading, and error isolation.
Author: Abhijit (System & Automation Engineer)
"""

import sys
import types
from typing import Any, Dict
import pytest

from tools.base import BaseTool, ToolResult
from tools.registry import (
    TOOL_REGISTRY,
    register_tool,
    auto_load_module_tools,
    execute_tool,
    get_registered_tools,
    get_tools_schema,
)


class DummyPluginTool(BaseTool):
    """Fake tool used to verify dynamic registration."""
    name: str = "dummy_plugin_action"
    description: str = "A mock tool provided by a plugin module."

    def run(self, value: int = 10, **kwargs: Any) -> ToolResult:
        return ToolResult(
            success=True,
            data={"doubled": value * 2},
            message=f"Computed value: {value * 2}"
        )


class AnotherMockTool(BaseTool):
    """Another mock tool for testing list of tools."""
    name: str = "another_mock_action"
    description: str = "Second mock tool."

    def run(self, **kwargs: Any) -> ToolResult:
        return ToolResult(success=True, data="ok", message="executed")


def test_register_tool_success() -> None:
    """Verifies that register_tool correctly registers a BaseTool."""
    tool = DummyPluginTool()
    register_tool(tool)

    assert "dummy_plugin_action" in TOOL_REGISTRY
    assert TOOL_REGISTRY["dummy_plugin_action"] == tool

    # Verify tool appears in registered list and schemas
    registered = get_registered_tools()
    assert tool in registered

    schemas = get_tools_schema()
    assert any(s["name"] == "dummy_plugin_action" for s in schemas)

    # Verify execution via execute_tool
    res = execute_tool("dummy_plugin_action", {"value": 5})
    assert res.success is True
    assert res.data["doubled"] == 10


def test_register_tool_validations() -> None:
    """Verifies type and name validation in register_tool."""
    with pytest.raises(TypeError, match="Expected BaseTool instance"):
        register_tool("not_a_tool")  # type: ignore[arg-type]

    class BadTool(BaseTool):
        name = ""

    with pytest.raises(ValueError, match="Tool name must be a non-empty string"):
        register_tool(BadTool())


def test_auto_load_module_tools_with_fake_module() -> None:
    """Verifies auto_load_module_tools registers tools exposed in module.TOOLS."""
    fake_mod_name = "vision.tools"
    mock_tool = AnotherMockTool()

    # Create a synthetic module with TOOLS list
    fake_mod = types.ModuleType(fake_mod_name)
    fake_mod.TOOLS = [mock_tool]  # type: ignore[attr-defined]

    # Temporarily inject fake module into sys.modules
    original_mod = sys.modules.get(fake_mod_name)
    sys.modules[fake_mod_name] = fake_mod

    try:
        auto_load_module_tools()

        assert "another_mock_action" in TOOL_REGISTRY
        res = execute_tool("another_mock_action")
        assert res.success is True
        assert res.data == "ok"
    finally:
        # Restore sys.modules
        if original_mod is not None:
            sys.modules[fake_mod_name] = original_mod
        else:
            sys.modules.pop(fake_mod_name, None)


def test_auto_load_ignores_missing_modules() -> None:
    """Verifies that non-existent modules do not raise errors during auto-load."""
    # Ensure missing modules pass silently without crashing
    auto_load_module_tools()


def test_auto_load_handles_module_exceptions(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifies that unexpected errors in external modules are logged and caught."""
    import importlib

    def faulty_import(name: str) -> Any:
        if name == "creator.tools":
            raise RuntimeError("Corrupted creator package")
        return importlib.__import__(name)

    monkeypatch.setattr(importlib, "import_module", faulty_import)

    # Should not raise exception
    auto_load_module_tools()
