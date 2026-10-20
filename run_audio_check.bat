@echo off
echo ========================================================
echo   JARVIS Voice - Audio Check and Loopback Test (Day 1)
echo ========================================================
call .\venv\Scripts\activate.bat
python voice\audio_check.py
pause
