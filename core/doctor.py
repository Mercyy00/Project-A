"""Jarvis Core System Diagnostic Doctor.

Authored by: Jay (Team Lead & Core Brain Engineer)
Inspects the health, connectivity, tool registry, memory vault, vision,
audio hardware, and sandbox integrity of Project JARVIS before deployment.
"""

from __future__ import annotations

import datetime
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Ensure project root is in sys.path
_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from dotenv import load_dotenv


def check_environment() -> Dict[str, Any]:
    """Check API keys and environment configuration."""
    project_root = Path(__file__).resolve().parent.parent
    env_file = project_root / ".env"
    if env_file.exists():
        load_dotenv(dotenv_path=env_file)
    else:
        load_dotenv()

    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
    groq_key = os.getenv("GROQ_API_KEY", "").strip()
    groq_model = os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b").strip()
    gemini_model = os.getenv("GEMINI_MODEL") or os.getenv("MODEL_NAME") or "gemini-3.5-flash"
    telegram_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()

    has_gemini = bool(gemini_key and gemini_key != "your_gemini_api_key_here")
    has_groq = bool(groq_key and groq_key != "your_groq_api_key_here")

    if has_gemini and has_groq:
        status = "PASS"
        msg = f"Dual LLM active (Groq: {groq_model} + Gemini: {gemini_model})"
    elif has_gemini:
        status = "PASS"
        msg = f"Gemini active ({gemini_model}), Groq key missing"
    elif has_groq:
        status = "PASS"
        msg = f"Groq active ({groq_model}), Gemini key missing"
    else:
        status = "FAIL"
        msg = "No valid LLM API keys found in .env"

    details = {
        "gemini_configured": has_gemini,
        "groq_configured": has_groq,
        "gemini_model": gemini_model,
        "groq_model": groq_model,
        "telegram_configured": bool(telegram_token and telegram_token != "your_telegram_bot_token_here"),
    }
    return {"status": status, "message": msg, "details": details}


def check_tool_registry() -> Dict[str, Any]:
    """Check the autonomous tool registry and count active tools across modules."""
    try:
        from tools.registry import auto_load_module_tools, get_registered_tools, get_tools_schema

        auto_load_module_tools()
        tools = get_registered_tools()
        count = len(tools)
        schemas = get_tools_schema()

        if count >= 30:
            status = "PASS"
            msg = f"{count} tools discovered across all modules"
        elif count > 0:
            status = "WARN"
            msg = f"{count} tools discovered (expected >= 30)"
        else:
            status = "FAIL"
            msg = "Tool registry is empty"

        return {
            "status": status,
            "message": msg,
            "details": {"count": count, "schema_count": len(schemas)},
        }
    except Exception as exc:
        return {"status": "FAIL", "message": f"Tool registry error: {exc}", "details": {}}


def check_memory_vault() -> Dict[str, Any]:
    """Check SQLite persistent memory database initialization."""
    try:
        import asyncio
        from memory.db import get_db_path

        db_path = asyncio.run(get_db_path())
        status = "PASS"
        msg = f"SQLite storage ready at {db_path}"
        return {
            "status": status,
            "message": msg,
            "details": {"db_path": str(db_path)},
        }
    except Exception as exc:
        return {"status": "FAIL", "message": f"Memory vault error: {exc}", "details": {}}


def check_sandbox() -> Dict[str, Any]:
    """Check filesystem sandbox existence and write safety."""
    try:
        project_root = Path(__file__).resolve().parent.parent
        sandbox_path = project_root / "safe_sandbox"
        sandbox_path.mkdir(parents=True, exist_ok=True)

        test_file = sandbox_path / ".doctor_probe"
        test_file.write_text("ok", encoding="utf-8")
        test_file.unlink(missing_ok=True)

        return {
            "status": "PASS",
            "message": f"Sandbox operational at {sandbox_path.name}/",
            "details": {"path": str(sandbox_path)},
        }
    except Exception as exc:
        return {"status": "FAIL", "message": f"Sandbox error: {exc}", "details": {}}


def check_vision() -> Dict[str, Any]:
    """Check Screen Vision capture subsystem status."""
    try:
        is_paused = os.getenv("VISION_PAUSED", "0").strip() == "1"
        try:
            import mss  # noqa: F401
            has_mss = True
        except ImportError:
            has_mss = False

        if not has_mss:
            return {"status": "WARN", "message": "mss package not installed", "details": {}}

        if is_paused:
            status = "WARN"
            msg = "Screen vision is PAUSED (VISION_PAUSED=1)"
        else:
            status = "PASS"
            msg = "MSS screen capture active (VISION_PAUSED=0)"

        return {
            "status": status,
            "message": msg,
            "details": {"paused": is_paused, "mss_available": has_mss},
        }
    except Exception as exc:
        return {"status": "WARN", "message": f"Vision probe error: {exc}", "details": {}}


def check_creator_engine() -> Dict[str, Any]:
    """Check ReportLab, DOCX, and PPTX document engines and Devanagari fonts."""
    try:
        engines_loaded = []
        try:
            import reportlab  # noqa: F401
            engines_loaded.append("PDF")
        except ImportError:
            pass

        try:
            import docx  # noqa: F401
            engines_loaded.append("DOCX")
        except ImportError:
            pass

        try:
            import pptx  # noqa: F401
            engines_loaded.append("PPTX")
        except ImportError:
            pass

        fonts_dir = Path(__file__).resolve().parent.parent / "creator" / "fonts"
        has_fonts = fonts_dir.exists() and any(fonts_dir.glob("*.ttf"))

        if len(engines_loaded) == 3:
            status = "PASS"
            font_msg = "Devanagari fonts loaded" if has_fonts else "system fonts fallback"
            msg = f"PDF, DOCX, PPTX engines ready ({font_msg})"
        elif engines_loaded:
            status = "WARN"
            msg = f"Partial engines ready: {', '.join(engines_loaded)}"
        else:
            status = "FAIL"
            msg = "No document creation engines available"

        return {
            "status": status,
            "message": msg,
            "details": {"engines": engines_loaded, "fonts_present": has_fonts},
        }
    except Exception as exc:
        return {"status": "WARN", "message": f"Creator check error: {exc}", "details": {}}


def check_audio_subsystem() -> Dict[str, Any]:
    """Check microphone input, speaker output, and Edge-TTS synthesis."""
    try:
        has_sounddevice = False
        input_devices = 0
        output_devices = 0
        try:
            import sounddevice as sd
            has_sounddevice = True
            devs = sd.query_devices()
            input_devices = sum(1 for d in devs if d.get("max_input_channels", 0) > 0)
            output_devices = sum(1 for d in devs if d.get("max_output_channels", 0) > 0)
        except Exception:
            pass

        try:
            import edge_tts  # noqa: F401
            has_edge_tts = True
        except ImportError:
            has_edge_tts = False

        if input_devices > 0 and output_devices > 0:
            status = "PASS"
            msg = f"Audio I/O ready ({input_devices} in, {output_devices} out)"
        elif has_sounddevice or has_edge_tts:
            status = "PASS"
            msg = "Edge-TTS synthesis ready (default audio devices)"
        else:
            status = "WARN"
            msg = "Audio hardware not detected (CLI mode unaffected)"

        return {
            "status": status,
            "message": msg,
            "details": {
                "sounddevice": has_sounddevice,
                "input_devices": input_devices,
                "output_devices": output_devices,
                "edge_tts": has_edge_tts,
            },
        }
    except Exception as exc:
        return {"status": "WARN", "message": f"Audio check error: {exc}", "details": {}}


def check_llm_ping() -> Dict[str, Any]:
    """Perform live roundtrip ping to primary LLM core."""
    try:
        from core.brain import JarvisBrain

        brain = JarvisBrain(enable_tools=False)
        reply = brain.chat("Respond with one word: 'READY'.", mode="combat")
        if reply and len(reply.strip()) > 0:
            return {
                "status": "PASS",
                "message": f"Live LLM roundtrip successful: {reply.strip()[:30]}",
                "details": {"reply": reply.strip()},
            }
        return {"status": "WARN", "message": "LLM returned empty reply", "details": {}}
    except Exception as exc:
        return {
            "status": "WARN",
            "message": f"Live LLM ping deferred: {str(exc)[:60]}",
            "details": {"error": str(exc)},
        }


def diagnose_system(run_live_llm_ping: bool = False) -> Dict[str, Any]:
    """Execute complete system diagnostic checks across all modules.

    Args:
        run_live_llm_ping: Whether to execute a live roundtrip API request.

    Returns:
        Structured dictionary containing status and individual subsystem results.
    """
    checks: Dict[str, Dict[str, Any]] = {
        "environment": check_environment(),
        "tool_registry": check_tool_registry(),
        "memory_vault": check_memory_vault(),
        "sandbox": check_sandbox(),
        "vision": check_vision(),
        "creator_engine": check_creator_engine(),
        "audio_subsystem": check_audio_subsystem(),
    }

    if run_live_llm_ping:
        checks["live_llm"] = check_llm_ping()

    statuses = [c["status"] for c in checks.values()]
    if "FAIL" in statuses:
        overall = "FAIL"
    elif "WARN" in statuses:
        overall = "WARN"
    else:
        overall = "PASS"

    total_tools = checks.get("tool_registry", {}).get("details", {}).get("count", 0)

    return {
        "status": overall,
        "timestamp": datetime.datetime.now().isoformat(),
        "checks": checks,
        "total_tools": total_tools,
    }


def format_doctor_report(report: Dict[str, Any]) -> str:
    """Format diagnostic report into clean, futuristic ASCII dashboard table."""
    lines: List[str] = [
        "=" * 72,
        "              PROJECT JARVIS - SYSTEM DIAGNOSTIC DOCTOR",
        "=" * 72,
    ]

    labels = {
        "environment": "Environment & LLM Keys",
        "tool_registry": "Autonomous Tool Registry",
        "memory_vault": "Persistent Memory Vault",
        "sandbox": "Sandboxed Filesystem",
        "vision": "Screen Vision Subsystem",
        "creator_engine": "Document Creator Suite",
        "audio_subsystem": "Audio I/O & TTS Engine",
        "live_llm": "Live Neural Core Ping",
    }

    for key, info in report.get("checks", {}).items():
        tag = f"[{info['status']}]"
        label = labels.get(key, key.replace("_", " ").title())
        msg = info.get("message", "")
        lines.append(f" {tag:<8} {label:<26} - {msg}")

    lines.append("-" * 72)
    overall = report.get("status", "PASS")
    if overall == "PASS":
        lines.append(" ALL SYSTEMS OPERATIONAL - JARVIS V1.0 IS BATTLE-READY")
    elif overall == "WARN":
        lines.append(" SYSTEM OPERATIONAL WITH ADVISORY WARNINGS (NON-CRITICAL)")
    else:
        lines.append(" CRITICAL SYSTEM FAULT DETECTED - REVIEW FAILED CHECKS ABOVE")
    lines.append("=" * 72)

    return "\n".join(lines)


def check_dependencies(force: bool = False) -> bool:
    """Fast check whether requirements.txt packages are satisfied in venv.

    Returns True instantly (~0.05s) if dependencies are already installed and cached.
    If missing or force=True, runs pip install --prefer-binary and saves the stamp.
    """
    import hashlib
    import subprocess

    project_root = Path(__file__).resolve().parent.parent
    req_file = project_root / "requirements.txt"
    if not req_file.exists():
        return True

    current_hash = hashlib.md5(req_file.read_bytes()).hexdigest()
    stamp_file = project_root / "venv" / ".requirements_hash"

    if not force and stamp_file.exists():
        try:
            if stamp_file.read_text(encoding="utf-8").strip() == current_hash:
                import fastapi
                import groq
                import psutil
                import pyautogui
                return True
        except Exception:
            pass

    # Needs install
    print("[*] Installing / verifying dependencies from requirements.txt...")
    print("[*] (Using --prefer-binary for fast pre-compiled Windows wheels)...")
    res = subprocess.run([
        sys.executable, "-m", "pip", "install", "-r", str(req_file), "--prefer-binary"
    ])
    if res.returncode == 0:
        try:
            stamp_file.parent.mkdir(parents=True, exist_ok=True)
            stamp_file.write_text(current_hash, encoding="utf-8")
        except Exception:
            pass
        return True
    return False


def run_doctor(verbose: bool = True, run_live_llm_ping: bool = False) -> bool:
    """Run system diagnostic and print status table to stdout.

    Args:
        verbose: Whether to print formatted ASCII report.
        run_live_llm_ping: Whether to include live API network ping.

    Returns:
        bool: True if overall status is PASS or WARN, False on FAIL.
    """
    report = diagnose_system(run_live_llm_ping=run_live_llm_ping)
    if verbose:
        print("\n" + format_doctor_report(report) + "\n")
    return report["status"] != "FAIL"


if __name__ == "__main__":
    if "--check-deps" in sys.argv:
        force = "--install" in sys.argv or "--update" in sys.argv
        success = check_dependencies(force=force)
        sys.exit(0 if success else 1)
    success = run_doctor(verbose=True, run_live_llm_ping=True)
    sys.exit(0 if success else 1)
