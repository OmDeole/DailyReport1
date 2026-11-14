@echo off
title KSPG Daily Report - Django Backend (Waitress)
color 0A

echo ==============================================================================
echo  KSPG Sales & Production Command Center - Backend Service
echo  Starting Django WSGI with Waitress Server for Windows IIS ARR Integration
echo ==============================================================================

cd /d "%~dp0backend"

:: Detect Python Virtual Environment
set VENV_PYTHON=..\.venv\Scripts\python.exe
if not exist "%VENV_PYTHON%" (
    set VENV_PYTHON=.venv\Scripts\python.exe
)
if not exist "%VENV_PYTHON%" (
    set VENV_PYTHON=python
)

echo [1/3] Checking Database Migrations...
"%VENV_PYTHON%" manage.py migrate --noinput
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Migration failed. Check database credentials in backend/.env.
    pause
    exit /b %ERRORLEVEL%
)

echo [2/3] Collecting Static Files...
"%VENV_PYTHON%" manage.py collectstatic --noinput

echo [3/3] Launching Waitress Production Server on http://127.0.0.1:8000 ...
echo  IIS Application Request Routing (ARR) should proxy /api/* to this port.
echo  Keep this terminal window open.
echo ==============================================================================

"%VENV_PYTHON%" -m waitress --listen=127.0.0.1:8000 daily_report_backend.wsgi:application

pause

