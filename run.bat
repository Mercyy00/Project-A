@echo off
:: ============================================================================
:: Project JARVIS - Unified Windows Application Launcher
:: Usage:
::   run.bat          (Launches Web HUD Interface - default)
::   run.bat --ui     (Launches Web HUD Interface)
::   run.bat --cli    (Launches Terminal Command Center)
::   run.bat --voice  (Launches Spoken Multilingual Voice Loop)
::   run.bat --check  (Runs Pre-flight System Health Diagnostics)
::   run.bat --all    (Concurrently Launches Web HUD and Background Services)
:: ============================================================================

setlocal
cd /d "%~dp0"

if exist ".\venv\Scripts\activate.bat" (
    call ".\venv\Scripts\activate.bat"
) else (
    echo [!] Virtual environment not detected at .\venv. Using system Python...
)

python main.py %*

endlocal
