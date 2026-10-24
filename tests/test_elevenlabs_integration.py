"""Tests for ElevenLabs TTS integration from MARK LVI."""

import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from ui.server import app
from voice.tts import JarvisSpeaker

client = TestClient(app)


def test_providers_endpoint_includes_elevenlabs():
    """Verify /api/config/providers reports ElevenLabs configuration options."""
    res = client.get("/api/config/providers")
    assert res.status_code == 200
    data = res.json()
    assert "elevenlabs_voice_id" in data
    assert "has_elevenlabs" in data
    assert "tts_provider" in data


def test_set_providers_config_elevenlabs():
    """Verify setting ElevenLabs provider updates environment and response."""
    payload = {
        "tts_provider": "elevenlabs",
        "elevenlabs_voice_id": "pNInz6obpgDQGcFmaJgB",
        "elevenlabs_api_key": "test_elevenlabs_dummy_key",
    }
    res = client.post("/api/config/providers", json=payload)
    assert res.status_code == 200
    assert res.json()["success"] is True
    assert os.getenv("TTS_PROVIDER") == "elevenlabs"
    assert os.getenv("ELEVENLABS_VOICE_ID") == "pNInz6obpgDQGcFmaJgB"
    assert os.getenv("ELEVENLABS_API_KEY") == "test_elevenlabs_dummy_key"


@pytest.mark.asyncio
async def test_elevenlabs_async_fallback_when_api_fails(monkeypatch, tmp_path):
    """Verify that if ElevenLabs API returns error, JarvisSpeaker seamlessly falls back to Edge-TTS."""
    monkeypatch.setenv("TTS_PROVIDER", "elevenlabs")
    monkeypatch.setenv("ELEVENLABS_API_KEY", "invalid_key")
    speaker = JarvisSpeaker()
    speaker.temp_dir = tmp_path

    # Mock _generate_audio_elevenlabs_async to simulate 401/fail
    mock_eleven = AsyncMock(return_value=False)
    monkeypatch.setattr(speaker, "_generate_audio_elevenlabs_async", mock_eleven)

    # Mock edge-tts fallback to succeed
    async def mock_edge(text, voice, out_path):
        out_path.write_bytes(b"dummy_edge_audio_data")
        return True

    monkeypatch.setattr(speaker, "_generate_audio_edge", mock_edge)

    result_path = await speaker.speak_to_file_async("Testing fallback mechanism", lang="en")
    assert result_path != ""
    assert Path(result_path).is_file()
    assert Path(result_path).read_bytes() == b"dummy_edge_audio_data"
    assert mock_eleven.called


@pytest.mark.asyncio
async def test_elevenlabs_async_success_path(monkeypatch, tmp_path):
    """Verify that when ElevenLabs returns audio bytes, it is saved and cached."""
    monkeypatch.setenv("TTS_PROVIDER", "elevenlabs")
    monkeypatch.setenv("ELEVENLABS_API_KEY", "valid_key")
    speaker = JarvisSpeaker()
    speaker.temp_dir = tmp_path

    async def mock_eleven(text, out_path):
        out_path.write_bytes(b"dummy_elevenlabs_mp3_stream")
        return True

    monkeypatch.setattr(speaker, "_generate_audio_elevenlabs_async", mock_eleven)

    result_path = await speaker.speak_to_file_async("Hello from ElevenLabs", lang="en")
    assert result_path != ""
    assert Path(result_path).is_file()
    assert Path(result_path).read_bytes() == b"dummy_elevenlabs_mp3_stream"
