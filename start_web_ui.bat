@echo off
title PropLead & WhatsApp Hub - Web App
setlocal

cd /d "%~dp0"

echo ====================================================================
echo        PROPLEAD & WHATSAPP HUB - WEB COMMAND CENTER
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

echo Starting Web Server on http://localhost:5000 ...
echo You can share the Network link with anyone on your Wi-Fi/Network.
echo.

:: Automatically open browser after 2 seconds
start "" cmd /c "timeout /t 2 >nul & start http://localhost:5000"

:: Start Flask Web App
"%PYTHON_CMD%" web_app.py

pause
