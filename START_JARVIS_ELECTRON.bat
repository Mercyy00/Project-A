@echo off
:: ============================================================================
::  PROJECT J.A.R.V.I.S. - ELECTRON DESKTOP APPLICATION LAUNCHER
::  Launches the Frameless Glass Desktop App with Native Backend Automation
:: ============================================================================
chcp 65001 >nul
setlocal
title Project JARVIS - Desktop Application (Electron)
cd /d "%~dp0"

echo ========================================================================
echo       PROJECT J.A.R.V.I.S. - ELECTRON DESKTOP APPLICATION
echo ========================================================================
echo.

:: ---------------------------------------------------------------------------
:: STEP 1: Verify Node.js runtime
:: ---------------------------------------------------------------------------
echo [*] Checking Node.js runtime...
node --version >nul 2>&1
if errorlevel 1 goto :no_node

for /f "tokens=*" %%v in ('node --version') do set "NODE_VER=%%v"
echo [OK] Node.js %NODE_VER% detected.
echo.

:: ---------------------------------------------------------------------------
:: STEP 2: Verify Python Environment
:: ---------------------------------------------------------------------------
echo [*] Checking Python virtual environment...
if exist "venv\Scripts\python.exe" (
    echo [OK] Python virtual environment found: venv\Scripts\python.exe
) else (
    echo [!] venv\Scripts\python.exe not found. Falling back to system Python.
)
echo.

:: ---------------------------------------------------------------------------
:: STEP 3: Verify desktop dependencies (npm install if missing)
:: ---------------------------------------------------------------------------
if not exist "desktop\node_modules\electron" (
    echo [*] Installing Electron dependencies in desktop folder...
    cd /d "%~dp0desktop"
    call npm install --no-audit --no-fund
    if errorlevel 1 goto :npm_install_failed
    cd /d "%~dp0"
    echo [OK] Electron packages installed successfully.
    echo.
)

:: ---------------------------------------------------------------------------
:: STEP 4: Launch Electron Desktop Application
:: ---------------------------------------------------------------------------
echo [*] Launching JARVIS Electron Desktop Window...
echo [*] Global Summon Hotkey: Ctrl+Shift+Space
echo.

cd /d "%~dp0desktop"
call npm start

if errorlevel 1 (
    echo.
    echo [!] Electron app exited with error code %errorlevel%.
)

echo.
echo ========================================================================
echo       JARVIS Desktop session ended.
echo ========================================================================
echo.
pause
exit /b 0

:no_node
echo.
echo [ERROR] Node.js is not installed or not in PATH!
echo Please install Node.js v18 or later from https://nodejs.org/
echo.
pause
exit /b 1

:npm_install_failed
echo.
echo [ERROR] Failed to install Electron dependencies in desktop folder.
echo Please run 'npm install' inside the desktop directory manually.
echo.
pause
exit /b 1
