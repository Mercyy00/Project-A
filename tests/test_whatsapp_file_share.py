"""
Unit and Integration Tests for WhatsApp File Sharing (Task 9).
Verifies Windows CF_HDROP clipboard drop, contact selection, caption typing,
WhatsAppTool.send_file execution, and fast-path intent matching.
"""

import os
from pathlib import Path
import pytest
from unittest.mock import MagicMock, patch

from tools.whatsapp_tool import (
    WhatsAppTool,
    copy_file_to_clipboard,
)
from messaging.whatsapp import share_whatsapp_file
from ui.server import parse_whatsapp_intent
from tools.base import ToolResult


class TestClipboardFileDrop:
    """Test Windows CF_HDROP file-drop clipboard placement."""

    def test_copy_existing_file_to_clipboard(self, tmp_path):
        test_file = tmp_path / "quantum_notes.pdf"
        test_file.write_bytes(b"%PDF-1.4 Mock PDF Content for testing")

        success = copy_file_to_clipboard(str(test_file))
        if os.name == "nt":
            assert success is True
        else:
            assert success is False

    def test_copy_non_existent_file_returns_false(self):
        success = copy_file_to_clipboard("non_existent_path_xyz_123.doc")
        assert success is False


class TestWhatsAppToolFileSharing:
    """Test WhatsAppTool.send_file validation and automation sequence."""

    @pytest.fixture
    def sample_file(self, tmp_path):
        p = tmp_path / "architecture_diagram.png"
        p.write_bytes(b"\x89PNG\r\n\x1a\nMock PNG Data")
        return p

    def test_send_file_not_found(self):
        tool = WhatsAppTool()
        res = tool.send_file(file_path="does_not_exist_99.png", contact="Aryan")
        assert res.success is False
        assert "not found" in res.message.lower()

    def test_send_empty_file_rejected(self, tmp_path):
        tool = WhatsAppTool()
        empty_f = tmp_path / "empty.txt"
        empty_f.write_text("")
        res = tool.send_file(file_path=str(empty_f), contact="Aryan")
        assert res.success is False
        assert "empty" in res.message.lower()

    def test_send_file_success_flow(self, sample_file):
        tool = WhatsAppTool()

        with patch.object(tool, "search_contact", return_value=ToolResult(success=True, message="Contact found")), \
             patch("tools.whatsapp_tool.copy_file_to_clipboard", return_value=True), \
             patch("pyautogui.hotkey"), \
             patch("pyautogui.press"), \
             patch("pyperclip.copy"):

            res = tool.send_file(
                file_path=str(sample_file),
                contact="Aryan",
                caption="Here is the architectural overview."
            )
            assert res.success is True
            assert "Successfully shared file" in res.message
            assert res.data["file"] == "architecture_diagram.png"
            assert res.data["contact"] == "Aryan"
            assert res.data["caption"] == "Here is the architectural overview."

    def test_messaging_whatsapp_share_wrapper(self, sample_file):
        with patch("messaging.whatsapp.find_contact", return_value="+919876543210"), \
             patch.object(WhatsAppTool, "send_file") as mock_send:
            mock_send.return_value = ToolResult(
                success=True,
                message="Successfully shared file 'architecture_diagram.png' with Jayesh on WhatsApp."
            )
            msg = share_whatsapp_file("Jayesh", str(sample_file), caption="Check this out")
            assert "Successfully shared file" in msg


class TestWhatsAppFileShareIntentParsing:
    """Test server intent regex parsing for file sharing commands."""

    def test_share_file_with_contact(self):
        intent = parse_whatsapp_intent("share file report.pdf with Aryan on whatsapp")
        assert intent is not None
        assert intent["action"] == "send_file"
        assert intent["file_path"] == "report.pdf"
        assert intent["contact"] == "Aryan"

    def test_send_image_with_caption(self):
        intent = parse_whatsapp_intent("send image diagram.png to Jay on whatsapp saying Check this diagram")
        assert intent is not None
        assert intent["action"] == "send_file"
        assert intent["file_path"] == "diagram.png"
        assert intent["contact"] == "Jay"
        assert "Check this diagram" in intent["caption"]
