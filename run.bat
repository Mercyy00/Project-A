@echo off
TITLE J.A.R.V.I.S. Desktop Assistant Launcher
COLOR 0B
echo ========================================================
echo        J.A.R.V.I.S. MULTI-USER DESKTOP AI CORE
echo ========================================================
echo.
echo [1/3] Navigating to Project Root Directory...
cd /d "%~dp0"

echo [2/3] Checking Python Virtual Environment...
if exist "venv\Scripts\python.exe" (
    set "PYTHON_EXE=venv\Scripts\python.exe"
) else (
    set "PYTHON_EXE=python"
)

echo [3/3] Starting Jarvis Backend Server on http://0.0.0.0:8000 ...
start "JARVIS SERVER CORE" "%PYTHON_EXE%" -m uvicorn ui.server:app --port 8000 --host 0.0.0.0

echo.
echo Waiting for server initialization...
timeout /t 2 /nobreak >nul

echo Opening Jarvis Futuristic Web HUD in default browser...
start http://127.0.0.1:8000

echo.
echo ========================================================
echo  JARVIS is ONLINE and operational!
echo  Access Web HUD at: http://127.0.0.1:8000
echo  Press CTRL+C or close this window to stop the server.
echo ========================================================
echo.
pause
