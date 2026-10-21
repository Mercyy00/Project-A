"""Project JARVIS - Central Unified Application Entrypoint.

Allows launching any of Jarvis's operational interfaces:
  - Web HUD Interface:       python main.py --ui      (default)
  - Spoken Voice Loop:       python main.py --voice
  - Terminal Chat REPL:      python main.py --cli
"""

from __future__ import annotations

import argparse
import os
import sys
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

    if args.voice:
        launch_voice(auto_mode=args.auto)
    elif args.cli:
        launch_cli()
    else:
        # Default mode is Web HUD
        launch_ui(host=args.host, port=args.port, open_browser=not args.no_browser)


if __name__ == "__main__":
    main()
