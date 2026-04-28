@echo off
TITLE LINK Suite Launcher
echo ========================================
echo 🚀 Starting LINK: Visual Orchestration
echo ========================================

:: Check for .env file
if not exist .env (
    echo.
    echo ❌ ERROR: .env file not found!
    echo.
    echo It looks like this is a fresh clone. 
    echo Please copy .env.example to .env and add your DISCORD_TOKEN.
    echo.
    if exist .env.example (
        echo Creating .env from .env.example...
        copy .env.example .env
        echo ✅ Created .env file. Please edit it and add your token!
    )
    echo.
    pause
    exit /b
)


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
