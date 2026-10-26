"""Unit tests for UI Server API Key Configuration and Neural Core Authentication."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient
from ui.server import app

client = TestClient(app)


def test_get_key_status_endpoint():
    """Verify key-status endpoint returns configured flag and masked key."""
    response = client.get("/api/config/key-status")
    assert response.status_code == 200
    data = response.json()
    assert "configured" in data
    assert "masked_key" in data
    assert "gemini_model" in data


def test_set_key_empty_rejected():
    """Verify setting empty key returns 422 or 400 validation error."""
    response = client.post("/api/config/set-key", json={"gemini_api_key": ""})
    assert response.status_code in (400, 422)


def test_set_key_invalid_probe_rejected():
    """Verify invalid key that fails live GenAI verification returns 400/401."""
    with patch("google.genai.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.models.get.side_effect = Exception("403 API_KEY_INVALID")
        mock_client_cls.return_value = mock_client

        response = client.post("/api/config/set-key", json={"gemini_api_key": "AIzaSy_fake_invalid_key"})
        assert response.status_code == 401
        assert "Invalid Gemini API key" in response.json().get("detail", "")


def test_set_key_successful_auth():
    """Verify valid key updates environment and reinitializes brain."""
    with patch("google.genai.Client") as mock_client_cls, \
         patch("pathlib.Path.write_text"):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client

        response = client.post(
            "/api/config/set-key",
            json={"gemini_api_key": "AIzaSy_valid_mock_key_12345"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is True
        assert os.environ.get("GEMINI_API_KEY") == "AIzaSy_valid_mock_key_12345"
        mock_client.models.get.assert_called_once()


def test_set_providers_rejects_unimplemented_tts_engine():
    """The settings API must reject TTS options that silently resolve to Edge."""
    response = client.post("/api/config/providers", json={"tts_provider": "piper"})
    assert response.status_code == 400
    assert "edge" in response.json()["detail"]
