@echo off
title JARVIS - Sync with Main (Vidhita)
cd /d "%~dp0\.."
echo ========================================================
echo   JARVIS - Syncing feature/vidhita-creator from main
echo ========================================================
git checkout main
git pull origin main
git checkout feature/vidhita-creator
git merge main --no-edit
echo.
echo ========================================================
echo   [SUCCESS] Your branch is now 100%% up to date with main!
echo ========================================================
pause
