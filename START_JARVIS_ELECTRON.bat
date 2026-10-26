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
:: STEP 1: Verify Node.js and npm
:: ---------------------------------------------------------------------------
echo [*] Checking Node.js runtime...
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Node.js is not installed or not in PATH!
    echo Please install Node.js (v18+) from https://nodejs.org/
    echo.
    pause
    exit /b 1
)

for /f "tokens=*" %%v in ('node --version') do set "NODE_VER=%%v"
echo [OK] Node.js %NODE_VER% detected.
echo.

:: ---------------------------------------------------------------------------
:: STEP 2: Verify desktop dependencies (npm install if missing)
:: ---------------------------------------------------------------------------
if not exist "desktop\node_modules\electron" (
    echo [*] Installing Electron dependencies in desktop\ ...
    cd desktop
    call npm install --no-audit --no-fund
    cd ..
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to install Electron dependencies.
        pause
        exit /b 1
    )
    echo [OK] Electron packages installed successfully.
    echo.
)

:: ---------------------------------------------------------------------------
:: STEP 3: Launch Electron Desktop Application
:: ---------------------------------------------------------------------------
echo [*] Starting JARVIS Electron Desktop Window...
echo [*] Global Summon Hotkey: Ctrl+Shift+Space
echo.

cd desktop
call npm start

if %errorlevel% neq 0 (
    echo.
    echo [!] Electron app exited with code %errorlevel%.
    pause
)

endlocal
