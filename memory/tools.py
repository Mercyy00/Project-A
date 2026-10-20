"""Jarvis Memory Tools for Autonomous ReAct Brain Calling.

Exposes SaveNoteTool and SearchNotesTool conforming strictly to BaseTool
and ARCHITECTURE.md interfaces.
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict
from tools.base import BaseTool, ToolResult
from memory.storage import MemoryManager

# Singleton memory manager instance
_memory_manager = MemoryManager()


def _run_async(coro: Any) -> Any:
    """Safely execute an asynchronous coroutine in synchronous context."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If already running inside an active loop (e.g. FastAPI / asyncio thread)
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                return executor.submit(asyncio.run, coro).result()
        return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)


class SaveNoteTool(BaseTool):
    """Tool that persists a note or reminder into Jarvis's SQLite long-term memory."""

    name: str = "save_note"
    description: str = (
        "Saves an important note, reminder, or piece of information into persistent SQLite memory. "
        "Arguments: title (string summary), content (detailed body text)."
    )

    def run(self, title: str, content: str, **kwargs: Any) -> ToolResult:
        """Saves a note to SQLite database."""
        try:
            if not title or not title.strip():
                return ToolResult(
                    success=False,
                    data=None,
                    message="Note title cannot be empty."
                )
            if not content or not content.strip():
                return ToolResult(
                    success=False,
                    data=None,
                    message="Note content cannot be empty."
                )

            note_id = _run_async(_memory_manager.add_note(title.strip(), content.strip()))
            return ToolResult(
                success=True,
                data={"id": note_id, "title": title, "content": content},
                message=f"Note '{title}' saved successfully with ID {note_id}."
            )
        except Exception as exc:
            return ToolResult(
                success=False,
                data=None,
                message=f"Failed to save note: {str(exc)}"
            )

    def get_schema(self) -> Dict[str, Any]:
        """Returns OpenAPI/Gemini schema for function declaration."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Short, clear title for the note or reminder."
                    },
                    "content": {
                        "type": "string",
                        "description": "The detailed information or reminder text to store."
                    }
                },
                "required": ["title", "content"]
            }
        }


class SearchNotesTool(BaseTool):
    """Tool that searches through previously saved notes in persistent SQLite memory."""

    name: str = "search_notes"
    description: str = (
        "Searches through user notes and memories stored in SQLite using a query keyword. "
        "Argument: query (string keyword or phrase)."
    )

    def run(self, query: str, **kwargs: Any) -> ToolResult:
        """Searches notes in SQLite database."""
        try:
            if not query or not query.strip():
                return ToolResult(
                    success=False,
                    data=[],
                    message="Search query cannot be empty."
                )

            results = _run_async(_memory_manager.search_notes(query.strip()))
            count = len(results)
            return ToolResult(
                success=True,
                data=results,
                message=f"Found {count} matching note{'s' if count != 1 else ''}."
            )
        except Exception as exc:
            return ToolResult(
                success=False,
                data=[],
                message=f"Failed to search notes: {str(exc)}"
            )

    def get_schema(self) -> Dict[str, Any]:
        """Returns OpenAPI/Gemini schema for function declaration."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search phrase or keyword to locate relevant notes."
                    }
                },
                "required": ["query"]
            }
        }


# Canonical exported tools list for Abhijit's registry auto-loader (Catch-Up Plan Section 4 & 7)
TOOLS = [SaveNoteTool(), SearchNotesTool()]
