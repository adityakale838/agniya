@echo off
echo ========================================
echo   AGNIYA Web Application
echo   OPTIMIZED Backend (ALL Innovations Active)
echo ========================================
echo.
echo Starting Backend API Server (OPTIMIZED)...
start cmd /k "cd /d %~dp0 && .\envb\Scripts\activate && python api\server_optimized.py"
timeout /t 3 /nobreak > nul
echo.
echo Starting Frontend React App...
cd webapp
start http://localhost:3000
npm run dev
