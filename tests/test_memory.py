"""Unit tests for Rohit's Memory and Backend Day 1 milestones."""

from __future__ import annotations

import os
from pathlib import Path
import tempfile
from typing import Generator
import aiosqlite
from fastapi.testclient import TestClient
import pytest

from memory.db import check_db_health, init_db
from ui.server import app


@pytest.fixture
def temp_db_file() -> Generator[str, None, None]:
    """Provide a temporary database file path for isolated testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        temp_path = f.name
    yield temp_path
    if os.path.exists(temp_path):
        try:
            os.remove(temp_path)
        except OSError:
            pass
    # Clean up potential WAL / SHM files
    for extra in [f"{temp_path}-wal", f"{temp_path}-shm"]:
        if os.path.exists(extra):
            try:
                os.remove(extra)
            except OSError:
                pass


@pytest.mark.asyncio
async def test_init_db_creates_tables_and_wal(temp_db_file: str) -> None:
    """Verify tables 'notes' and 'chat_history' exist and WAL mode is active."""
    await init_db(temp_db_file)

    async with aiosqlite.connect(temp_db_file) as db:
        # Check journal_mode is WAL
        async with db.execute("PRAGMA journal_mode;") as cursor:
            row = await cursor.fetchone()
            assert row is not None
            assert row[0].lower() == "wal"

        # Check required tables exist
        async with db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name IN ('notes', 'chat_history');"
        ) as cursor:
            rows = await cursor.fetchall()
            table_names = {r[0] for r in rows}
            assert "notes" in table_names
            assert "chat_history" in table_names


@pytest.mark.asyncio
async def test_db_health_check(temp_db_file: str) -> None:
    """Verify check_db_health returns True for initialized database and False for missing one."""
    assert not await check_db_health("non_existent_path/dummy.db")
    await init_db(temp_db_file)
    assert await check_db_health(temp_db_file)


def test_health_endpoint() -> None:
    """Verify GET /health returns HTTP 200 with {'status': 'healthy', 'db': 'connected'}."""
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data == {"status": "healthy", "db": "connected"}
