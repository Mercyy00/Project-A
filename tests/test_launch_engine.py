"""Test suite for universal app, file, and task launching in ui/server.py."""

import pytest
import os
import sys

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
