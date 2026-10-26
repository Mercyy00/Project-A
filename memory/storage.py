"""Persistent storage and memory manager for Project Jarvis.

Implements note taking CRUD, conversation history logging, and memory search
using SQLite, aiosqlite, and ChromaDB vector store.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional
import aiosqlite
from memory.db import get_db, get_db_path, init_db


class MemoryManager:
    """Manages persistent SQLite operations for notes and interaction history."""

    def __init__(self, db_path: Optional[str] = None) -> None:
        """Initialize MemoryManager with target database path."""
        self.db_path = db_path

    async def _ensure_db_initialized(self) -> None:
        """Ensure the database and tables are ready before executing operations."""
        path = await get_db_path(self.db_path)
        if not path.exists():
            await init_db(self.db_path)

    async def add_note(self, title: str, content: str) -> int:
        """Create and persist a new user note.

        Args:
            title: Short descriptive title of the note.
            content: Body text of the note.

        Returns:
            The primary key integer ID of the created note.
        """
        await self._ensure_db_initialized()
        path = await get_db_path(self.db_path)
        try:
            async with aiosqlite.connect(str(path)) as db:
                cursor = await db.execute(
                    "INSERT INTO notes (title, content) VALUES (?, ?);",
                    (title.strip(), content.strip()),
                )
                await db.commit()
                note_id = cursor.lastrowid or 0

                # Auto-sync to ChromaDB semantic vector store
                try:
                    from memory.vector_store import VectorMemoryStore
                    vstore = VectorMemoryStore.get_instance()
                    vstore.add_note(note_id=note_id, title=title.strip(), content=content.strip())
                except Exception:
                    pass

                return note_id
        except Exception as exc:
            raise RuntimeError(f"Failed to add note '{title}': {exc}") from exc

    async def list_notes(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Retrieve the most recent persistent notes.

        Args:
            limit: Maximum number of notes to return (default: 20).

        Returns:
            A list of dictionary representations of notes.
        """
        await self._ensure_db_initialized()
        path = await get_db_path(self.db_path)
        try:
            async with aiosqlite.connect(str(path)) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute(
                    """
                    SELECT id, title, content, created_at
                    FROM notes
                    ORDER BY id DESC
                    LIMIT ?;
                    """,
                    (limit,),
                ) as cursor:
                    rows = await cursor.fetchall()
                    return [
                        {
                            "id": row["id"],
                            "title": row["title"],
                            "content": row["content"],
                            "created_at": str(row["created_at"]),
                        }
                        for row in rows
                    ]
        except Exception as exc:
            raise RuntimeError(f"Failed to list notes: {exc}") from exc

    async def search_notes(self, query: str) -> List[Dict[str, Any]]:
        """Search persistent notes matching query string in title or content.

        Args:
            query: The search substring or keyword.

        Returns:
            List of matching notes.
        """
        await self._ensure_db_initialized()
        path = await get_db_path(self.db_path)
        try:
            wildcard = f"%{query.strip()}%"
            async with aiosqlite.connect(str(path)) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute(
                    """
                    SELECT id, title, content, created_at
                    FROM notes
                    WHERE title LIKE ? OR content LIKE ?
                    ORDER BY id DESC;
                    """,
                    (wildcard, wildcard),
                ) as cursor:
                    rows = await cursor.fetchall()
                    return [
                        {
                            "id": row["id"],
                            "title": row["title"],
                            "content": row["content"],
                            "created_at": str(row["created_at"]),
                        }
                        for row in rows
                    ]
        except Exception as exc:
            raise RuntimeError(f"Failed to search notes with query '{query}': {exc}") from exc

    async def save_interaction(self, role: str, content: str) -> None:
        """Persist a conversation turn into chat_history table.

        Args:
            role: Speaker role ('user' or 'assistant').
            content: Message text.
        """
        await self._ensure_db_initialized()
        path = await get_db_path(self.db_path)
        try:
            async with aiosqlite.connect(str(path)) as db:
                cursor = await db.execute(
                    "INSERT INTO chat_history (role, content) VALUES (?, ?);",
                    (role.strip(), content.strip()),
                )
                await db.commit()
                turn_id = cursor.lastrowid or 0

                # Auto-sync to ChromaDB semantic vector store
                try:
                    from memory.vector_store import VectorMemoryStore
                    vstore = VectorMemoryStore.get_instance()
                    vstore.add_chat_turn(turn_id=str(turn_id), role=role.strip(), content=content.strip())
                except Exception:
                    pass
        except Exception as exc:
            raise RuntimeError(f"Failed to save interaction for role '{role}': {exc}") from exc

    async def get_recent_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Retrieve the most recent conversation messages in chronological order.

        Args:
            limit: Maximum number of recent turns to retrieve.

        Returns:
            List of message dicts with role, content, and timestamp.
        """
        await self._ensure_db_initialized()
        path = await get_db_path(self.db_path)
        try:
            async with aiosqlite.connect(str(path)) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute(
                    """
                    SELECT id, role, content, timestamp
                    FROM chat_history
                    ORDER BY id DESC
                    LIMIT ?;
                    """,
                    (limit,),
                ) as cursor:
                    rows = await cursor.fetchall()
                    # Reverse so oldest in window is first for LLM prompt context
                    return [
                        {
                            "id": row["id"],
                            "role": row["role"],
                            "content": row["content"],
                            "timestamp": str(row["timestamp"]),
                        }
                        for row in reversed(rows)
                    ]
        except Exception as exc:
            raise RuntimeError(f"Failed to get recent history: {exc}") from exc

    async def get_relevant_context(self, query: str, limit: int = 5) -> List[str]:
        """Interface for Jay's Core Brain: retrieves relevant context snippets using semantic RAG and keyword search."""
        context: List[str] = []

        # 1. First retrieve via semantic ChromaDB vector search
        try:
            from memory.vector_store import VectorMemoryStore
            vstore = VectorMemoryStore.get_instance()
            semantic_matches = vstore.query_notes(query, n_results=limit)
            for m in semantic_matches:
                context.append(f"Semantic Note [{m['title']}]: {m['content']}")
        except Exception:
            pass

        # 2. Complement with SQLite keyword search if needed
        if len(context) < limit:
            try:
                notes = await self.search_notes(query)
                for n in notes:
                    item = f"Note [{n['title']}]: {n['content']}"
                    if item not in context:
                        context.append(item)
                    if len(context) >= limit:
                        break
            except Exception:
                pass

        return context
