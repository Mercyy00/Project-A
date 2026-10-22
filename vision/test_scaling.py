"""Display scaling verification test script for Project Jarvis (Aryan - Day 9).

Validates mouse coordinate accuracy under Windows display scaling (100%, 125%, 150%)
and multi-monitor environments.
Moves the mouse pointer to five calibration anchor points:
1. Screen Centre (50%, 50%)
2. Top-Left Quadrant (25%, 25%)
3. Top-Right Quadrant (75%, 25%)
4. Bottom-Left Quadrant (25%, 75%)
5. Bottom-Right Quadrant (75%, 75%)

Prints a formatted PASS/FAIL summary table.
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from typing import Dict, List, Optional, Tuple

import mss
import pyautogui

from vision.screen import take_screenshot

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def get_display_metrics() -> Dict[str, float]:
    """Retrieve screen dimensions and Windows DPI scaling metrics.

    Returns:
        Dictionary with screen width, height, and estimated DPI scaling ratio.
    """
    dpi_scale = 1.0
    if os.name == "nt":
        try:
            import ctypes
            # Get DPI for primary monitor
            user32 = ctypes.windll.user32
            # 0 = MONITOR_DEFAULTTOPRIMARY
            hdc = user32.GetDC(0)
            gdi32 = ctypes.windll.gdi32
            # LOGPIXELSX = 88
            dpi_x = gdi32.GetDeviceCaps(hdc, 88)
            user32.ReleaseDC(0, hdc)
            dpi_scale = round(dpi_x / 96.0, 2)
        except Exception as exc:
            logger.debug("Failed to read system DPI via GDI: %s", exc)

    screen_w, screen_h = pyautogui.size()
    return {
        "width": float(screen_w),
        "height": float(screen_h),
        "dpi_scale": dpi_scale,
    }


def run_scaling_test(auto_mode: bool = False) -> int:
    """Execute interactive or automated display scaling calibration.

    Args:
        auto_mode: If True, executes smoothly without prompting for user keystrokes.

    Returns:
        Exit code (0 if all points passed, 1 otherwise).
    """
    print("\n" + "=" * 60)
    print(" JARVIS VISION: DISPLAY SCALING VERIFICATION (Day 9)")
    print("=" * 60)

    try:
        metrics = get_display_metrics()
        width = int(metrics["width"])
        height = int(metrics["height"])
        dpi_scale = metrics["dpi_scale"]

        print(f"Detected Resolution : {width} x {height} px")
        print(f"Windows DPI Scale   : {int(dpi_scale * 100)}% ({dpi_scale}x)")
        print("-" * 60)

        # Baseline screenshot check
        print("[1/2] Capturing calibration screenshot...")
        shot_path = take_screenshot()
        print(f"      Saved to: {shot_path}")

        # Calibration test points
        test_points: List[Tuple[str, int, int]] = [
            ("Centre (50%, 50%)", int(width * 0.50), int(height * 0.50)),
            ("Top-Left (25%, 25%)", int(width * 0.25), int(height * 0.25)),
            ("Top-Right (75%, 25%)", int(width * 0.75), int(height * 0.25)),
            ("Bottom-Left (25%, 75%)", int(width * 0.25), int(height * 0.75)),
            ("Bottom-Right (75%, 75%)", int(width * 0.75), int(height * 0.75)),
        ]

        results: List[Tuple[str, int, int, str]] = []

        print("\n[2/2] Testing mouse coordinates across quadrants...")
        for name, target_x, target_y in test_points:
            try:
                pyautogui.moveTo(target_x, target_y, duration=0.4)
                current_x, current_y = pyautogui.position()

                # Verify pointer arrived within 2 pixels of target
                delta_x = abs(current_x - target_x)
                delta_y = abs(current_y - target_y)
                accurate = (delta_x <= 2 and delta_y <= 2)

                if auto_mode:
                    status = "PASS" if accurate else "FAIL"
                    time.sleep(0.15)
                else:
                    prompt = input(f"  Mouse moved to {name} ({target_x}, {target_y}). Confirm? [Y/n]: ").strip().lower()
                    if prompt in ("", "y", "yes") and accurate:
                        status = "PASS"
                    else:
                        status = "FAIL"

                results.append((name, target_x, target_y, status))
            except Exception as pt_err:
                logger.error("Error testing point %s: %s", name, pt_err)
                results.append((name, target_x, target_y, "ERROR"))

        # Print formatted summary table
        print("\n" + "=" * 60)
        print(f"{'Test Point':<26} | {'Target (X, Y)':<18} | {'Status':<8}")
        print("-" * 60)
        all_passed = True
        for name, tx, ty, status in results:
            coords_str = f"({tx}, {ty})"
            print(f"{name:<26} | {coords_str:<18} | {status:<8}")
            if status != "PASS":
                all_passed = False
        print("=" * 60)

        if all_passed:
            print(">> ALL DISPLAY SCALING TESTS PASSED SUCCESSFULLY! <<\n")
            return 0
        else:
            print(">> WARNING: Some coordinates deviated from target positions! <<\n")
            return 1

    except Exception as exc:
        print(f"\nExecution failed with error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test display scaling accuracy for Project Jarvis Vision.")
    parser.add_argument("--auto", action="store_true", help="Run automatically without interactive prompts.")
    args = parser.parse_args()

    sys.exit(run_scaling_test(auto_mode=args.auto))
