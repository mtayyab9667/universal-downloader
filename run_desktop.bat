@echo off
title Universal Video & Short Drama Downloader
cd /d "%~dp0"

echo ======================================================================
echo   Starting Universal Video Downloader Desktop App...
echo ======================================================================
echo.

python main.py
if errorlevel 1 (
    echo.
    echo An error occurred running the desktop app.
    pause
)
