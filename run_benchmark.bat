@echo off
echo ========================================================
echo   Running Whisper Model Benchmark (Day 5)
echo ========================================================
call .\venv\Scripts\activate.bat
python voice\benchmark_models.py
pause
