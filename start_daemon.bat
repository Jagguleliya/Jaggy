@echo off
echo ========================================================
echo   Starting YouTube Shorts Background Auto-Poster...
echo ========================================================
cd /d "%~dp0"
start "" "%~dp0venv\Scripts\pythonw.exe" daemon.py
timeout /t 2 /nobreak >nul
echo.
"%~dp0venv\Scripts\python.exe" "%~dp0status.py"
pause
