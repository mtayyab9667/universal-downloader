@echo off
title Universal Video & Drama Downloader
cd /d "%~dp0"
python main.py
if errorlevel 1 (
    echo.
    echo An error occurred. Press any key to exit.
    pause >nul
)
