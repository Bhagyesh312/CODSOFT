@echo off
title ThinkSprint — Dev Server

echo.
echo  ==========================================
echo   ThinkSprint — Starting Development Server
echo  ==========================================
echo.

:: Check venv exists
if not exist "venv\Scripts\activate.bat" (
    echo  [ERROR] Virtual environment not found.
    echo  Run: python -m venv venv ^&^& venv\Scripts\activate ^&^& pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)

:: Activate virtual environment
call venv\Scripts\activate.bat

:: Check .env exists
if not exist ".env" (
    echo  [WARN] .env file not found. Copying from .env.example...
    copy .env.example .env >nul
)

:: Set Flask env vars
set FLASK_APP=app.py
set FLASK_ENV=development
set FLASK_DEBUG=1

echo  [1/2] Running database migrations...
python -m flask db upgrade
if errorlevel 1 (
    echo  [WARN] Migration step had issues, continuing anyway...
)

echo.
echo  [2/2] Starting Flask server...
echo.
echo  ==========================================
echo   App running at: http://localhost:5000
echo  ==========================================
echo.

:: Open browser after a short delay (1.5s gives Flask time to start)
start "" cmd /c "timeout /t 2 /nobreak >nul && start http://localhost:5000"

:: Start Flask (this blocks — keep window open)
python -m flask run --host=0.0.0.0 --port=5000

echo.
echo  Server stopped.
pause
