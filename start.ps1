# AGNIYA: start the API and the dashboard, wait until both answer, open the dashboard.
#   .\start.ps1            (from the project folder, in PowerShell)
# Each server runs in its own window; close a window to stop that server.

$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot

function Wait-Url($url, $seconds) {
    $deadline = (Get-Date).AddSeconds($seconds)
    while ((Get-Date) -lt $deadline) {
        try { if ((Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 5).StatusCode -eq 200) { return $true } } catch { }
        Start-Sleep -Seconds 2
    }
    return $false
}

function Test-Port($port) {
    return [bool](Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue)
}

Write-Host "AGNIYA: Paillier-2048 encrypted analytics" -ForegroundColor Cyan

if (-not (Test-Path "$root\envb\Scripts\python.exe")) { throw "Python environment missing: create envb first (README, Setup)." }
if (-not (Test-Path "$root\webapp\node_modules")) { throw "Web app dependencies missing: run 'npm ci' in the webapp folder first." }

if (Test-Port 5000) {
    Write-Host "API already running on port 5000." -ForegroundColor Green
} else {
    Write-Host "Starting the API on http://127.0.0.1:5000 ..." -ForegroundColor Yellow
    Start-Process powershell -ArgumentList '-NoExit', '-Command', "Set-Location '$root'; & '.\envb\Scripts\python.exe' api\server_optimized.py"
}
if (-not (Wait-Url 'http://127.0.0.1:5000/api/health' 90)) { throw "The API did not answer within 90 s: check its window for an error." }
Write-Host "API is up." -ForegroundColor Green

if (Test-Port 3000) {
    Write-Host "Dashboard already running on port 3000." -ForegroundColor Green
} else {
    Write-Host "Starting the dashboard on http://localhost:3000 (the first page load compiles, ~10 s) ..." -ForegroundColor Yellow
    Start-Process powershell -ArgumentList '-NoExit', '-Command', "Set-Location '$root\webapp'; npm run dev"
}
if (-not (Wait-Url 'http://localhost:3000/dashboard' 180)) { throw "The dashboard did not answer within 180 s: check its window for an error." }
Write-Host "Dashboard is up." -ForegroundColor Green

Start-Process 'http://localhost:3000/dashboard'
Write-Host ""
Write-Host "Ready. Banking walkthrough: docs\PITCH-DAY.md" -ForegroundColor Cyan
Write-Host "  1. Load data: data\bank_customers.csv (keep the key in this browser)"
Write-Host "  2. Choose protection: set credit_score to Paillier + range, then Encrypt (about 3.5 s)"
Write-Host "  3. Ask questions: click each bank question once before presenting"
