import psutil
from tools.base import BaseTool, ToolResult

class GetSystemStatsTool(BaseTool):
    """Tool that retrieves telemetry information from the host machine."""
    name = "get_system_stats"
    description = (
        "Retrieves current laptop telemetry including CPU usage percentage, "
        "RAM usage, and battery status. Takes no arguments."
    )

    def run(self) -> ToolResult:
        try:
            cpu_percent = psutil.cpu_percent(interval=0.2)
            ram = psutil.virtual_memory()
            battery = psutil.sensors_battery()

            battery_info = (
                f"{battery.percent}% ({'Plugged in' if battery.power_plugged else 'On Battery'})"
                if battery else "No battery detected (Desktop or AC power)"
            )

            stats = {
                "cpu_usage_percent": cpu_percent,
                "ram_usage_percent": ram.percent,
                "ram_used_gb": round(ram.used / (1024 ** 3), 2),
                "ram_total_gb": round(ram.total / (1024 ** 3), 2),
                "battery": battery_info
            }
            return ToolResult(
                success=True,
                data=stats,
                message="System statistics retrieved successfully."
            )
        except Exception as e:
            return ToolResult(
                success=False,
                data=None,
                message=f"Failed to fetch system stats: {str(e)}"
            )

    def get_schema(self):
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
