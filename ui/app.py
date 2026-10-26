"""Standalone Native Desktop Application for Project JARVIS.

Wraps the JARVIS Web HUD inside an authentic, chromeless native Windows
desktop application window using pywebview (Microsoft Edge WebView2)
or native browser Application Mode (--app flag).
"""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

PORT = int(os.getenv("SERVER_PORT", "8000"))
HOST = os.getenv("SERVER_HOST", "127.0.0.1")
URL = f"http://{HOST}:{PORT}/"
APP_TITLE = "J.A.R.V.I.S. // Autonomous Desktop Assistant"


def is_server_ready(host: str = HOST, port: int = PORT, timeout: float = 0.25) -> bool:
    """Check if the backend server is accepting connections."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception:
        return False


def start_backend_thread(host: str = HOST, port: int = PORT) -> threading.Thread:
    """Launch the FastAPI Uvicorn server in a dedicated background daemon thread."""
    def _run() -> None:
        try:
            import uvicorn
            uvicorn.run("ui.server:app", host=host, port=port, log_level="warning")
        except Exception as exc:
            print(f"[ERROR] Failed to run backend server: {exc}")

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    return t


def launch_native_app_window(url: str = URL) -> None:
    """Launch the dedicated chromeless desktop application window."""
    # 1. Attempt pywebview (true native WebView2 desktop window)
    try:
        import webview
        print(f"[*] Launching {APP_TITLE} via native Edge WebView2...")
        webview.create_window(
            title=APP_TITLE,
            url=url,
            width=1366,
            height=850,
            min_size=(960, 600),
            background_color="#070a0f",
        )
        webview.start(debug=False)
        return
    except Exception as exc:
        print(f"[*] Notice: pywebview window notice ({exc}). Falling back to App Mode...")

    # 2. Fallback to Microsoft Edge / Google Chrome Application Mode
    candidates = [
        os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"),
        os.path.expandvars(r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"),
        os.path.expandvars(r"%LocalAppData%\Microsoft\Edge\Application\msedge.exe"),
        os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
    ]
    for exe in candidates:
        if os.path.isfile(exe):
            try:
                proc = subprocess.Popen([
                    exe,
                    f"--app={url}",
                    "--window-size=1366,850",
                    "--app-id=jarvis-desktop-assistant",
                ])
                proc.wait()
                return
            except Exception:
                pass

    # 3. Generic Windows shell start fallback
    try:
        subprocess.run(f'start msedge --app="{url}" --window-size=1366,850', shell=True)
        return
    except Exception:
        pass

    # 4. Standard default browser fallback
    import webbrowser
    webbrowser.open(url)


def main() -> None:
    """Main desktop application entrypoint."""
    print("=" * 60)
    print("     PROJECT J.A.R.V.I.S. - DESKTOP APPLICATION")
    print("=" * 60)

    if not is_server_ready(HOST, PORT):
        print(f"[*] Starting local JARVIS backend on {URL}...")
        start_backend_thread(HOST, PORT)
        # Wait up to 10 seconds for backend to initialize
        for _ in range(50):
            time.sleep(0.2)
            if is_server_ready(HOST, PORT):
                break

    print(f"[*] Backend server ready on {URL}")
    print("[*] Engaging native desktop application window...")
    launch_native_app_window(URL)


if __name__ == "__main__":
    main()
