@echo off
echo ========================================================
echo   JARVIS Voice - Live Microphone STT Test (Day 2 & 3)
echo ========================================================
call .\venv\Scripts\activate.bat
python voice\test_stt.py --mic
pause
