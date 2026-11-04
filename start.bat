@echo off
title PropLead & WhatsApp Outreach - Master Command Center
setlocal
cd /d "%~dp0"

:MENU
cls
echo ====================================================================
echo        PROPLEAD & WHATSAPP OUTREACH - UNIFIED COMMAND CENTER
echo ====================================================================
echo.
echo   [1] Start Web Dashboard (Browser GUI - Scraper, CRM & WhatsApp)
echo   [2] Run Property Dealer Lead Scraper (Terminal CLI)
echo   [3] Run WhatsApp Outreach Tool (Terminal CLI)
echo   [4] Open Exports Folder (.xlsx & .csv Leads)
echo   [5] Install / Verify Dependencies (Python & Node.js)
echo   [0] Exit
echo.
echo ====================================================================
set /p "CHOICE=Enter your choice [0-5]: "

if "%CHOICE%"=="1" goto START_WEB
if "%CHOICE%"=="2" goto RUN_SCRAPER
if "%CHOICE%"=="3" goto RUN_WHATSAPP
if "%CHOICE%"=="4" goto OPEN_EXPORTS
if "%CHOICE%"=="5" goto INSTALL_DEPS
if "%CHOICE%"=="0" exit /b 0

echo Invalid choice. Please try again.
timeout /t 2 >nul
goto MENU

:START_WEB
cls
echo Starting Web Dashboard on http://localhost:5000 ...
call start_web_ui.bat
goto MENU

:RUN_SCRAPER
cls
call run_scraper.bat
goto MENU

:RUN_WHATSAPP
cls
call run_whatsapp.bat
goto MENU

:OPEN_EXPORTS
cls
echo Opening exports folder...
if not exist "exports" mkdir "exports"
start "" "exports"
timeout /t 2 >nul
goto MENU

:INSTALL_DEPS
cls
echo ====================================================================
echo               INSTALLING & VERIFYING DEPENDENCIES
echo ====================================================================
echo.
echo [1/3] Checking Python Packages...
pip install -r requirements.txt
echo.
echo [2/3] Checking Playwright Browsers...
playwright install chromium
echo.
echo [3/3] Checking Node.js Packages...
npm install
echo.
echo ====================================================================
echo Dependencies check completed!
echo ====================================================================
pause
goto MENU
