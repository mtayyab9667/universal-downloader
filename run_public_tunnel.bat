@echo off
title Cloudflare Quick Public Tunnel
cd /d "%~dp0"

echo ======================================================================
echo   Universal Downloader - Instant Free Public URL (Cloudflare Tunnel)
echo ======================================================================
echo.

if not exist "%~dp0cloudflared.exe" (
    echo Downloading portable Cloudflare tunnel client (one-time download)...
    powershell -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe' -OutFile '%~dp0cloudflared.exe'"
    if errorlevel 1 (
        echo Failed to download cloudflared. Please check your internet connection.
        pause
        exit /b 1
    )
    echo Download complete!
    echo.
)

echo Starting tunnel for http://localhost:8000...
echo Keep this window OPEN to keep the public URL online.
echo.
"%~dp0cloudflared.exe" tunnel --url http://localhost:8000
pause
