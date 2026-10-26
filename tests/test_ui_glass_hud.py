"""Tests for Glass HUD UI & REST Endpoints."""

import pytest
from fastapi.testclient import TestClient

from ui.server import app

client = TestClient(app)


def test_index_html_contains_glass_mockup_design_tokens_and_globe():
    """Verify index.html contains all design tokens, animations, and SVG globe elements from Main.dc.html."""
    res = client.get("/")
    assert res.status_code == 200
    html = res.text

    # Orbits and animations
    assert ".o1" in html
    assert ".o2" in html
    assert ".o3" in html
    assert ".breathe" in html
    assert ".mer" in html
    assert ".scan" in html
    assert ".tick" in html

    # Prefers-reduced-motion
    assert "prefers-reduced-motion: reduce" in html

    # Design tokens & modes
    assert ":root" in html
    assert '[data-theme="stealth"]' in html
    assert '[data-theme="combat"]' in html

    # Agent data-state attributes
    assert '[data-state="thinking"]' in html
    assert '[data-state="speaking"]' in html
    assert '[data-state="executing_tool"]' in html
    assert '[data-state="error"]' in html

    # Views
    assert 'data-view="chat"' in html
    assert 'data-view="voice"' in html
    assert 'data-view="documents"' in html
    assert 'data-view="memory"' in html
    assert 'data-view="automations"' in html


def test_recent_conversations_endpoint():
    """Verify /api/conversations/recent returns list."""
    res = client.get("/api/conversations/recent")
    assert res.status_code == 200
    assert isinstance(res.json(), list)


def test_recent_documents_endpoint():
    """Verify /api/documents/recent returns list of document descriptors."""
    res = client.get("/api/documents/recent")
    assert res.status_code == 200
    docs = res.json()
    assert isinstance(docs, list)


def test_open_file_endpoint_validation():
    """Verify /api/open-file validates parameters properly."""
    # Empty path -> 400
    res_bad = client.post("/api/open-file", json={})
    assert res_bad.status_code == 400

    # Non-existent file -> 200 with success=False
    res_not_found = client.post("/api/open-file", json={"file_path": "non_existent_file_xyz_123.pdf"})
    assert res_not_found.status_code == 200
    assert res_not_found.json()["success"] is False
