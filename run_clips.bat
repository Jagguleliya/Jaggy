@echo off
echo ========================================================
echo   YouTube Shorts Bot - Viral Clips & Dynamic Narration
echo ========================================================
echo.
"%~dp0venv\Scripts\python.exe" "%~dp0main.py" %*
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Bot exited with an error code: %ERRORLEVEL%
) else (
    echo.
    echo Execution completed successfully!
)
pause
