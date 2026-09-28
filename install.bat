@echo off
echo ============================================
echo  YouTube Shorts Bot - Installer
echo ============================================
echo.

:: Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed!
    echo Please install Python 3.10+ from https://python.org
    echo Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)

echo [1/4] Creating virtual environment...
python -m venv venv
if errorlevel 1 (
    echo [ERROR] Failed to create virtual environment.
    pause
    exit /b 1
)

echo [2/4] Activating virtual environment...
call venv\Scripts\activate.bat

echo [3/4] Installing dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies.
    echo Try running: pip install -r requirements.txt manually.
    pause
    exit /b 1
)

echo [4/4] Creating directory structure...
if not exist "data\music\upbeat" mkdir "data\music\upbeat"
if not exist "data\music\mysterious" mkdir "data\music\mysterious"
if not exist "data\music\dramatic" mkdir "data\music\dramatic"
if not exist "data\music\chill" mkdir "data\music\chill"
if not exist "data\music\inspiring" mkdir "data\music\inspiring"
if not exist "data\clip_cache" mkdir "data\clip_cache"
if not exist "output" mkdir "output"
if not exist "user_clips" mkdir "user_clips"
if not exist "templates\fonts" mkdir "templates\fonts"
if not exist "templates\overlays" mkdir "templates\overlays"

:: Initialize data files
if not exist "data\performance_log.json" echo [] > "data\performance_log.json"
if not exist "data\used_topics.json" echo [] > "data\used_topics.json"
if not exist "data\engagement_log.json" echo [] > "data\engagement_log.json"
if not exist "data\style_scores.json" echo {} > "data\style_scores.json"

echo.
echo ============================================
echo  Installation Complete!
echo ============================================
echo.
echo Next steps:
echo   1. Add your API keys to config\config.yaml
echo   2. Run: python setup_oauth.py (for YouTube OAuth)
echo   3. Place your 2 recorded clips in user_clips\
echo   4. Download some royalty-free music to data\music\
echo   5. Test with: python main.py --dry-run
echo.
pause
