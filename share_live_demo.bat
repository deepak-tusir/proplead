@echo off
title PropLead - Client Live Demo Sharing
setlocal enabledelayedexpansion

cd /d "%~dp0"

echo ====================================================================
echo        PROPLEAD - CLIENT SECURE LIVE DEMO (CODE 100%% PROTECTED)
echo ====================================================================
echo.
echo [1/2] Checking local Web App on http://localhost:5000 ...

netstat -ano | findstr :5000 >nul 2>nul
if %errorlevel% neq 0 (
    echo Starting Web Server in a separate window...
    start "PropLead Server" /min cmd /c "start_web_ui.bat"
    timeout /t 3 >nul
) else (
    echo [OK] Web App is already running on http://localhost:5000
)

echo.
echo [2/2] Launching Secure Worldwide HTTPS Tunnel...
echo.
echo ====================================================================
echo  CLIENT DEMO SAFETY INSTRUCTIONS:
echo  1. Aapka Source Code aur GitHub link 100%% safe hai (Client ko 0%% access).
echo  2. Neeche jo "https://....trycloudflare.com" link aayega, usey copy karke Client ko bhejein.
echo  3. Client apne mobile ya laptop ke browser me poora software test kar sakega.
echo  4. JAISE HI DEMO KHATAM HO: Is window ko band kar dein (Link turant band ho jayega).
echo ====================================================================
echo.

if exist "cloudflared.exe" (
    cloudflared.exe tunnel --url http://localhost:5000
) else (
    echo cloudflared.exe not found, trying npx localtunnel...
    cmd /c "npx --yes localtunnel --port 5000"
)

pause
