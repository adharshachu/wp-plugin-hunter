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

echo [4/4] Starting Server...
echo Visit http://localhost:8000 in your browser.
python server.py

pause
