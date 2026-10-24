"""Test suite for universal app, file, and task launching in ui/server.py."""

import pytest
import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

# Ensure project root in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ui.server import (
    normalize_command,
    find_dynamic_app_in_system,
    find_user_file_or_folder,
    try_launch_system_app,
)


def test_normalize_command():
    assert normalize_command("Hey, Jarvis, Open.File Manager.") == "hey jarvis open file manager"
    assert normalize_command("Open WhatsApp and send hi to Abhijit.") == "open whatsapp and send hi to abhijit"
    assert normalize_command("File manager") == "file manager"
    assert normalize_command("brave") == "brave"


def test_file_manager_launch():
    res = try_launch_system_app("Hey, Jarvis, Open.File Manager.")
    assert res is not None
    label, detail = res
    assert "File Manager" in label or "Explorer" in label


def test_direct_app_name():
    res = try_launch_system_app("File manager")
    assert res is not None
    label, detail = res
    assert "File Manager" in label or "Explorer" in label

    res_brave = try_launch_system_app("brave")
    assert res_brave is not None
    label_brave, _ = res_brave
    assert "Brave" in label_brave


def test_downloads_folder():
    res = try_launch_system_app("Open downloads")
    assert res is not None
    label, _ = res
    assert "Downloads" in label


def test_compound_whatsapp_task():
    res = try_launch_system_app("Open WhatsApp and send hi to Abhijit.")
    assert res is not None
    label, detail = res
    assert "WhatsApp" in label
    assert detail is not None
    assert "Abhijit" in detail
    assert "hi" in detail


def test_compound_chrome_search():
    res = try_launch_system_app("Open Chrome and search best AI tools")
    assert res is not None
    label, detail = res
    assert "Chrome" in label
    assert detail is not None
    assert "best AI tools" in detail


def test_user_file_search():
    res = try_launch_system_app("open catchup plan")
    assert res is not None
    label, _ = res
    assert "Catchup_Plan" in label or "pdf" in label.lower()


def test_conversational_queries_not_hijacked():
    # Greetings and status queries should NOT trigger app launches
    assert try_launch_system_app("Hey Jarvis, who are you?") is None
    assert try_launch_system_app("What are your capabilities?") is None
    assert try_launch_system_app("I am Rohit") is None
    assert try_launch_system_app("What is the time?") is None
    assert try_launch_system_app("Check system specs") is None


@pytest.mark.asyncio
async def test_dynamic_multi_user_neutral_by_default():
    from ui.server import _generate_response

    # New guest user session (not Rohit)
    guest_session = {"name": "User", "is_known": False}
    resp = await _generate_response("Hey Jarvis", session_user=guest_session)
    assert "Rohit" not in resp
    assert "Greetings!" in resp or "Jarvis is online" in resp

    resp_who = await _generate_response("Who am I?", session_user=guest_session)
    assert "Rohit" not in resp_who
    assert "Sir" in resp_who or "User" in resp_who


@pytest.mark.asyncio
async def test_dynamic_multi_user_introduction_and_reset():
    from ui.server import _generate_response

    session = {"name": "User", "is_known": False}
    intro_resp = await _generate_response("Hey Jarvis, I am Shiv", session_user=session)
    assert "Shiv" in intro_resp
    assert session["name"] == "Shiv"
    assert session["is_known"] is True

    greet_resp = await _generate_response("Hey Jarvis", session_user=session)
    assert "Shiv" in greet_resp

    # Reset
    reset_resp = await _generate_response("reset user", session_user=session)
    assert "cleared" in reset_resp or "neutral" in reset_resp
    assert session["is_known"] is False


@pytest.mark.asyncio
async def test_http_chat_waits_for_core_and_returns_its_response(monkeypatch):
    """HTTP chat must return the actual core result without a short timeout."""
    from core import service
    from ui import server

    core_handler = AsyncMock(return_value={
        "text": "The requested operation completed.",
        "tool_steps": ["open_app({'app_name': 'chrome'})"],
        "source": "ui_http",
    })
    monkeypatch.setattr(service, "handle_text", core_handler)
    monkeypatch.setattr(
        server.asyncio,
        "wait_for",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("unexpected timeout")),
    )

    result = await server.http_chat(server.ChatPayload(text="open Chrome"))

    assert result["text"] == "The requested operation completed."
    assert result["tool_steps"] == ["open_app({'app_name': 'chrome'})"]
    core_handler.assert_awaited_once_with("open Chrome", source="ui_http", mode="normal")


@pytest.mark.asyncio
async def test_http_chat_reports_core_failure_without_fabricating_success(monkeypatch):
    """A core failure must surface as an HTTP error rather than a canned success."""
    from fastapi import HTTPException
    from core import service
    from ui import server

    monkeypatch.setattr(service, "handle_text", AsyncMock(return_value={
        "text": "Subsystem execution error: provider unavailable",
        "tool_steps": [],
        "source": "ui_http",
    }))

    with pytest.raises(HTTPException) as error:
        await server.http_chat(server.ChatPayload(text="open Chrome"))

    assert error.value.status_code == 503


def test_stt_endpoint_accepts_raw_browser_audio(monkeypatch: pytest.MonkeyPatch) -> None:
    """The browser posts raw WebM, matching the local Whisper endpoint contract."""
    from fastapi.testclient import TestClient
    from ui import server

    expected_audio = b"webm-audio" * 16

    class FakeTranscriber:
        def transcribe_file(self, audio_path: str | Path) -> dict[str, str]:
            assert Path(audio_path).read_bytes() == expected_audio
            return {"text": "Open Chrome", "language": "en"}

    monkeypatch.setattr("voice.stt.get_transcriber", lambda: FakeTranscriber())
    with TestClient(server.app) as client:
        response = client.post(
            "/api/stt",
            content=expected_audio,
            headers={"Content-Type": "audio/webm"},
        )

    assert response.status_code == 200
    assert response.json() == {"success": True, "text": "Open Chrome", "language": "en"}


@pytest.mark.asyncio
async def test_generate_response_does_not_claim_success_when_services_are_down(monkeypatch):
    """The HUD fallback must be transparent if neither the core nor Gemini is available."""
    from core import service
    from ui import server

    async def fail_core(*_args, **_kwargs):
        raise RuntimeError("provider unavailable")

    monkeypatch.setattr(service, "handle_text", fail_core)
    monkeypatch.setattr(server, "get_genai_client", lambda: None)

    response = await server._generate_response("Explain quantum computing")

    assert "couldn't reach" in response.lower()
    assert "acknowledged your directive" not in response.lower()


@pytest.mark.asyncio
async def test_device_active_tasks_inspection():
    from ui.server import _generate_response

    resp = await _generate_response("show active tasks")
    assert "Active PC Tasks" in resp or "Running Applications" in resp
    assert "PID" in resp or "RAM" in resp


@pytest.mark.asyncio
async def test_device_deep_file_search():
    from ui.server import _generate_response

    resp = await _generate_response("search files for catchup")
    assert "Device File Search Results" in resp or "Found" in resp
    assert "Catchup_Plan" in resp or "pdf" in resp.lower()
