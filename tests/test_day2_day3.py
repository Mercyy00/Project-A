"""Unit and integration tests for Rohit's Day 2 and Day 3 milestones."""

from __future__ import annotations

import os
from pathlib import Path
import tempfile
from typing import Generator
import pytest
from fastapi.testclient import TestClient

from memory.db import init_db
from memory.storage import MemoryManager
from ui.server import app


@pytest.fixture
def temp_db() -> Generator[str, None, None]:
    """Provide a temporary database path for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
    yield path
    for p in [path, f"{path}-wal", f"{path}-shm"]:
        if os.path.exists(p):
            try:
                os.remove(p)
            except OSError:
                pass


@pytest.mark.asyncio
async def test_memory_manager_crud(temp_db: str) -> None:
    """Test Note taking CRUD and search operations in MemoryManager."""
    await init_db(temp_db)
    manager = MemoryManager(temp_db)

    # 1. Add notes
    id1 = await manager.add_note("Project Architecture", "Review Section 4 interfaces")
    id2 = await manager.add_note("Buy Groceries", "Milk, eggs, coffee beans")
    assert id1 > 0
    assert id2 > id1

    # 2. List notes
    notes = await manager.list_notes(limit=10)
    assert len(notes) == 2
    assert notes[0]["id"] == id2  # Most recent first
    assert notes[0]["title"] == "Buy Groceries"

    # 3. Search notes
    results = await manager.search_notes("coffee")
    assert len(results) == 1
    assert results[0]["title"] == "Buy Groceries"

    empty_results = await manager.search_notes("NonExistentKeywordXYZ")
    assert len(empty_results) == 0

    # 4. Chat history interaction
    await manager.save_interaction("user", "Hello Jarvis")
    await manager.save_interaction("assistant", "Greetings Rohit")
    history = await manager.get_recent_history(limit=5)
    assert len(history) == 2
    assert history[0]["role"] == "user"
    assert history[1]["role"] == "assistant"


def test_rest_notes_api() -> None:
    """Test POST /api/notes and GET /api/notes REST endpoints."""
    with TestClient(app) as client:
        # Create a note
        post_res = client.post(
            "/api/notes",
            json={"title": "Buy Groceries", "content": "Milk, eggs, bread"},
        )
        assert post_res.status_code == 201
        created = post_res.json()
        assert created["title"] == "Buy Groceries"
        assert "id" in created

        # List notes
        get_res = client.get("/api/notes")
        assert get_res.status_code == 200
        notes = get_res.json()
        assert isinstance(notes, list)
        assert any(n["title"] == "Buy Groceries" for n in notes)

        # Search notes
        search_res = client.get("/api/notes/search?q=Groceries")
        assert search_res.status_code == 200
        matched = search_res.json()
        assert len(matched) >= 1
        assert "Groceries" in matched[0]["title"]


def test_telemetry_endpoint() -> None:
    """Test GET /api/telemetry returns telemetry structure."""
    with TestClient(app) as client:
        res = client.get("/api/telemetry")
        assert res.status_code == 200
        data = res.json()
        assert "success" in data
        if data["success"]:
            assert "cpu_usage_percent" in data["data"]
            assert "ram_usage_percent" in data["data"]


def test_websocket_channel() -> None:
    """Test /ws/jarvis bidirectional WebSocket communication."""
    with TestClient(app) as client:
        with client.websocket_connect("/ws/jarvis") as ws:
            # Send chat action
            ws.send_json({"action": "chat", "text": "Report system status"})

            # Receive thinking status
            msg1 = ws.receive_json()
            assert msg1["type"] == "status"
            assert msg1["status"] == "thinking"

            # Receive response (may be preceded by tool_steps if tools executed)
            msg2 = ws.receive_json()
            if msg2.get("type") == "tool_steps":
                assert "steps" in msg2
                msg2 = ws.receive_json()

            assert msg2["type"] == "response"
            assert "text" in msg2
            assert len(msg2["text"]) > 0

            # Receive idle status
            msg3 = ws.receive_json()
            assert msg3["type"] == "status"
            assert msg3["status"] == "idle"


def test_hud_html_serving() -> None:
    """Test GET / returns HTML single-page HUD client."""
    with TestClient(app) as client:
        res = client.get("/")
        assert res.status_code == 200
        assert "text/html" in res.headers["content-type"]
        assert "JARVIS" in res.text
