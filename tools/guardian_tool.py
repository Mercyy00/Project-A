"""
Hardware Watchdog and System Guardian Tool for Project JARVIS.
Author: Abhijit (System & Automation Engineer)

Conforms to BaseTool specification. Provides:
1. Hardware health check (battery %, disk partitions, CPU, RAM).
2. Proactive alert trigger and watchdog status inspection.
3. Upcoming meeting and schedule watchdog queries.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from tools.base import BaseTool, ToolResult
from core.hardware_watchdog import HardwareWatchdog
from core.scheduler import JarvisScheduler

logger = logging.getLogger(__name__)


class HardwareWatchdogTool(BaseTool):
    """Tool for checking hardware health telemetry and proactive watchdog alerts."""

    name: str = "hardware_watchdog"
    description: str = (
        "Inspects hardware health metrics (battery percentage, disk space, CPU, RAM), "
        "checks for upcoming meetings in the next 10 minutes, and triggers proactive system alerts."
    )

    def get_schema(self) -> Dict[str, Any]:
        """Returns JSON schema definition for LLM tool calling."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["check_status", "check_meetings", "trigger_test_alert", "recent_alerts"],
                        "description": (
                            "'check_status' (run full check on battery, disk, CPU, RAM), "
                            "'check_meetings' (check for meetings in the next 10 minutes), "
                            "'trigger_test_alert' (dispatch a test notification to HUD and Telegram), "
                            "or 'recent_alerts' (list recent dispatched alerts)."
                        )
                    },
                    "test_title": {
                        "type": "string",
                        "description": "Optional title when action is 'trigger_test_alert'."
                    },
                    "test_message": {
                        "type": "string",
                        "description": "Optional body message when action is 'trigger_test_alert'."
                    }
                },
                "required": ["action"]
            }
        }

    def run(
        self,
        action: str = "check_status",
        test_title: Optional[str] = None,
        test_message: Optional[str] = None,
        **kwargs: Any
    ) -> ToolResult:
        """Executes watchdog actions and returns structured ToolResult."""
        act = action.strip().lower()
        watchdog = HardwareWatchdog.get_instance()
        scheduler = JarvisScheduler.get_instance()

        try:
            if act in ("check_status", "status", "health"):
                import psutil
                bat = psutil.sensors_battery()
                bat_info = {
                    "percent": bat.percent if bat else None,
                    "plugged": bat.power_plugged if bat else None,
                } if bat else "No battery detected (Desktop)"

                disk_info = []
                for p in psutil.disk_partitions(all=False):
                    if "cdrom" in p.opts or not p.device:
                        continue
                    try:
                        u = psutil.disk_usage(p.mountpoint)
                        disk_info.append({
                            "drive": p.mountpoint,
                            "percent_used": u.percent,
                            "free_gb": round(u.free / (1024 ** 3), 1),
                            "total_gb": round(u.total / (1024 ** 3), 1),
                        })
                    except (PermissionError, OSError):
                        continue

                cpu_pct = psutil.cpu_percent(interval=None)
                ram = psutil.virtual_memory()

                data = {
                    "battery": bat_info,
                    "disk": disk_info,
                    "cpu_percent": cpu_pct,
                    "ram_percent": ram.percent,
                    "ram_free_gb": round(ram.available / (1024 ** 3), 1),
                }

                # Check if any threshold warnings were found
                triggered_alerts = watchdog.run_all_checks()

                lines = ["System Hardware Health Report:"]
                if isinstance(bat_info, dict) and bat_info.get("percent") is not None:
                    charging_str = "Plugged in" if bat_info["plugged"] else "Discharging"
                    lines.append(f"- Battery: {bat_info['percent']}% ({charging_str})")
                else:
                    lines.append("- Battery: A/C Wall Power (Desktop)")

                for d in disk_info:
                    lines.append(f"- Disk {d['drive']}: {d['percent_used']}% full ({d['free_gb']} GB free of {d['total_gb']} GB)")

                lines.append(f"- CPU Utilization: {cpu_pct}%")
                lines.append(f"- Memory Usage: {ram.percent}% ({round(ram.available / (1024 ** 3), 1)} GB free)")

                if triggered_alerts:
                    lines.append("\nActive Proactive Warnings:")
                    for a in triggered_alerts:
                        lines.append(f"  * [{a['level'].upper()}] {a['title']}: {a['message']}")

                return ToolResult(
                    success=True,
                    data=data,
                    message="\n".join(lines)
                )

            elif act in ("check_meetings", "meetings"):
                meeting_alerts = watchdog.check_upcoming_meetings()
                if meeting_alerts:
                    return ToolResult(
                        success=True,
                        data=meeting_alerts,
                        message=f"Detected {len(meeting_alerts)} meetings starting soon: " + "; ".join(a['title'] for a in meeting_alerts)
                    )
                else:
                    return ToolResult(
                        success=True,
                        data=[],
                        message="No upcoming meetings detected in the next 10 minutes."
                    )

            elif act in ("trigger_test_alert", "test_alert"):
                t = test_title or "System Alert Test"
                m = test_message or "This is a proactive alert test sent to HUD and Telegram."
                alert = scheduler.dispatch_alert(
                    title=t, message=m, level="warning", category="system"
                )
                return ToolResult(
                    success=True,
                    data=alert,
                    message=f"Dispatched proactive alert: '{t}' - {m}"
                )

            elif act in ("recent_alerts", "history"):
                recent = scheduler.get_recent_alerts(limit=10)
                if not recent:
                    return ToolResult(
                        success=True,
                        data=[],
                        message="No proactive alerts dispatched yet."
                    )
                lines = [f"Recent Proactive Alerts ({len(recent)}):"]
                for r in recent:
                    lines.append(f"- [{r['formatted_time']}] [{r['level'].upper()}] {r['title']}: {r['message']}")
                return ToolResult(
                    success=True,
                    data=recent,
                    message="\n".join(lines)
                )

            else:
                return ToolResult(
                    success=False,
                    data=None,
                    message=f"Unknown watchdog action '{action}'. Supported: check_status, check_meetings, trigger_test_alert, recent_alerts."
                )

        except Exception as e:
            logger.exception("HardwareWatchdogTool failed: %s", e)
            return ToolResult(
                success=False,
                data=None,
                message=f"Watchdog execution failed: {e}"
            )
