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
    assert "jarvis-pwa-v5" in res.text


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
