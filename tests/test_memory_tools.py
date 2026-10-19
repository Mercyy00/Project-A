"""Unit tests for Rohit's memory/tools.py tools."""

import pytest
from memory.tools import SaveNoteTool, SearchNotesTool, TOOLS
from tools.base import ToolResult


def test_tools_list_exported():
    """Verify TOOLS list contains both SaveNoteTool and SearchNotesTool."""
    assert len(TOOLS) == 2
    tool_names = [t.name for t in TOOLS]
    assert "save_note" in tool_names
    assert "search_notes" in tool_names


def test_save_and_search_notes_tools():
    """Verify SaveNoteTool writes to SQLite and SearchNotesTool retrieves it."""
    save_tool = SaveNoteTool()
    search_tool = SearchNotesTool()

    # Save note
    res = save_tool.run(title="Exam Reminder", content="Physics exam is on Friday at 10 AM")
    assert isinstance(res, ToolResult)
    assert res.success is True
    assert "Exam Reminder" in res.message

    # Search note
    search_res = search_tool.run(query="Physics")
    assert isinstance(search_res, ToolResult)
    assert search_res.success is True
    assert len(search_res.data) >= 1
    assert search_res.data[0]["title"] == "Exam Reminder"
