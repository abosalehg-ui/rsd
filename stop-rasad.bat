@echo off
title Stop Rasad
color 0C

echo.
echo  Stopping Rasad...
echo.

taskkill /FI "WINDOWTITLE eq RasadBackend*" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq RasadFrontend*" /F >nul 2>&1

echo  [OK] Rasad stopped.
echo.
pause
