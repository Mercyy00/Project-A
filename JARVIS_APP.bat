@echo off
:: ============================================================================
::  PROJECT J.A.R.V.I.S. - STANDALONE NATIVE DESKTOP APPLICATION LAUNCHER
:: ============================================================================
chcp 65001 >nul
setlocal
title Project JARVIS - Desktop Application
cd /d "%~dp0"

if exist ".\venv\Scripts\python.exe" (
    set "PY_EXE=.\venv\Scripts\python.exe"
) else (
    set "PY_EXE=python"
)

"%PY_EXE%" ui\app.py %*

if %errorlevel% neq 0 (
    echo.
    echo [!] Application closed or exited with code %errorlevel%.
)

endlocal
