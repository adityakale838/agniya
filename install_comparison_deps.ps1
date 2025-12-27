# Install TenSEAL for SEAL vs AGNIYA benchmarks
Write-Host ("=" * 80) -ForegroundColor Cyan
Write-Host "  Installing Comparison Benchmark Dependencies" -ForegroundColor Cyan
Write-Host ("=" * 80) -ForegroundColor Cyan
Write-Host ""

# Check if virtual environment is activated
if ($env:VIRTUAL_ENV) {
    Write-Host "Virtual environment activated: $env:VIRTUAL_ENV" -ForegroundColor Green
} else {
    Write-Host "Activating virtual environment..." -ForegroundColor Yellow
    .\envb\Scripts\Activate.ps1
}

Write-Host ""
Write-Host "Installing TenSEAL (Microsoft SEAL wrapper)..." -ForegroundColor Yellow
pip install tenseal

Write-Host ""
Write-Host "Verifying installation..." -ForegroundColor Green
$testResult = python -c "import tenseal; print('TenSEAL version:', tenseal.__version__)" 2>&1

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host ("=" * 80) -ForegroundColor Green
    Write-Host "Installation Complete!" -ForegroundColor Green
    Write-Host ("=" * 80) -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "  1. Run benchmark: python scripts\benchmark_against_seal_openfhe.py" -ForegroundColor White
    Write-Host "  2. View results: data\benchmark_results\" -ForegroundColor White
    Write-Host "  3. Read guide: SEAL_OPENFHE_COMPARISON.md" -ForegroundColor White
    Write-Host ""
} else {
    Write-Host ""
    Write-Host "Installation failed" -ForegroundColor Red
    Write-Host ""
    Write-Host "Troubleshooting:" -ForegroundColor Yellow
    Write-Host "  1. Ensure Python 3.7-3.11 is installed" -ForegroundColor White
    Write-Host "  2. Install Visual C++ Redistributable:" -ForegroundColor White
    Write-Host "     https://aka.ms/vs/17/release/vc_redist.x64.exe" -ForegroundColor White
    Write-Host "  3. Try: pip install --upgrade pip setuptools wheel" -ForegroundColor White
    Write-Host ""
}

# Note about OpenFHE
Write-Host "Note about OpenFHE:" -ForegroundColor Cyan
Write-Host "   OpenFHE requires building from source (30-60 minutes)" -ForegroundColor White
Write-Host "   The benchmark will run without it (AGNIYA vs SEAL only)" -ForegroundColor White
Write-Host "   See SEAL_OPENFHE_COMPARISON.md for installation details" -ForegroundColor White
Write-Host ""
