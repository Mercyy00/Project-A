"""Tests for the Electron Desktop Application configuration and files."""

import json
from pathlib import Path


def test_electron_package_json():
    """Verify desktop/package.json exists and has correct electron & builder configs."""
    pkg_path = Path("desktop/package.json")
    assert pkg_path.exists(), "desktop/package.json must exist"

    data = json.loads(pkg_path.read_text(encoding="utf-8"))
    assert data["name"] == "jarvis-desktop"
    assert data["main"] == "main.js"
    assert "start" in data["scripts"]
    assert "dist" in data["scripts"]
    assert "electron" in data["devDependencies"]
    assert "electron-builder" in data["devDependencies"]

    build_cfg = data.get("build", {})
    assert build_cfg.get("appId") == "ai.jarvis.desktop"
    assert build_cfg.get("productName") == "JARVIS"
    assert "win" in build_cfg
    assert "mac" in build_cfg


def test_electron_preload_script():
    """Verify desktop/preload.js securely exposes window controls and APIs."""
    preload_path = Path("desktop/preload.js")
    assert preload_path.exists(), "desktop/preload.js must exist"

    content = preload_path.read_text(encoding="utf-8")
    assert "contextBridge.exposeInMainWorld" in content
    assert "electronAPI" in content
    assert "minimizeWindow" in content
    assert "maximizeWindow" in content
    assert "closeWindow" in content
    assert "openExternal" in content


def test_electron_main_script():
    """Verify desktop/main.js implements single instance, acrylic glass, tray, and backend lifecycle."""
    main_path = Path("desktop/main.js")
    assert main_path.exists(), "desktop/main.js must exist"

    content = main_path.read_text(encoding="utf-8")
    assert "app.requestSingleInstanceLock()" in content
    assert "findPythonExecutable" in content
    assert "checkBackendHealth" in content
    assert "spawnPythonBackend" in content
    assert "stopPythonBackend" in content
    assert "titleBarStyle: 'hidden'" in content
    assert "backgroundMaterial" in content
    assert "'acrylic'" in content
    assert "setPermissionRequestHandler" in content
    assert "globalShortcut.register" in content
    assert "new Tray" in content


def test_electron_launch_script():
    """Verify START_JARVIS_ELECTRON.bat exists and launches the Electron desktop app."""
    bat_path = Path("START_JARVIS_ELECTRON.bat")
    assert bat_path.exists(), "START_JARVIS_ELECTRON.bat must exist"

    content = bat_path.read_text(encoding="utf-8")
    assert "node --version" in content
    assert "desktop" in content
    assert "npm start" in content


def test_existing_launchers_remain_intact():
    """Verify existing launcher scripts are not broken."""
    for script_name in ["START_JARVIS.bat", "START_JARVIS_QT.bat", "run.bat"]:
        p = Path(script_name)
        assert p.exists(), f"{script_name} must remain intact"
