# AGNIYA Patent-Grade Benchmark - Complete Reproducibility Script (Windows)
# ===========================================================================
#
# This script runs all experiments end-to-end for Indian patent filing.
#
# Usage:
#   .\run.ps1                      # Run all benchmarks
#   .\run.ps1 -OutputDir results2  # Custom output directory
#
# Requirements:
#   - Python 3.10+
#   - Virtual environment at .\envb\ (or modify $VenvPath)
#   - All dependencies installed (see requirements.txt)

param(
    [string]$OutputDir = "results"
)

$ErrorActionPreference = "Stop"

# Configuration
$VenvPath = ".\envb"
$ScriptPath = "scripts\patent_grade_benchmark.py"

Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "AGNIYA - Patent-Grade Benchmark Suite" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Output directory: $OutputDir"
Write-Host ""

# Check if virtual environment exists
if (-not (Test-Path $VenvPath)) {
    Write-Host "Error: Virtual environment not found at $VenvPath" -ForegroundColor Red
    Write-Host "Please run: python -m venv $VenvPath"
    exit 1
}

# Activate virtual environment
Write-Host "Activating virtual environment..."
$ActivateScript = Join-Path $VenvPath "Scripts\Activate.ps1"
if (Test-Path $ActivateScript) {
    & $ActivateScript
} else {
    Write-Host "Error: Cannot find activation script" -ForegroundColor Red
    exit 1
}

# Verify Python
Write-Host "Checking Python version..."
python --version

# Verify dependencies
Write-Host "Verifying dependencies..."
try {
    python -c "import numpy, pandas; print('✓ numpy, pandas')"
    python -c "import gmpy2; print('✓ gmpy2')"
} catch {
    Write-Host "Warning: Some dependencies may be missing" -ForegroundColor Yellow
}

# Set UTF-8 encoding
$env:PYTHONIOENCODING = "utf-8"

# Run benchmark
Write-Host ""
Write-Host "Starting benchmark suite..." -ForegroundColor Green
Write-Host "This may take 10-30 minutes depending on hardware."
Write-Host ""

python $ScriptPath --output-dir $OutputDir

# Check if results were generated
$SummaryFile = Join-Path $OutputDir "summary.md"
if (Test-Path $SummaryFile) {
    Write-Host ""
    Write-Host "================================================================" -ForegroundColor Green
    Write-Host "SUCCESS!" -ForegroundColor Green
    Write-Host "================================================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Results saved in: $OutputDir\"
    Write-Host ""
    Write-Host "Key files:"
    Write-Host "  - summary.md            # Executive summary"
    Write-Host "  - methods.md            # Methodology"
    Write-Host "  - env/environment.txt   # Environment specs"
    Write-Host "  - csv/*.csv             # Raw data"
    Write-Host ""
    Write-Host "Ready for patent filing!" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "Error: Benchmark completed but summary.md not found" -ForegroundColor Red
    exit 1
}
