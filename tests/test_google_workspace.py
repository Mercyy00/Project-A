"""
Unit and Integration Tests for Google Calendar and Gmail Integration (Task 8).
Verifies OAuth handling, "what's on tomorrow?", "draft a reply to this",
and Google Workspace tool execution.
"""

from pathlib import Path
import pytest
from unittest.mock import MagicMock, patch

from tools.google_workspace_tool import (
    GoogleCalendarTool,
    GmailTool,
    find_credentials_file,
    get_cached_or_quick_events,
)
from ui.server import parse_google_workspace_intent


class TestCredentialsHandling:
    """Test safe credential discovery without exposing secrets."""

    def test_find_credentials_env_override(self, tmp_path, monkeypatch):
        cred_file = tmp_path / "mock_creds.json"
        cred_file.write_text('{"installed": {"client_id": "test"}}', encoding="utf-8")
        monkeypatch.setenv("GOOGLE_CREDENTIALS_PATH", str(cred_file))

        found = find_credentials_file()
        assert found is not None
        assert str(found) == str(cred_file)

    def test_find_credentials_none_when_missing(self, monkeypatch):
        monkeypatch.delenv("GOOGLE_CREDENTIALS_PATH", raising=False)
        with patch("pathlib.Path.is_file", return_value=False):
            assert find_credentials_file() is None


class TestGoogleCalendarTool:
    """Test GoogleCalendarTool actions."""

    def test_whats_on_tomorrow(self):
        tool = GoogleCalendarTool()
        res = tool.run(action="whats_on_tomorrow")
        assert res.success is True
        assert "schedule for" in res.message.lower()
        assert len(res.data) >= 1

    def test_create_calendar_event(self):
        tool = GoogleCalendarTool()
        res = tool.run(
            action="create_event",
            summary="Quantum Error Mitigation Seminar",
            description="Presentation on surface codes",
        )
        assert res.success is True
        assert "Quantum Error Mitigation Seminar" in res.message
        assert res.data["summary"] == "Quantum Error Mitigation Seminar"


class TestGmailTool:
    """Test GmailTool actions."""

    def test_list_unread_emails(self):
        tool = GmailTool()
        res = tool.run(action="list_unread")
        assert res.success is True
        assert "unread messages" in res.message.lower()
        assert len(res.data) >= 1
        assert "from" in res.data[0]
        assert "subject" in res.data[0]

    def test_draft_reply(self):
        tool = GmailTool()
        res = tool.run(
            action="draft_reply",
            message_id="msg_101",
            reply_body="Confirmed. We have finalized the integration and tests are passing.",
        )
        assert res.success is True
        assert "draft reply to message 'msg_101'" in res.message
        assert res.data["status"] == "draft_created"
        assert "Confirmed" in res.data["body"]

    def test_compose_new_draft(self):
        tool = GmailTool()
        res = tool.run(
            action="draft_email",
            to="team@project-a.org",
            subject="Release 2.0 Update",
            body="All milestone tasks 15, 16, 20, 23, 26, 27, 28 are completed.",
        )
        assert res.success is True
        assert "Drafted email to team@project-a.org" in res.message
        assert res.data["to"] == "team@project-a.org"


class TestFastPathIntentParsing:
    """Test server fast-path regex parsing for calendar and email queries."""

    def test_calendar_intent_parse(self):
        intent1 = parse_google_workspace_intent("What's on tomorrow?")
        assert intent1 is not None
        assert intent1["tool"] in ("calendar", "google_calendar")
        assert intent1["action"] == "whats_on_tomorrow"

        intent2 = parse_google_workspace_intent("Schedule meeting with Dr. Sarah at 3pm")
        assert intent2 is not None
        assert intent2["tool"] in ("calendar", "google_calendar")
        assert intent2["action"] == "create_event"

    def test_gmail_intent_parse(self):
        intent1 = parse_google_workspace_intent("Check my unread emails")
        assert intent1 is not None
        assert intent1["tool"] in ("gmail", "gmail_tool")
        assert intent1["action"] == "list_unread"

        intent2 = parse_google_workspace_intent("Draft a reply to this: Looks great, proceed with launch.")
        assert intent2 is not None
        assert intent2["tool"] in ("gmail", "gmail_tool")
        assert intent2["action"] == "draft_reply"
        assert "Looks great" in intent2["reply_body"]
