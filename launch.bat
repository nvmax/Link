@echo off
TITLE LINK Suite Launcher
echo ========================================
echo 🚀 Starting LINK: Visual Orchestration
echo ========================================

:: Start the Dashboard in a new window
echo [1/2] Launching Dashboard...
start "LINK Dashboard" cmd /k "npm run dashboard"

:: Start the Bot in a new window
echo [2/2] Launching Discord Bot...
start "LINK Bot" cmd /k "npm run bot"

echo.
echo ✅ Both services are launching!
echo.
echo You can close this launcher window. 
echo Dashboard: http://localhost:3000
echo ========================================
