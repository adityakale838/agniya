@echo off
rem Same as start.ps1: starts the API and the dashboard, waits until both answer, opens the dashboard.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start.ps1"
pause
