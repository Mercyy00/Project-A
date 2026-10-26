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


def test_clean_chat_response_formatting():
    """Verify format_clean_chat_response strips robotic prefixes and cleans document responses."""
    from ui.server import format_clean_chat_response

    # Strips robotic multi-action prefix
    robotic = "Completed the requested steps: Opened Google Chrome."
    assert format_clean_chat_response(robotic) == "Done. Opened Google Chrome."

    # Transforms document creation into conversational summary
    doc_raw = (
        "Created the PDF document using the 'ocean' theme (detailed depth). "
        "Saved at D:\\engineers\\Project - A\\generated_reports\\Solar_Energy_20261026_120000.pdf. "
        "It includes 3 live search sources."
    )
    clean_doc = format_clean_chat_response(doc_raw)
    assert clean_doc == "Done. I researched current sources, wrote each section separately and added three charts."
    assert "D:\\engineers" not in clean_doc

    # Strips raw commands if present
    cmd_leak = "powershell -Command Get-Process\nDone. Checked system status."
    clean_cmd = format_clean_chat_response(cmd_leak)
    assert "powershell" not in clean_cmd
    assert "Done. Checked system status." in clean_cmd


def test_ui_clean_scroll_and_file_cards():
    """Verify index.html has hidden scrollbars, smooth scrolling, floating scroll pill, and clean file card."""
    res = client.get("/")
    assert res.status_code == 200
    html = res.text

    # Scrollbar hiding & smooth scroll
    assert "scrollbar-width: none !important" in html
    assert "display: none !important" in html
    assert "scroll-behavior: smooth" in html
    assert "scroll-bottom-pill" in html
    assert "scrollBottomBtn" in html

    # Clean file card elements
    assert ".file-card" in html
    assert ".file-badge" in html
    assert ".file-title" in html
    assert ".file-sub" in html
    assert ".btn-file-open" in html
    assert "Solar Energy: A Field Report" in html
