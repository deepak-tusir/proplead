@echo off
title Property Dealer Leads Scraper
setlocal

cd /d "%~dp0"

echo ====================================================================
echo             PROPERTY DEALERS & REAL ESTATE LEADS EXTRACTOR
echo ====================================================================
echo.

:: Try to find Python
set "PYTHON_CMD="
where python >nul 2>nul
if %errorlevel% equ 0 (
    set "PYTHON_CMD=python"
) else (
    if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
        set "PYTHON_CMD=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    ) else (
        echo [ERROR] Python not found in PATH or standard location.
        pause
        exit /b 1
    )
)

"%PYTHON_CMD%" main.py

echo.
echo Press any key to exit...
pause >nul
