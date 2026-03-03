@echo off
title Rasad OSINT Dashboard
color 0A

echo.
echo  ========================================
echo       Rasad v1.0 - OSINT Dashboard
echo  ========================================
echo.

:: Check Python
echo [1/5] Checking Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo  [ERROR] Python not found! Download from: https://www.python.org/downloads/
    echo  Make sure to check "Add Python to PATH" during install
    pause
    exit /b
)
echo  [OK] Python found
echo.

:: Check Node.js
echo [2/5] Checking Node.js...
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo  [ERROR] Node.js not found! Download from: https://nodejs.org/
    pause
    exit /b
)
echo  [OK] Node.js found
echo.

:: Install Backend
echo [3/5] Installing Backend dependencies...
cd /d "%~dp0backend"
pip install -r requirements.txt --quiet 2>nul
if %errorlevel% neq 0 (
    echo  [ERROR] Failed to install Python packages
    pause
    exit /b
)
echo  [OK] Backend ready
echo.

:: Install Frontend
echo [4/5] Installing Frontend dependencies...
cd /d "%~dp0frontend"
if not exist node_modules (
    call npm install --silent
    if %errorlevel% neq 0 (
        echo  [ERROR] Failed to install Node packages
        pause
        exit /b
    )
)
echo  [OK] Frontend ready
echo.

:: Create data folder
if not exist "%~dp0data" mkdir "%~dp0data"

echo [5/5] Starting Rasad...
echo.
echo  ========================================
echo   Frontend:  http://localhost:3000
echo   API Docs:  http://localhost:8000/docs
echo  ========================================
echo.

:: Start Backend
cd /d "%~dp0backend"
start "RasadBackend" cmd /c "uvicorn app.main:app --reload --port 8000"

:: Wait for backend
echo  Waiting for Backend to start...
timeout /t 5 /nobreak >nul

:: Start Frontend
cd /d "%~dp0frontend"
start "RasadFrontend" cmd /c "npm run dev"

:: Wait for frontend
echo  Waiting for Frontend to start...
timeout /t 5 /nobreak >nul

:: Open browser
start http://localhost:3000

echo.
echo  Rasad is running!
echo  Close this window or press Ctrl+C to stop.
echo.
pause
