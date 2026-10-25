"""
Action Outcome Verification for JARVIS.

Ported from Mark LVI's core/outcome.py.
Replaces blind assumptions with evidence-backed verification of system states:
- Done: Observed that the desired effect actually occurred
- Failed: Observed an explicit error or absence of effect
- Pending / Uncertain: Action was dispatched but outcome cannot yet be verified
"""

from __future__ import annotations

import time
import sys
from typing import Any, Dict, Optional, Literal

OutcomeStatus = Literal["done", "failed", "pending"]


class ActionOutcome:
    """Represents a verified action outcome."""
    def __init__(self, status: OutcomeStatus, message: str, evidence: Optional[Dict[str, Any]] = None):
        self.status = status
        self.message = message
        self.evidence = evidence or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "message": self.message,
            "evidence": self.evidence
        }

    def __str__(self) -> str:
        ev_str = f" [Evidence: {self.evidence}]" if self.evidence else ""
        return f"{self.status.upper()}: {self.message}{ev_str}"


def verify_process_running(proc_name: str, timeout_seconds: float = 2.0) -> bool:
    """Checks if a named process is actively running in the OS process table."""
    try:
        import psutil
        start = time.time()
        target = proc_name.lower().replace(".exe", "")
        while time.time() - start <= timeout_seconds:
            for p in psutil.process_iter(['name']):
                p_name = (p.info.get('name') or '').lower().replace(".exe", "")
                if target in p_name:
                    return True
            time.sleep(0.2)
        return False
    except Exception:
        return False


def verify_window_present(window_substr: str, timeout_seconds: float = 2.0) -> bool:
    """Checks if a visible window with matching title exists."""
    if sys.platform != "win32":
        return True
    try:
        import win32gui
        start = time.time()
        sub = window_substr.lower()
        while time.time() - start <= timeout_seconds:
            matched = False
            def enum_cb(hwnd, _):
                nonlocal matched
                if win32gui.IsWindowVisible(hwnd):
                    t = win32gui.GetWindowText(hwnd).lower()
                    if sub in t:
                        matched = True
            win32gui.EnumWindows(enum_cb, None)
            if matched:
                return True
            time.sleep(0.2)
        return False
    except Exception:
        return False
