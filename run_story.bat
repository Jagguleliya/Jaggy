@echo off
echo ========================================================
echo   YouTube Shorts Bot - Daily Movie Saga (Part Release)
echo ========================================================
echo.
"%~dp0venv\Scripts\python.exe" "%~dp0main.py" --mode story_universe %*
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Bot exited with an error code: %ERRORLEVEL%
) else (
    echo.
    echo Episode generated and uploaded successfully!
)
pause
