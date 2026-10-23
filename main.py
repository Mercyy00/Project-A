"""Project JARVIS - Central Unified Application Entrypoint.

Allows launching any of Jarvis's operational interfaces:
  - Web HUD Interface:       python main.py --ui      (default)
  - Spoken Voice Loop:       python main.py --voice
  - Terminal Chat REPL:      python main.py --cli
  - Telegram Remote Bot:     python main.py --telegram
  - Full Concurrent Stack:   python main.py --all
  - System Health Doctor:    python main.py --check
"""

from __future__ import annotations

import argparse
import os
import sys
import threading
import time
import webbrowser
from pathlib import Path

# Ensure project root is in sys.path
_project_root = Path(__file__).resolve().parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))


def launch_ui(host: str = "127.0.0.1", port: int = 8000, open_browser: bool = True) -> None:
    """Launch the FastAPI Web HUD backend and open the browser interface."""
    import uvicorn

    url = f"http://{host}:{port}"
    print("=" * 60)
    print("     PROJECT JARVIS - SCI-FI WEB HUD DASHBOARD")
    print("=" * 60)
    print(f"[*] Starting server at: {url}")
    print("[*] Press Ctrl+C to stop.\n")

    if open_browser:
        try:
            webbrowser.open(url)
        except Exception:
            pass

    uvicorn.run("ui.server:app", host=host, port=port, reload=False)


def launch_voice(auto_mode: bool = False) -> None:
    """Launch the interactive spoken multilingual voice loop."""
    from main_voice import main as run_voice
    if auto_mode:
        sys.argv.append("--auto")
    run_voice()


def launch_cli() -> None:
    """Launch the interactive terminal chat runner."""
    from main_cli import main as run_cli
    run_cli()


def launch_telegram() -> None:
    """Launch the Telegram bot remote bridge interface."""
    from messaging.telegram_bot import start_bot
    print("=" * 60)
    print("     PROJECT JARVIS - TELEGRAM REMOTE BRIDGE")
    print("=" * 60)
    print("[*] Starting Telegram polling listener...")
    print("[*] Press Ctrl+C to stop.\n")
    start_bot()


def launch_doctor(run_live_ping: bool = False) -> None:
    """Run full pre-flight system diagnostics."""
    from core.doctor import run_doctor
    success = run_doctor(verbose=True, run_live_llm_ping=run_live_ping)
    sys.exit(0 if success else 1)


def launch_all(host: str = "127.0.0.1", port: int = 8000, open_browser: bool = True) -> None:
    """Launch FastAPI Web HUD server and background services concurrently."""
    import uvicorn

    print("=" * 65)
    print("      PROJECT JARVIS - FULL STACK CONCURRENT LAUNCH")
    print("=" * 65)
    print(f"[*] Starting Web HUD backend at: http://{host}:{port}")

    server_thread = threading.Thread(
        target=lambda: uvicorn.run("ui.server:app", host=host, port=port, reload=False, log_level="warning"),
        daemon=True,
    )
    server_thread.start()
    time.sleep(1.0)

    if open_browser:
        try:
            webbrowser.open(f"http://{host}:{port}")
        except Exception:
            pass

    telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if telegram_token and telegram_token != "your_telegram_bot_token_here":
        print("[*] Launching Telegram Bot remote bridge...")
        try:
            from messaging.telegram_bot import start_bot
            start_bot()
        except (KeyboardInterrupt, SystemExit):
            print("\n[*] Shutting down JARVIS services.")
        except Exception as exc:
            print(f"[!] Telegram bot error: {exc}. Web HUD continues running.")
            server_thread.join()
    else:
        print("[*] Telegram token not configured in .env. Web HUD active.")
        print("[*] Press Ctrl+C to terminate services.\n")
        try:
            while server_thread.is_alive():
                time.sleep(0.5)
        except (KeyboardInterrupt, SystemExit):
            print("\n[*] Terminating JARVIS server.")


def main() -> None:
    """Parse command line arguments and launch requested Jarvis interface."""
    parser = argparse.ArgumentParser(
        description="Project JARVIS - Autonomous Desktop AI Assistant",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--ui",
        action="store_true",
        help="Launch the FastAPI Web HUD browser interface (default)",
    )
    group.add_argument(
        "--voice",
        action="store_true",
        help="Launch the interactive multilingual spoken voice loop",
    )
    group.add_argument(
        "--cli",
        action="store_true",
        help="Launch the terminal text chat runner",
    )
    group.add_argument(
        "--telegram",
        action="store_true",
        help="Launch the Telegram remote bot listener",
    )
    group.add_argument(
        "--check",
        "--doctor",
        dest="check",
        action="store_true",
        help="Run pre-flight system health & diagnostics doctor",
    )
    group.add_argument(
        "--all",
        action="store_true",
        help="Concurrently launch FastAPI Web HUD and background services",
    )
    parser.add_argument(
        "--live-ping",
        action="store_true",
        help="Perform live LLM network ping when running --check",
    )
    parser.add_argument(
        "--host",
        type=str,
        default=os.getenv("SERVER_HOST", "127.0.0.1"),
        help="Server host for Web HUD (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("SERVER_PORT", "8000")),
        help="Server port for Web HUD (default: 8000)",
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Do not automatically open browser when starting Web HUD",
    )
    parser.add_argument(
        "--auto",
        action="store_true",
        help="Continuous listening mode for voice interface",
    )

    args = parser.parse_args()

    if args.check:
        launch_doctor(run_live_ping=args.live_ping)
    elif args.voice:
        launch_voice(auto_mode=args.auto)
    elif args.cli:
        launch_cli()
    elif args.telegram:
        launch_telegram()
    elif args.all:
        launch_all(host=args.host, port=args.port, open_browser=not args.no_browser)
    else:
        # Default mode is Web HUD
        launch_ui(host=args.host, port=args.port, open_browser=not args.no_browser)


if __name__ == "__main__":
    main()
