"""Tests for Aryan's screen vision module."""
import os
from pathlib import Path
import sys
import pytest

# Ensure project root is on sys.path when running script directly
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from vision.screen import take_screenshot


def test_take_screenshot():
    """Verify primary screen capture produces a valid JPEG file."""
    path = take_screenshot()
    assert os.path.exists(path)
    assert path.endswith(".jpg")
    assert os.path.getsize(path) > 0
    print(f"\n[SUCCESS] Screenshot saved successfully at: {path}")


def test_take_screenshot_region():
    """Verify taking a screenshot of a specific bounding box region."""
    region = (0, 0, 400, 300)
    path = take_screenshot(region=region)
    assert os.path.exists(path)
    assert path.endswith(".jpg")
    assert os.path.getsize(path) > 0
    print(f"\n[SUCCESS] Region screenshot saved successfully at: {path}")


def test_take_screenshot_privacy_paused(monkeypatch):
    """Verify that screen capture raises PermissionError when VISION_PAUSED=1."""
    monkeypatch.setenv("VISION_PAUSED", "1")
    with pytest.raises(PermissionError) as exc_info:
        take_screenshot()
    assert "paused by user privacy mode" in str(exc_info.value)


if __name__ == "__main__":
    test_take_screenshot()
