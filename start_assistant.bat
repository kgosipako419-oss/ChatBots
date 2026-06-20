@echo off
title Ekko Assistant
cd /d "%~dp0"
echo ============================================
echo   Ekko - your voice assistant
echo ============================================
echo Say "Ekko" then your command.
echo (First start takes a minute to warm up.)
echo Close this window or press Ctrl+C to stop.
echo.
py -m assistant.main
echo.
echo Ekko has stopped.
pause
