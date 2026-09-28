@echo off
echo ========================================================
echo   Starting ShortsFlow Studio (n8n Automation Engine)
echo ========================================================
echo.
echo Opening Studio Dashboard at http://localhost:8000 ...
start http://localhost:8000
echo.
cd /d "%~dp0"
"%~dp0venv\Scripts\python.exe" -m uvicorn web.app:app --host 127.0.0.1 --port 8000
pause
