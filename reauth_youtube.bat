@echo off
echo ========================================================
echo   YouTube Shorts Bot - Re-Authenticate YouTube Account
echo ========================================================
echo.
echo A browser window will open automatically.
echo Please log in with your YouTube Google Account and click "Allow".
echo.
cd /d "%~dp0"
"%~dp0venv\Scripts\python.exe" "%~dp0setup_oauth.py"
echo.
pause
