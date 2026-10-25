@echo off
:: ============================================================================
::  PROJECT J.A.R.V.I.S. - NATIVE PYQT6 SCI-FI DESKTOP HUD
::  One-Click Launcher & Automated Setup for Teammate Machines
:: ============================================================================
chcp 65001 >nul
setlocal
title JARVIS Native Sci-Fi Desktop HUD (Mark-LVI)
cd /d "%~dp0"

echo ========================================================================
echo        PROJECT J.A.R.V.I.S. - NATIVE PYQT6 SCI-FI DESKTOP HUD
echo ========================================================================
echo.

:: STEP 1: Verify Python 3.11+
echo [*] [1/5] Checking Python installation...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    py -3 --version >nul 2>&1
    if %errorlevel% neq 0 (
        echo [ERROR] Python is not installed or not added to PATH!
        echo Please install Python 3.11 or 3.12 from https://www.python.org/
        echo Make sure to check "Add python.exe to PATH" during installation.
        echo.
        pause
        exit /b 1
    ) else (
        set "PY_CMD=py -3"
    )
) else (
    set "PY_CMD=python"
)
for /f "tokens=2 delims= " %%v in ('%PY_CMD% --version 2^>^&1') do set "PY_VER=%%v"
echo [OK] Python %PY_VER% detected.
echo.

:: STEP 2: Check for Git Updates
echo [*] [2/5] Checking repository status...
git --version >nul 2>&1
if %errorlevel% equ 0 (
    if exist ".git" (
        echo [*] Pulling latest updates from origin main...
        git pull --quiet origin main >nul 2>&1
        if %errorlevel% neq 0 (
            echo [!] Offline or merge notice. Continuing with local codebase...
        ) else (
            echo [OK] Codebase is up to date.
        )
    )
)
echo.

:: STEP 3: Setup Virtual Environment (venv)
echo [*] [3/5] Checking virtual environment...
set "VENV_DIR=%~dp0venv"
set "VENV_PYTHON=%VENV_DIR%\Scripts\python.exe"

if not exist "%VENV_PYTHON%" (
    echo [*] Virtual environment not found at .\venv. Creating one now...
    %PY_CMD% -m venv "%VENV_DIR%"
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to create virtual environment!
        pause
        exit /b 1
    )
    echo [OK] Virtual environment created successfully.
)
call "%VENV_DIR%\Scripts\activate.bat"
echo [OK] Virtual environment active.
echo.

:: STEP 4: Ensure .env Exists
echo [*] [4/5] Checking .env configuration...
if not exist ".env" (
    if exist ".env.example" (
        copy ".env.example" ".env" >nul
        echo [NOTE] Created .env template. Please add your GEMINI_API_KEY if needed.
    )
) else (
    echo [OK] .env configuration found.
)
echo.

:: STEP 5: Verify Dependencies
echo [*] [5/5] Verifying dependencies (PyQt6, google-genai, sounddevice)...
"%VENV_PYTHON%" -c "import PyQt6, sounddevice, google.genai" >nul 2>&1
if %errorlevel% neq 0 (
    echo [*] Installing / updating required packages from requirements.txt...
    "%VENV_PYTHON%" -m pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to install dependencies. Check your internet connection.
        pause
        exit /b 1
    )
)
echo [OK] All dependencies satisfied.
echo.

echo ========================================================================
echo   ALL SYSTEMS GREEN - LAUNCHING J.A.R.V.I.S. NATIVE DESKTOP HUD
echo   - Full-Duplex Live Voice: Active
echo   - Mic Mute / Unmute: Press F4 key
echo ========================================================================
echo.

"%VENV_PYTHON%" main.py --qt %*

if %errorlevel% neq 0 (
    echo.
    echo [!] Application exited with code %errorlevel%.
    pause
)

endlocal
