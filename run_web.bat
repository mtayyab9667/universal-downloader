@echo off
title Universal Video Downloader - Web Server
cd /d "%~dp0backend"
echo ============================================================
echo   Starting Universal Video Downloader Web Server...
echo   Opening in your browser at: http://localhost:8000
echo ============================================================
start "" http://localhost:8000
python app.py
if errorlevel 1 (
    echo.
    echo An error occurred running the web server. Press any key to exit.
    pause >nul
)
