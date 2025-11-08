# AGNIYA Quick Start Script (PowerShell)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  AGNIYA Web Application" -ForegroundColor Cyan
Write-Host "  Professional Encryption Interface" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Starting Backend API Server (ADVANCED)..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PSScriptRoot'; .\envb\Scripts\Activate.ps1; python api\server_advanced.py"
Start-Sleep -Seconds 3

Write-Host ""
Write-Host "Starting Frontend React App..." -ForegroundColor Yellow
Set-Location "$PSScriptRoot\webapp"
Start-Process "http://localhost:3000"
npm run dev
