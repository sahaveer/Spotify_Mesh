@echo off
title Decentralized Media Hub - Dual-Mode (Mesh + Global)
setlocal enabledelayedexpansion

:: Navigate to project directory
cd /d "%~dp0"

echo ============================================================
echo   DECENTRALIZED MEDIA HUB (DUAL-MODE: MESH + GLOBAL)
echo ============================================================
echo.

:: Check for Python
where python >nul 2>nul
if %errorlevel% neq 0 (
    where py >nul 2>nul
    if %errorlevel% neq 0 (
        echo [ERROR] Python is not installed or not found in system PATH.
        echo Please install Python 3.10+ from https://www.python.org/
        echo Make sure to check "Add Python to PATH" during installation.
        echo.
        pause
        exit /b 1
    ) else (
        set "PY_CMD=py"
    )
) else (
    set "PY_CMD=python"
)

:: Verify dependencies
echo [*] Checking dependencies...
%PY_CMD% -c "import fastapi, uvicorn, mutagen, PIL, pydantic, yt_dlp, zeroconf, qrcode, imageio_ffmpeg" >nul 2>nul
if %errorlevel% neq 0 (
    echo [*] Installing required packages from requirements.txt...
    %PY_CMD% -m pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo [WARNING] Some dependencies failed to install. Attempting to start anyway...
    )
)

echo [+] Dependencies ready.
echo.
echo [*] Starting Media Player server...
echo [*] Press Ctrl+C at any time to stop the server.
echo.

:: Automatically launch default browser after 2 seconds
start "" cmd /c "timeout /t 2 /nobreak >nul & start http://localhost:8000"

:: Start Server Launcher
%PY_CMD% run_server.py %*

if %errorlevel% neq 0 (
    echo.
    echo [!] Server stopped with exit code %errorlevel%.
    pause
)
