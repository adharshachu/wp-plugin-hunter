@echo off
setlocal
title WP Plugin Hunter - Setup

echo [1/4] Checking Python environment...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH.
    pause
    exit /b
)

if not exist venv (
    echo [2/4] Creating Virtual Environment...
    python -m venv venv
)

echo [3/4] Installing dependencies...
call venv\Scripts\activate
pip install -r requirements.txt

echo [3.5/4] Checking Frontend...
if not exist "frontend\dist" (
    echo [NOTICE] Frontend build missing. Attempting to build...
    npm --version >nul 2>&1
    if %errorlevel% equ 0 (
        cd frontend
        npm install && npm run build
        cd ..
    ) else (
        echo [WARNING] Node.js/npm not found. Cannot build frontend.
        echo Please ensure Node.js is installed or provide the 'frontend/dist' folder.
    )
)

echo [4/4] Starting Server...
echo Visit http://localhost:8000 in your browser.
python server.py

pause
