"""Tests for Desktop Application & PWA integration."""

from fastapi.testclient import TestClient

from ui.server import app
from ui.app import is_server_ready

client = TestClient(app)


def test_manifest_endpoint():
    """Verify manifest.json is served with application/manifest+json."""
    res = client.get("/manifest.json")
    assert res.status_code == 200
    assert "manifest+json" in res.headers["content-type"]
    data = res.json()
    assert data["name"] == "J.A.R.V.I.S. Autonomous AI Assistant"
    assert data["display"] == "standalone"


def test_service_worker_endpoint():
    """Verify sw.js is served with application/javascript."""
    res = client.get("/sw.js")
    assert res.status_code == 200
    assert "javascript" in res.headers["content-type"]
    assert "jarvis-pwa-v7" in res.text


def test_icon_endpoint():
    """Verify icon.svg is served with image/svg+xml."""
    res = client.get("/icon.svg")
    assert res.status_code == 200
    assert "svg" in res.headers["content-type"]
    assert "<svg" in res.text


def test_index_html_contains_pwa_elements():
    """Verify index.html has manifest link and install button."""
    res = client.get("/")
    assert res.status_code == 200
    assert '<link rel="manifest" href="/manifest.json">' in res.text
    assert 'id="installAppBtn"' in res.text


def test_chat_renderer_escapes_user_and_model_content():
    """Chat text is HTML-escaped before trusted formatting tags are inserted."""
    res = client.get("/")
    assert res.status_code == 200
    assert "const escapedText = String(text).replace" in res.text
    assert "const formatted = escapedText" in res.text


def test_hud_greets_once_when_server_link_opens():
    """The HUD welcomes the user without an extra Gemini request."""
    res = client.get("/")
    assert res.status_code == 200
    assert "startupGreetingShown" in res.text
    assert "Hello, sir. JARVIS is ready when you are." in res.text


def test_hud_starts_one_live_voice_session_on_app_connect():
    """The voice call starts with the HUD and stays open across speech turns."""
    res = client.get("/")
    assert res.status_code == 200
    assert "greetOnStartup();\n            startVoice();" in res.text
