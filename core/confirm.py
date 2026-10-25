"""
Confirmation Safety Gate for JARVIS.

Ported from Mark LVI's core/confirm.py.
Enforces a non-forgeable safety gate for destructive system operations:
- Model cannot forge a confirmation parameter
- Dangerous operations issue a structured confirmation token
- Execution requires explicit user approval
"""

from __future__ import annotations

import secrets
import time
from typing import Any, Callable, Dict, Optional

_pending_confirmations: Dict[str, Dict[str, Any]] = {}
CONFIRMATION_TIMEOUT = 120.0  # seconds before token expires


def requires_confirmation(operation: str, description: str, callback: Callable[..., Any], **kwargs) -> str:
    """Registers a high-risk operation and returns a confirmation prompt with a unique token."""
    token = secrets.token_hex(8).upper()
    _pending_confirmations[token] = {
        "operation": operation,
        "description": description,
        "callback": callback,
        "kwargs": kwargs,
        "created_at": time.time()
    }
    return (
        f"SAFETY GATE: Operation '{operation}' requires explicit confirmation.\n"
        f"Action: {description}\n"
        f"To confirm, reply with 'CONFIRM {token}' within {int(CONFIRMATION_TIMEOUT)} seconds."
    )


def execute_confirmation(token: str) -> Dict[str, Any]:
    """Validates confirmation token and executes the pending operation."""
    cleaned_token = token.strip().upper().replace("CONFIRM", "").strip()
    entry = _pending_confirmations.get(cleaned_token)
    if not entry:
        return {"success": False, "message": "Invalid or expired confirmation token."}

    if time.time() - entry["created_at"] > CONFIRMATION_TIMEOUT:
        _pending_confirmations.pop(cleaned_token, None)
        return {"success": False, "message": "Confirmation token has expired."}

    _pending_confirmations.pop(cleaned_token, None)
    try:
        cb = entry["callback"]
        result = cb(**entry["kwargs"])
        if getattr(result, "success", True) is False:
            return {
                "success": False,
                "message": getattr(result, "message", "The operation failed."),
                "result": result,
            }
        return {"success": True, "message": f"Operation '{entry['operation']}' executed successfully.", "result": result}
    except Exception as exc:
        return {"success": False, "message": f"Operation failed during execution: {str(exc)}"}
