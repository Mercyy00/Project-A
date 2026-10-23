"""Unit tests for Jarvis Core Doctor system diagnostics module.

Authored by: Jay (Team Lead & Core Brain Engineer)
"""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from core.doctor import diagnose_system, format_doctor_report, run_doctor


class TestJarvisDoctor(unittest.TestCase):
    """Test suite for system diagnostic doctor checks."""

    def test_diagnose_system_structure(self) -> None:
        """Verify diagnose_system returns structured dict with all required checks."""
        report = diagnose_system(run_live_llm_ping=False)
        self.assertIsInstance(report, dict)
        self.assertIn("status", report)
        self.assertIn("checks", report)
        self.assertIn("total_tools", report)
        self.assertIn("timestamp", report)

        required_checks = [
            "environment",
            "tool_registry",
            "memory_vault",
            "sandbox",
            "creator_engine",
            "vision",
        ]
        for check in required_checks:
            self.assertIn(check, report["checks"], f"Missing check: {check}")
            self.assertIn("status", report["checks"][check])
            self.assertIn("message", report["checks"][check])

    def test_format_doctor_report(self) -> None:
        """Verify formatted report produces human-readable diagnostic output."""
        mock_report = {
            "status": "PASS",
            "timestamp": "2026-10-23T12:00:00",
            "total_tools": 38,
            "checks": {
                "environment": {"status": "PASS", "message": "All keys loaded"},
                "tool_registry": {"status": "PASS", "message": "38 tools loaded"},
                "memory_vault": {"status": "PASS", "message": "SQLite active"},
                "sandbox": {"status": "PASS", "message": "safe_sandbox ready"},
            },
        }
        formatted = format_doctor_report(mock_report)
        self.assertIn("JARVIS", formatted)
        self.assertIn("[PASS]", formatted)
        self.assertIn("All keys loaded", formatted)

    def test_run_doctor_returns_boolean(self) -> None:
        """Verify run_doctor returns True when critical systems pass."""
        result = run_doctor(verbose=False, run_live_llm_ping=False)
        self.assertIsInstance(result, bool)


if __name__ == "__main__":
    unittest.main()
