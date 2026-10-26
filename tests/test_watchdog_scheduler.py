"""
Unit and Integration Tests for Proactive Scheduler & Hardware Watchdog (Tasks 27-28).
Verifies battery alerts (15%), disk space warnings, meeting alerts (within 10 mins),
APScheduler event bus, and HardwareWatchdogTool execution.
"""

import asyncio
from datetime import datetime, timedelta
import pytest
from unittest.mock import MagicMock, patch

from core.scheduler import JarvisScheduler
from core.hardware_watchdog import HardwareWatchdog
from tools.guardian_tool import HardwareWatchdogTool


class TestJarvisScheduler:
    """Test scheduler lifecycle, alert listeners, and dispatch bus."""

    def test_singleton_accessor(self):
        s1 = JarvisScheduler.get_instance()
        s2 = JarvisScheduler.get_instance()
        assert s1 is s2

    def test_alert_listener_registration_and_dispatch(self):
        scheduler = JarvisScheduler()
        received_alerts = []

        def sample_listener(alert):
            received_alerts.append(alert)

        scheduler.register_alert_listener(sample_listener)
        assert sample_listener in scheduler.listeners

        scheduler.dispatch_alert(
            title="Battery Low (15%)",
            message="Plug in your laptop immediately.",
            level="critical",
        )

        assert len(received_alerts) == 1
        assert received_alerts[0]["title"] == "Battery Low (15%)"
        assert len(scheduler.get_recent_alerts()) >= 1

        scheduler.unregister_alert_listener(sample_listener)
        assert sample_listener not in scheduler.listeners


class TestHardwareWatchdog:
    """Test battery, disk, CPU, and meeting monitoring with debouncing."""

    @pytest.fixture
    def watchdog(self):
        wd = HardwareWatchdog(
            battery_threshold_low=20,
            battery_threshold_critical=15,
            disk_threshold_percent=90.0,
            meeting_window_minutes=10,
            debounce_seconds=100.0,
        )
        return wd

    def test_battery_critical_alert(self, watchdog):
        # Mock psutil.sensors_battery returning 15% and discharging
        mock_battery = MagicMock()
        mock_battery.percent = 15
        mock_battery.power_plugged = False
        mock_battery.secsleft = 1800

        with patch("psutil.sensors_battery", return_value=mock_battery):
            alert = watchdog.check_battery()
            assert alert is not None
            assert alert["level"] == "critical"
            assert "15%" in alert["title"]
            assert "15%" in alert["message"] or "charger" in alert["message"].lower()

    def test_battery_normal_when_plugged_in(self, watchdog):
        mock_battery = MagicMock()
        mock_battery.percent = 15
        mock_battery.power_plugged = True  # Plugged in
        mock_battery.secsleft = -1

        with patch("psutil.sensors_battery", return_value=mock_battery):
            alert = watchdog.check_battery()
            assert alert is None

    def test_disk_space_warning(self, watchdog):
        mock_part = MagicMock()
        mock_part.opts = ""
        mock_part.device = "C:\\"
        mock_part.mountpoint = "C:\\"

        mock_usage = MagicMock()
        mock_usage.percent = 95.0
        mock_usage.free = 4 * 1024 * 1024 * 1024  # 4 GB free

        with patch("psutil.disk_partitions", return_value=[mock_part]), \
             patch("psutil.disk_usage", return_value=mock_usage):
            alerts = watchdog.check_disk()
            assert len(alerts) >= 1
            assert "disk" in alerts[0]["title"].lower() or "space" in alerts[0]["title"].lower()
            assert "95" in alerts[0]["title"] or "4.0" in alerts[0]["message"]

    def test_upcoming_meeting_alert(self, watchdog):
        # Mock upcoming reminder in 7 minutes
        start_time = datetime.now() + timedelta(minutes=7)
        mock_reminders = [
            {
                "id": "rem_1",
                "text": "Sprint Planning Sync",
                "remind_at": start_time.isoformat(),
                "status": "pending"
            }
        ]

        with patch("messaging.reminders.load_reminders", return_value=mock_reminders):
            alerts = watchdog.check_upcoming_meetings()
            assert len(alerts) >= 1
            assert "Meeting in" in alerts[0]["title"]
            assert "Sprint Planning Sync" in alerts[0]["message"]

    def test_debouncing_prevents_spam(self, watchdog):
        mock_battery = MagicMock()
        mock_battery.percent = 14
        mock_battery.power_plugged = False
        mock_battery.secsleft = 1200

        with patch("psutil.sensors_battery", return_value=mock_battery):
            # First check -> generates alert
            alert1 = watchdog.check_battery()
            assert alert1 is not None

            # Immediate second check -> debounced (None)
            alert2 = watchdog.check_battery()
            assert alert2 is None


class TestHardwareWatchdogTool:
    """Test HardwareWatchdogTool BaseTool interface."""

    def test_check_status(self):
        tool = HardwareWatchdogTool()
        result = tool.run(action="check_status")
        assert result.success is True
        assert "cpu" in result.data or "ram" in result.data or "disk" in result.data

    def test_trigger_test_alert_and_recent_alerts(self):
        tool = HardwareWatchdogTool()
        result = tool.run(
            action="trigger_test_alert",
            test_title="Proactive Test Ping",
            test_message="Test alert sent to HUD and Telegram."
        )
        assert result.success is True

        recent = tool.run(action="recent_alerts")
        assert recent.success is True
        assert len(recent.data) >= 1
        assert any(a["title"] == "Proactive Test Ping" for a in recent.data)
