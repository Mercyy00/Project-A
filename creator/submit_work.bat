@echo off
title JARVIS - Push Work to GitHub (Vidhita)
cd /d "%~dp0\.."
echo ========================================================
echo   JARVIS - Running Tests and Pushing to GitHub
echo ========================================================
call .\venv\Scripts\activate.bat 2>nul
python -m pytest tests/test_creator.py -v
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Tests failed! Fix errors before pushing to GitHub.
    pause
    exit /b %ERRORLEVEL%
)
echo.
set /p commit_msg="Enter commit summary (or press ENTER for default): "
if "%commit_msg%"=="" set commit_msg=update document creator deliverables
git add creator/ tests/test_creator.py
git commit -m "feat(creator): %commit_msg%"
git push origin feature/vidhita-creator
echo.
echo ========================================================
echo   [SUCCESS] Your work is committed and pushed to GitHub!
echo ========================================================
pause
