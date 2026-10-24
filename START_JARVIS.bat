@echo off
:: ============================================================================
::  PROJECT J.A.R.V.I.S. - AUTONOMOUS DESKTOP AI ASSISTANT
::  One-Click Master Launcher & Environment Setup
:: ============================================================================
chcp 65001 >nul
setlocal
title Project JARVIS - Autonomous Desktop AI Assistant
cd /d "%~dp0"

echo ========================================================================
echo        PROJECT J.A.R.V.I.S. - AUTONOMOUS DESKTOP AI ASSISTANT
echo ========================================================================
echo.

:: ---------------------------------------------------------------------------
:: STEP 1: Verify Python 3.11+
:: ---------------------------------------------------------------------------
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

:: ---------------------------------------------------------------------------
:: STEP 2: Synchronize with Git Remote (Pull latest files)
:: ---------------------------------------------------------------------------
echo [*] [2/5] Checking git repository status...
git --version >nul 2>&1
if %errorlevel% equ 0 (
    if exist ".git" (
        echo [*] Checking for repository updates...
        git pull --quiet origin main >nul 2>&1
        if %errorlevel% neq 0 (
            echo [!] Git pull notice or offline state. Continuing with current local codebase...
        ) else (
            echo [OK] Codebase is up to date.
        )
    ) else (
        echo [!] Not a git repository or .git folder not found. Skipping git sync.
    )
) else (
    echo [!] Git not detected in PATH. Skipping git pull.
)
echo.

:: ---------------------------------------------------------------------------
:: STEP 3: Setup & Activate Virtual Environment (venv)
:: ---------------------------------------------------------------------------
echo [*] [3/5] Setting up virtual environment...
if not exist "venv\Scripts\activate.bat" (
    echo [*] Virtual environment not found at .\venv.
    echo [*] Creating fresh Python virtual environment - please wait...
    %PY_CMD% -m venv venv
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to create virtual environment!
        pause
        exit /b 1
    )
    echo [OK] Virtual environment created successfully.
)

call ".\venv\Scripts\activate.bat"
echo [OK] Virtual environment activated: %VIRTUAL_ENV%
echo.

:: ---------------------------------------------------------------------------
:: STEP 4: Ensure .env Configuration Exists
:: ---------------------------------------------------------------------------
echo [*] [4/5] Checking environment secrets configuration...
if not exist ".env" (
    if exist ".env.example" (
        echo [*] Creating .env file from .env.example...
        copy ".env.example" ".env" >nul
        echo [NOTE] Created .env template. You can configure API keys in .env.
    ) else (
        echo [!] Warning: .env and .env.example not found.
    )
) else (
    echo [OK] .env configuration detected.
)
echo.

:: ---------------------------------------------------------------------------
:: STEP 5: Verify and Install Dependencies (Fast Smart Cache)
:: ---------------------------------------------------------------------------
echo [*] [5/5] Checking dependencies...
python core\doctor.py --check-deps %*
if %errorlevel% equ 0 (
    echo [OK] Dependencies verified and ready - fast cache active.
) else (
    echo [!] Dependency verification notice. Proceeding with launch...
)
echo.

:: ---------------------------------------------------------------------------
:: BONUS: Create Desktop Shortcut if not already present
:: ---------------------------------------------------------------------------
set "SHORTCUT_PATH=%USERPROFILE%\Desktop\Project JARVIS.lnk"
if exist "%SHORTCUT_PATH%" goto :after_shortcut

echo [*] Creating desktop shortcut on your Windows Desktop...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%SHORTCUT_PATH%'); $s.TargetPath = '%~dp0START_JARVIS.bat'; $s.WorkingDirectory = '%~dp0'; $s.Description = 'Project JARVIS Autonomous Desktop AI Assistant'; $s.Save()" >nul 2>&1
if exist "%SHORTCUT_PATH%" echo [OK] Desktop shortcut created at "%SHORTCUT_PATH%"

:after_shortcut

:: ---------------------------------------------------------------------------
:: LAUNCH JARVIS APPLICATION WINDOW
:: ---------------------------------------------------------------------------
echo ========================================================================
echo   ALL SYSTEMS GREEN - LAUNCHING J.A.R.V.I.S. DESKTOP APPLICATION
echo ========================================================================
echo.
echo [*] Starting JARVIS in standalone native application window...
echo [*] Dedicated window mode without browser tabs or address bars.
echo.

python main.py --app %*

if %errorlevel% neq 0 (
    echo.
    echo [!] Application exited with code %errorlevel%.
    pause
)

endlocal
