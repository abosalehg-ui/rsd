@echo off
:: ============================================================
::  Rasad - one-click launcher
::  First run: creates a private Python environment and builds the
::  interface (a few minutes). Later runs start in seconds.
::  Close this window to stop Rasad.
:: ============================================================
chcp 65001 >nul
title Rasad
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
cd /d "%~dp0backend"

if exist ".venv\Scripts\python.exe" goto deps

set "PY="
where python >nul 2>&1 && set "PY=python"
if not defined PY where py >nul 2>&1 && set "PY=py -3"
if not defined PY (
    echo.
    echo  Python 3.10+ is required: https://www.python.org/downloads/
    echo  Tick "Add Python to PATH" during installation, then run Rasad.bat again.
    echo.
    pause
    exit /b 1
)
echo  First run: preparing Rasad...
%PY% -m venv .venv
if errorlevel 1 (
    echo  Could not create the Python environment.
    pause
    exit /b 1
)

:deps
:: Reinstall packages only when requirements.txt changed since the last run
fc /b requirements.txt .venv\requirements.stamp >nul 2>&1
if not errorlevel 1 goto run
echo  Installing packages...
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -q -r requirements.txt
if errorlevel 1 (
    echo  Package installation failed - check the internet connection and try again.
    pause
    exit /b 1
)
copy /y requirements.txt .venv\requirements.stamp >nul

:run
".venv\Scripts\python.exe" run_desktop.py
if errorlevel 1 pause
