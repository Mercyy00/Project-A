@echo off
title JARVIS - Messaging Unit Tests Runner
cd /d "d:\Project A"
echo ========================================================
echo   Running PyTest Suite for JARVIS Messaging (Trupti)
echo ========================================================
echo.
python -m pytest tests\test_messaging.py -v
echo.
pause
