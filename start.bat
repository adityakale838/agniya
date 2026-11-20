@echo off
echo ========================================
echo   AGNIYA Web Application
echo   Paillier-2048 encrypted aggregation
echo ========================================
echo.
echo Starting Backend API Server (127.0.0.1:5000)...
start cmd /k "cd /d %~dp0 && .\envb\Scripts\activate && python api\server_optimized.py"
timeout /t 3 /nobreak > nul
echo.
echo Starting Frontend React App...
cd webapp
start http://localhost:3000
npm run dev
