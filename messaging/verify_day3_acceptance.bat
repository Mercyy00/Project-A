@echo off
title JARVIS - Day 3 Acceptance Test
cd /d "d:\Project A"
echo ========================================================
echo   Running Day 3 Acceptance Verification
echo   Question: 'What is the date today?'
echo ========================================================
echo.
python messaging\test_bot_brain.py --verify
echo.
pause
