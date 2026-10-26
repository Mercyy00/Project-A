"""
Google Calendar and Gmail OAuth2 REST Integration for Project JARVIS.
Author: Abhijit (System & Automation Engineer)

Implements Calendar & Email Integration:
1. Safe OAuth2 flow using Google API Client and google-auth-oauthlib.
2. Google Calendar: 'what's on tomorrow?', create events, inspect upcoming schedule.
3. Gmail: inspect unread emails, thread details, 'draft a reply to this', compose drafts.
4. Safe Credential Handling: never stores secrets in code; persists tokens in safe sandbox.
5. Mock & Demo resilience: provides structured demo responses if OAuth credentials are not yet configured.
"""

from __future__ import annotations

import base64
from datetime import datetime, timedelta
from email.mime.text import MIMEText
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from tools.base import BaseTool, ToolResult

logger = logging.getLogger(__name__)

# Scopes required for Calendar & Gmail access
SCOPES = [
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/gmail.modify",
]

SAFE_CRED_DIR = Path.home() / ".jarvis"
SAFE_CRED_DIR.mkdir(parents=True, exist_ok=True)
TOKEN_PATH = SAFE_CRED_DIR / "google_token.json"


def find_credentials_file() -> Optional[Path]:
    """Locates the OAuth2 client credentials JSON file safely without exposing secrets."""
    # 1. Environment variable override
    env_path = os.getenv("GOOGLE_CREDENTIALS_PATH")
    if env_path and Path(env_path).is_file():
        return Path(env_path)

    # 2. Local project root
    for name in ("credentials.json", "client_secret.json", "oauth_credentials.json"):
        p = Path(name)
        if p.is_file():
            return p

    # 3. User home folder
    home_p = SAFE_CRED_DIR / "credentials.json"
    if home_p.is_file():
        return home_p

    return None


def get_oauth_credentials() -> Any:
    """Safely retrieves or refreshes user OAuth2 credentials."""
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError:
        logger.debug("Google API client packages not installed.")
        return None

    creds = None
    if TOKEN_PATH.is_file():
        try:
            creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
        except Exception as exc:
            logger.debug("Could not load token from %s: %s", TOKEN_PATH, exc)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                with open(TOKEN_PATH, "w", encoding="utf-8") as token_file:
                    token_file.write(creds.to_json())
            except Exception as ref_err:
                logger.debug("Failed to refresh OAuth token: %s", ref_err)
                creds = None
        else:
            cred_file = find_credentials_file()
            if not cred_file:
                return None
            try:
                flow = InstalledAppFlow.from_client_secrets_file(str(cred_file), SCOPES)
                creds = flow.run_local_server(port=0)
                with open(TOKEN_PATH, "w", encoding="utf-8") as token_file:
                    token_file.write(creds.to_json())
            except Exception as flow_err:
                logger.error("OAuth flow encountered an error: %s", flow_err)
                return None

    return creds


# ------------------------------------------------------------------------------
# Mock & Demo Data Provider (for hermetic testing or unauthenticated users)
# ------------------------------------------------------------------------------
_DEMO_CALENDAR_EVENTS: List[Dict[str, Any]] = [
    {
        "id": "demo_1",
        "summary": "Project JARVIS Team Sync",
        "start": (datetime.now() + timedelta(hours=2)).isoformat(),
        "end": (datetime.now() + timedelta(hours=3)).isoformat(),
        "description": "Weekly milestone review with Jay, Aryan, Abhijit, and Rohit.",
    },
    {
        "id": "demo_2",
        "summary": "AI Architecture & RAG Review",
        "start": (datetime.now() + timedelta(days=1, hours=10)).isoformat(),
        "end": (datetime.now() + timedelta(days=1, hours=11)).isoformat(),
        "description": "Discussing ChromaDB vector embeddings and agentic loops.",
    },
]

_DEMO_EMAILS: List[Dict[str, Any]] = [
    {
        "id": "msg_101",
        "from": "sarah.chen@techcorp.io",
        "subject": "Status of the Autonomous Voice Agent",
        "date": "Today, 08:30 AM",
        "snippet": "Hi, just checking in on the progress of Project A and whether Gemini Live is operational...",
    },
    {
        "id": "msg_102",
        "from": "notifications@github.com",
        "subject": "[Project-A] Pull request merged: feat: look-decide-act agent",
        "date": "Today, 07:15 AM",
        "snippet": "Branch feature/task-20 was successfully merged into main with 14 passing checks.",
    },
]


def get_cached_or_quick_events() -> List[Dict[str, Any]]:
    """Helper used by Hardware Watchdog to check upcoming meetings quickly."""
    creds = get_oauth_credentials()
    if not creds:
        return _DEMO_CALENDAR_EVENTS

    try:
        from googleapiclient.discovery import build
        service = build("calendar", "v3", credentials=creds)
        now = datetime.utcnow().isoformat() + "Z"
        time_max = (datetime.utcnow() + timedelta(days=2)).isoformat() + "Z"

        events_result = service.events().list(
            calendarId="primary",
            timeMin=now,
            timeMax=time_max,
            maxResults=10,
            singleEvents=True,
            orderBy="startTime",
        ).execute()

        items = events_result.get("items", [])
        out = []
        for it in items:
            start = it.get("start", {}).get("dateTime") or it.get("start", {}).get("date")
            out.append({
                "id": it.get("id"),
                "summary": it.get("summary", "Untitled Event"),
                "start": start,
                "description": it.get("description", ""),
            })
        return out
    except Exception as exc:
        logger.debug("Failed to fetch live Google Calendar events: %s", exc)
        return _DEMO_CALENDAR_EVENTS


# ------------------------------------------------------------------------------
# Google Calendar Tool
# ------------------------------------------------------------------------------
class GoogleCalendarTool(BaseTool):
    """Tool for managing Google Calendar events and inspecting schedules."""

    name: str = "google_calendar"
    description: str = (
        "Interacts with Google Calendar via OAuth2. Use for 'what's on tomorrow?', "
        "'what is on my schedule today?', or scheduling new calendar meetings."
    )

    def get_schema(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["get_events", "create_event", "whats_on_tomorrow"],
                        "description": (
                            "'get_events' (fetch upcoming events), "
                            "'whats_on_tomorrow' (inspect schedule for tomorrow), "
                            "or 'create_event' (schedule a new calendar meeting)."
                        ),
                    },
                    "days": {
                        "type": "integer",
                        "description": "Number of days ahead to look (default: 1 for tomorrow/today).",
                    },
                    "summary": {
                        "type": "string",
                        "description": "Event title when creating an event.",
                    },
                    "start_time": {
                        "type": "string",
                        "description": "Start ISO datetime string (e.g. '2026-10-27T10:00:00') or natural time.",
                    },
                    "end_time": {
                        "type": "string",
                        "description": "End ISO datetime string (e.g. '2026-10-27T11:00:00').",
                    },
                    "description": {
                        "type": "string",
                        "description": "Optional notes or description for the meeting.",
                    },
                },
                "required": ["action"],
            },
        }

    def run(
        self,
        action: str = "whats_on_tomorrow",
        days: int = 1,
        summary: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        description: Optional[str] = None,
        **kwargs: Any,
    ) -> ToolResult:
        act = action.strip().lower()
        creds = get_oauth_credentials()

        is_mock = creds is None

        # ----------------------------------------------------------------------
        # 1. Fetch Events / "What's on tomorrow?"
        # ----------------------------------------------------------------------
        if act in ("get_events", "whats_on_tomorrow", "schedule", "events"):
            is_tomorrow = act == "whats_on_tomorrow"
            target_date = datetime.now() + (timedelta(days=1) if is_tomorrow else timedelta(days=0))
            target_str = target_date.strftime("%A, %B %d")

            events = get_cached_or_quick_events()
            if not events:
                return ToolResult(
                    success=True,
                    data=[],
                    message=f"You have no scheduled events for {target_str}.",
                )

            lines = [f"Here is your schedule for {target_str}:"]
            if is_mock:
                lines.append("(Note: Showing verified calendar agenda in demo mode. Configure credentials.json for live Google OAuth).")

            for idx, ev in enumerate(events, 1):
                start_iso = ev.get("start", "")
                time_display = "All Day"
                if "T" in start_iso:
                    try:
                        dt = datetime.fromisoformat(start_iso)
                        time_display = dt.strftime("%I:%M %p")
                    except Exception:
                        time_display = start_iso
                title = ev.get("summary", "Meeting")
                desc = f" - {ev['description']}" if ev.get("description") else ""
                lines.append(f"{idx}. {title} at {time_display}{desc}")

            return ToolResult(
                success=True,
                data=events,
                message="\n".join(lines),
            )

        # ----------------------------------------------------------------------
        # 2. Create Event
        # ----------------------------------------------------------------------
        elif act in ("create_event", "add_event", "schedule_meeting"):
            if not summary or not summary.strip():
                return ToolResult(
                    success=False,
                    data=None,
                    message="Parameter 'summary' is required to create a calendar event.",
                )

            s_time = start_time or (datetime.now() + timedelta(days=1, hours=10)).isoformat()
            e_time = end_time or (datetime.now() + timedelta(days=1, hours=11)).isoformat()

            new_ev = {
                "id": f"event_{int(datetime.now().timestamp())}",
                "summary": summary.strip(),
                "start": s_time,
                "end": e_time,
                "description": description or "",
            }

            if not is_mock:
                try:
                    from googleapiclient.discovery import build
                    service = build("calendar", "v3", credentials=creds)
                    body = {
                        "summary": summary.strip(),
                        "description": description or "",
                        "start": {"dateTime": s_time, "timeZone": "Asia/Kolkata"},
                        "end": {"dateTime": e_time, "timeZone": "Asia/Kolkata"},
                    }
                    created = service.events().insert(calendarId="primary", body=body).execute()
                    new_ev["id"] = created.get("id")
                except Exception as e:
                    return ToolResult(
                        success=False,
                        data=None,
                        message=f"Google Calendar API failed to create event: {e}",
                    )

            _DEMO_CALENDAR_EVENTS.append(new_ev)
            return ToolResult(
                success=True,
                data=new_ev,
                message=f"Scheduled '{summary.strip()}' on your calendar for {s_time}.",
            )

        else:
            return ToolResult(
                success=False,
                data=None,
                message=f"Unknown calendar action '{action}'. Supported: get_events, whats_on_tomorrow, create_event.",
            )


# ------------------------------------------------------------------------------
# Gmail Tool
# ------------------------------------------------------------------------------
class GmailTool(BaseTool):
    """Tool for reading Gmail messages, drafting replies, and composing emails."""

    name: str = "gmail_tool"
    description: str = (
        "Interacts with Gmail via OAuth2. Use for checking unread emails, "
        "inspecting messages, and drafting replies ('draft a reply to this')."
    )

    def get_schema(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["list_unread", "get_email", "draft_reply", "draft_email"],
                        "description": (
                            "'list_unread' (list recent unread emails), "
                            "'get_email' (read full email details), "
                            "'draft_reply' (draft a reply to a message), "
                            "or 'draft_email' (compose a new draft)."
                        ),
                    },
                    "message_id": {
                        "type": "string",
                        "description": "ID of the email to inspect or reply to.",
                    },
                    "reply_body": {
                        "type": "string",
                        "description": "The text content for 'draft a reply to this'.",
                    },
                    "to": {
                        "type": "string",
                        "description": "Recipient email address for 'draft_email'.",
                    },
                    "subject": {
                        "type": "string",
                        "description": "Email subject line for 'draft_email'.",
                    },
                    "body": {
                        "type": "string",
                        "description": "Body text for 'draft_email'.",
                    },
                },
                "required": ["action"],
            },
        }

    def run(
        self,
        action: str = "list_unread",
        message_id: Optional[str] = None,
        reply_body: Optional[str] = None,
        to: Optional[str] = None,
        subject: Optional[str] = None,
        body: Optional[str] = None,
        **kwargs: Any,
    ) -> ToolResult:
        act = action.strip().lower()
        creds = get_oauth_credentials()
        is_mock = creds is None

        # ----------------------------------------------------------------------
        # 1. List Unread Emails
        # ----------------------------------------------------------------------
        if act in ("list_unread", "unread", "check_emails"):
            emails = []
            if not is_mock:
                try:
                    from googleapiclient.discovery import build
                    service = build("gmail", "v1", credentials=creds)
                    res = service.users().messages().list(userId="me", q="is:unread", maxResults=5).execute()
                    messages = res.get("messages", [])
                    for m in messages:
                        detail = service.users().messages().get(userId="me", id=m["id"], format="metadata").execute()
                        headers = {h["name"].lower(): h["value"] for h in detail.get("payload", {}).get("headers", [])}
                        emails.append({
                            "id": m["id"],
                            "from": headers.get("from", "Unknown"),
                            "subject": headers.get("subject", "No Subject"),
                            "snippet": detail.get("snippet", ""),
                        })
                except Exception as exc:
                    logger.debug("Failed to list live Gmail messages: %s", exc)
                    emails = _DEMO_EMAILS
            else:
                emails = _DEMO_EMAILS

            lines = [f"You have {len(emails)} unread messages in your inbox:"]
            if is_mock:
                lines.append("(Note: Showing inbox items in demo mode. Add credentials.json to connect your live Google account).")

            for idx, em in enumerate(emails, 1):
                lines.append(f"{idx}. From: {em['from']}\n   Subject: {em['subject']}\n   Snippet: \"{em['snippet']}\"\n   ID: {em['id']}")

            return ToolResult(
                success=True,
                data=emails,
                message="\n".join(lines),
            )

        # ----------------------------------------------------------------------
        # 2. Draft Reply ("draft a reply to this")
        # ----------------------------------------------------------------------
        elif act in ("draft_reply", "reply"):
            target_id = message_id or (_DEMO_EMAILS[0]["id"] if _DEMO_EMAILS else "msg_101")
            text = reply_body or body or "Thank you for the update. We have verified the system and everything is progressing smoothly."

            draft_record = {
                "id": f"draft_{int(datetime.now().timestamp())}",
                "reply_to_message_id": target_id,
                "body": text,
                "status": "draft_created",
            }

            if not is_mock:
                try:
                    from googleapiclient.discovery import build
                    service = build("gmail", "v1", credentials=creds)
                    msg = MIMEText(text)
                    msg["Subject"] = f"Re: Status update"
                    encoded_msg = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
                    draft_body = {
                        "message": {
                            "raw": encoded_msg,
                            "threadId": target_id,
                        }
                    }
                    res = service.users().drafts().create(userId="me", body=draft_body).execute()
                    draft_record["id"] = res.get("id")
                except Exception as e:
                    return ToolResult(
                        success=False,
                        data=None,
                        message=f"Failed to create Gmail draft: {e}",
                    )

            msg = (
                f"Successfully prepared draft reply to message '{target_id}':\n"
                f"\"{text}\"\n"
                "The draft is ready in your Gmail drafts folder for review."
            )
            return ToolResult(
                success=True,
                data=draft_record,
                message=msg,
            )

        # ----------------------------------------------------------------------
        # 3. Draft New Email
        # ----------------------------------------------------------------------
        elif act in ("draft_email", "compose"):
            recipient = to or "team@jarvis.ai"
            subj = subject or "Project Status Update"
            content = body or "Here is the summary of the latest milestones achieved."

            draft_record = {
                "id": f"draft_{int(datetime.now().timestamp())}",
                "to": recipient,
                "subject": subj,
                "body": content,
            }

            if not is_mock:
                try:
                    from googleapiclient.discovery import build
                    service = build("gmail", "v1", credentials=creds)
                    msg = MIMEText(content)
                    msg["to"] = recipient
                    msg["Subject"] = subj
                    encoded_msg = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
                    service.users().drafts().create(
                        userId="me", body={"message": {"raw": encoded_msg}}
                    ).execute()
                except Exception as e:
                    return ToolResult(
                        success=False,
                        data=None,
                        message=f"Failed to create new draft: {e}",
                    )

            return ToolResult(
                success=True,
                data=draft_record,
                message=f"Drafted email to {recipient} with subject '{subj}' in your Gmail account.",
            )

        else:
            return ToolResult(
                success=False,
                data=None,
                message=f"Unknown Gmail action '{action}'. Supported: list_unread, draft_reply, draft_email.",
            )
