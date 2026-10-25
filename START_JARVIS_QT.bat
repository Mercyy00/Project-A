@echo off
:: ============================================================================
::  PROJECT J.A.R.V.I.S. - NATIVE PYQT6 SCI-FI DESKTOP HUD
:: ============================================================================
chcp 65001 >nul
setlocal
title JARVIS Native Sci-Fi Desktop HUD (Mark-LVI)
cd /d "%~dp0"

echo ========================================================================
echo        PROJECT J.A.R.V.I.S. - NATIVE PYQT6 SCI-FI DESKTOP HUD
echo ========================================================================
echo.

if exist "venv\Scripts\python.exe" (
    set "PYTHON_EXE=venv\Scripts\python.exe"
) else (
    set "PYTHON_EXE=python"
)

echo [*] Launching Native PyQt6 Sci-Fi Desktop HUD...
echo [*] Full-duplex voice active. Press F4 to toggle mic mute.
echo.

"%PYTHON_EXE%" main.py --qt %*

if %errorlevel% neq 0 (
    echo.
    echo [!] Application exited with code %errorlevel%.
    pause
)

endlocal
