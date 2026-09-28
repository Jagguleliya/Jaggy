@echo off
echo ========================================================
echo   Stopping YouTube Shorts Background Auto-Poster...
echo ========================================================
cd /d "%~dp0"
"%~dp0venv\Scripts\python.exe" "%~dp0stop_daemon.py"
echo.
pause
