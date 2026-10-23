@echo off
title JARVIS - Creator Test Runner
cd /d "%~dp0\.."
echo ========================================================
echo   JARVIS - Document Creator Test Suite (Vidhita)
echo ========================================================
call .\venv\Scripts\activate.bat 2>nul
python -m pytest tests/test_creator.py -v
echo.
pause
