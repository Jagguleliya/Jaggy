@echo off
title JAGY — AI Video Slicing & Syndication Desktop Engine
color 0A
cls

echo ======================================================================
echo    JAGY — Autonomous AI Video Slicing & Syndication Engine v2.0
echo ======================================================================
echo.
echo [1/3] Checking Python installation...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo ERROR: Python is not detected on your system.
    echo Please install Python 3.10 or higher from https://python.org and re-run this file.
    echo.
    pause
    exit /b
)

echo [2/3] Preparing virtual environment & dependencies...
if not exist "venv\Scripts\python.exe" (
    echo Creating virtual environment (venv)...
    python -m venv venv
)

echo Installing required libraries...
call venv\Scripts\python.exe -m pip install -q -r requirements.txt

echo.
echo [3/3] Verifying Permissions & Opening JAGY AI Desktop Studio...
echo.

if exist "%~dp0dist\JAGY.exe" (
    "%~dp0dist\JAGY.exe"
) else (
    "%~dp0venv\Scripts\python.exe" "%~dp0launcher_app.py"
)

pause
