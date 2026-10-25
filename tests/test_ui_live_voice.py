"""Tests for the HUD's persistent Gemini Live voice controls."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from ui import server


@pytest.mark.asyncio
async def test_hud_voice_starts_and_stops_one_live_engine() -> None:
    """The voice button controls a single persistent Live session."""
    class FakeLiveEngine:
        voice_name = "Charon"
        connected = False

        def __init__(self, event_callback=None) -> None:
            self.stopped = asyncio.Event()

        async def run(self) -> None:
            await self.stopped.wait()

        def stop(self) -> None:
            self.stopped.set()

    websocket = AsyncMock()
    with patch("voice.gemini_live.GeminiLiveEngine", FakeLiveEngine):
        await server._start_live_voice(websocket)
        await asyncio.sleep(0)
        assert server._live_voice_engine is not None
        assert server._live_voice_task is not None
        await server._stop_live_voice(websocket)

    assert server._live_voice_engine is None
    assert server._live_voice_task is None
    websocket.send_json.assert_awaited_once()
