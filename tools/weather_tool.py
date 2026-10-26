"""
Weather Information Tool for JARVIS.

Ported from Mark LVI's weather_report.py.
Provides zero-dependency weather forecasting via public meteorological endpoints.
"""

from __future__ import annotations

import urllib.request
import urllib.parse
import json
from typing import Any, Dict, Optional

from tools.base import BaseTool, ToolResult


class WeatherReportTool(BaseTool):
    """Retrieves current weather forecasts for any city or region."""
    name: str = "weather_report"
    description: str = "Fetches the current weather, temperature, humidity, and forecast for a specified city or location."

    def get_schema(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "City or location name (e.g. 'London', 'New York', 'Tokyo', 'Mumbai')."
                    }
                },
                "required": ["location"]
            }
        }

    def run(self, location: str, **kwargs) -> ToolResult:
        loc = location.strip()
        if not loc:
            return ToolResult(success=False, message="Location must not be empty.")

        try:
            # Query wttr.in with JSON format
            encoded = urllib.parse.quote_plus(loc)
            url = f"https://wttr.in/{encoded}?format=j1"
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) JARVIS/Mark-LVI"}
            )
            with urllib.request.urlopen(req, timeout=8) as res:
                data = json.loads(res.read().decode("utf-8"))

            curr = data.get("current_condition", [{}])[0]
            temp_c = curr.get("temp_C", "--")
            temp_f = curr.get("temp_F", "--")
            desc = curr.get("weatherDesc", [{}])[0].get("value", "Clear")
            humidity = curr.get("humidity", "--")
            wind_speed = curr.get("windspeedKmph", "--")

            summary = f"Weather for {loc}: {desc}, {temp_c}°C ({temp_f}°F), Humidity: {humidity}%, Wind: {wind_speed} km/h."
            return ToolResult(
                success=True,
                data={
                    "location": loc,
                    "condition": desc,
                    "temp_c": temp_c,
                    "temp_f": temp_f,
                    "humidity": humidity,
                    "wind_speed_kmph": wind_speed
                },
                message=summary
            )
        except Exception as exc:
            return ToolResult(
                success=False,
                message=f"Weather lookup for '{loc}' failed: {str(exc)}"
            )
