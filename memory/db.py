"""Persistent SQLite database manager for Project Jarvis.

Handles connection pooling, schema initialization, and health checks
for notes and conversation history using aiosqlite and WAL mode.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import AsyncGenerator, Optional
import aiosqlite
from dotenv import load_dotenv

load_dotenv()

DEFAULT_DB_PATH = os.getenv("DATABASE_PATH", "memory/jarvis.db")


async def get_db_path(custom_path: Optional[str] = None) -> Path:
    """Resolve database file path and ensure parent directory exists."""
    target_path = Path(custom_path or DEFAULT_DB_PATH)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    return target_path


async def init_db(db_path: Optional[str] = None) -> None:
    """Initialize the SQLite database with WAL mode and required tables.

    Creates tables:
    - notes: id, title, content, created_at
    - chat_history: id, role, content, timestamp
    """
    path = await get_db_path(db_path)
    try:
        async with aiosqlite.connect(str(path)) as db:
            # Enable WAL (Write-Ahead Logging) mode for high performance concurrency
            await db.execute("PRAGMA journal_mode=WAL;")
            await db.execute("PRAGMA synchronous=NORMAL;")

            # Table for persistent user notes / tasks
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS notes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                """
            )

            # Table for multi-turn conversation history
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS chat_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
            await db.commit()
    except Exception as exc:
        raise RuntimeError(f"Database initialization failed at '{path}': {exc}") from exc


async def get_db(db_path: Optional[str] = None) -> AsyncGenerator[aiosqlite.Connection, None]:
    """Async generator yielding an active aiosqlite connection."""
    path = await get_db_path(db_path)
    async with aiosqlite.connect(str(path)) as db:
        db.row_factory = aiosqlite.Row
        yield db


async def check_db_health(db_path: Optional[str] = None) -> bool:
    """Verify database accessibility and readiness."""
    try:
        path = await get_db_path(db_path)
        if not path.exists():
            return False
        async with aiosqlite.connect(str(path)) as db:
            async with db.execute("SELECT 1;") as cursor:
                row = await cursor.fetchone()
                return row is not None and row[0] == 1
    except Exception:
        return False
