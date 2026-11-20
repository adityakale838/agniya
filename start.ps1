# AGNIYA Quick Start Script (PowerShell)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  AGNIYA Web Application" -ForegroundColor Cyan
Write-Host "  Paillier-2048 encrypted aggregation" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Starting Backend API Server (127.0.0.1:5000)..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PSScriptRoot'; .\envb\Scripts\Activate.ps1; python api\server_optimized.py"
Start-Sleep -Seconds 3

Write-Host ""
Write-Host "Starting Frontend Next.js App..." -ForegroundColor Yellow
Set-Location "$PSScriptRoot\webapp"
Start-Process "http://localhost:3000"
npm run dev
