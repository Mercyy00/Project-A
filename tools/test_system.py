"""
Project Jarvis - Day 1: System Telemetry Probe & Non-blocking App Launch
Author: Abhijit (System & Automation Engineer)
"""

import json
import subprocess
import sys
import psutil


def get_system_telemetry() -> dict:
    """Extracts CPU %, RAM usage in GB, and Battery status."""
    # 1. CPU Percentage (interval=0.2s)
    cpu_percent = psutil.cpu_percent(interval=0.2)

    # 2. RAM stats in GB
    vm = psutil.virtual_memory()
    ram_total_gb = round(vm.total / (1024 ** 3), 2)
    ram_used_gb = round(vm.used / (1024 ** 3), 2)
    ram_percent = vm.percent

    # 3. Battery status (handles Desktop PC where battery might be None)
    battery = psutil.sensors_battery()
    if battery is not None:
        battery_data = {
            "percent": battery.percent,
            "power_plugged": battery.power_plugged,
        }
    else:
        battery_data = {
            "percent": None,
            "power_plugged": True,  # Desktop PC / No battery
            "note": "No battery sensor detected (Desktop PC)",
        }

    return {
        "cpu": {
            "usage_percent": cpu_percent
        },
        "ram": {
            "used_gb": ram_used_gb,
            "total_gb": ram_total_gb,
            "usage_percent": ram_percent
        },
        "battery": battery_data
    }


def launch_notepad_non_blocking() -> subprocess.Popen:
    """Launches notepad.exe using subprocess.Popen so script does not block."""
    process = subprocess.Popen(["notepad.exe"])
    return process


def main():
    try:
        # Launch notepad non-blocking
        launch_notepad_non_blocking()

        # Extract system telemetry
        telemetry = get_system_telemetry()

        # Print structured JSON output
        print(json.dumps(telemetry, indent=4))

    except Exception as e:
        error_result = {"status": "error", "message": str(e)}
        print(json.dumps(error_result, indent=4), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()