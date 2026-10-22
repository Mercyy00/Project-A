"""Tests for the Neural TTS endpoint in the UI server."""

import pytest
from fastapi.testclient import TestClient
from ui.server import app

client = TestClient(app)


def test_neural_tts_endpoint_english():
    """Verify English text generates valid MP3 neural audio response."""
    response = client.get("/api/tts?text=Welcome+back+sir.+Jarvis+is+online.")
    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/mpeg"
    assert len(response.content) > 1000


def test_neural_tts_endpoint_hindi():
    """Verify Hindi Devanagari text generates valid MP3 neural audio response."""
    response = client.get("/api/tts?text=%E0%A4%A8%E0%A4%AE%E0%A4%B8%E0%A5%8D%E0%A4%A4%E0%A5%87+%E0%A4%B8%E0%A4%B0")
    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/mpeg"
    assert len(response.content) > 1000


def test_neural_tts_endpoint_empty_text():
    """Verify empty query parameter returns 422 validation error."""
    response = client.get("/api/tts?text=")
    assert response.status_code == 422
