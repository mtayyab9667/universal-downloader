@echo off
title Push Project to GitHub
cd /d "%~dp0"

echo ======================================================================
echo   Push Universal Downloader to GitHub
echo ======================================================================
echo.

set /p REPO_URL="Paste your GitHub Repository URL (e.g. https://github.com/user/repo.git): "

if "%REPO_URL%"=="" (
    echo No URL entered. Aborting.
    pause
    exit /b 1
)

echo.
echo Setting branch to main...
git branch -M main

echo Adding remote origin...
git remote remove origin 2>nul
git remote add origin %REPO_URL%

echo Pushing files to GitHub...
git push -u origin main

if errorlevel 1 (
    echo.
    echo Push failed. Please make sure you are logged into GitHub in your terminal or browser.
    pause
    exit /b 1
)

echo.
echo ======================================================================
echo   Success! Your project is now on GitHub!
echo   You can now connect it directly to Render.com.
echo ======================================================================
pause
