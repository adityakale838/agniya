# AGNIYA Evaluation Suite - Quick Start Script
# Runs benchmarks and generates visualizations

Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host "AGNIYA COMPREHENSIVE EVALUATION SUITE" -ForegroundColor Cyan
Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host ""

# Check if in correct directory
if (-not (Test-Path "evaluation_suite")) {
    Write-Host "ERROR: Must run from AGNIYA root directory" -ForegroundColor Red
    exit 1
}

# Check Python
Write-Host "Checking Python installation..." -ForegroundColor Yellow
$pythonVersion = python --version 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "  $pythonVersion" -ForegroundColor Green
} else {
    Write-Host "  ERROR: Python not found" -ForegroundColor Red
    exit 1
}

# Install dependencies
Write-Host ""
Write-Host "Installing evaluation suite dependencies..." -ForegroundColor Yellow
pip install -r evaluation_suite/requirements_evaluation.txt -q

if ($LASTEXITCODE -ne 0) {
    Write-Host "  WARNING: Some dependencies may have failed to install" -ForegroundColor Yellow
}

Write-Host "  Dependencies installed" -ForegroundColor Green

# Create output directories
Write-Host ""
Write-Host "Creating output directories..." -ForegroundColor Yellow
New-Item -ItemType Directory -Force -Path "evaluation_suite/results/raw_data" | Out-Null
New-Item -ItemType Directory -Force -Path "evaluation_suite/results/graphs" | Out-Null
New-Item -ItemType Directory -Force -Path "evaluation_suite/results/tables" | Out-Null
New-Item -ItemType Directory -Force -Path "evaluation_suite/results/logs" | Out-Null
Write-Host "  Directories created" -ForegroundColor Green

# Show menu
Write-Host ""
Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host "SELECT EVALUATION MODE:" -ForegroundColor Cyan
Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host ""
Write-Host "1. Quick Validation (30 minutes) - 3 repetitions, reduced tests" -ForegroundColor White
Write-Host "2. Full Evaluation (4-6 hours) - 10 repetitions, all tests" -ForegroundColor White
Write-Host "3. Micro-Benchmarks Only (10 minutes)" -ForegroundColor White
Write-Host "4. RNS Validation Only (15 minutes) - Patent Claim 1" -ForegroundColor White
Write-Host "5. Generate Visualizations Only (from existing results)" -ForegroundColor White
Write-Host "6. Exit" -ForegroundColor White
Write-Host ""

$choice = Read-Host "Enter choice (1-6)"

switch ($choice) {
    "1" {
        Write-Host ""
        Write-Host "Running Quick Validation..." -ForegroundColor Cyan
        python evaluation_suite/run_all_benchmarks.py --quick
    }
    "2" {
        Write-Host ""
        Write-Host "Running Full Evaluation..." -ForegroundColor Cyan
        Write-Host "WARNING: This will take 4-6 hours" -ForegroundColor Yellow
        $confirm = Read-Host "Continue? (y/n)"
        if ($confirm -eq "y") {
            python evaluation_suite/run_all_benchmarks.py --full
        }
    }
    "3" {
        Write-Host ""
        Write-Host "Running Micro-Benchmarks..." -ForegroundColor Cyan
        python evaluation_suite/run_all_benchmarks.py --category micro
    }
    "4" {
        Write-Host ""
        Write-Host "Running RNS Validation (Patent Claim 1)..." -ForegroundColor Cyan
        python evaluation_suite/run_all_benchmarks.py --category rns
    }
    "5" {
        Write-Host ""
        Write-Host "Generating Visualizations..." -ForegroundColor Cyan
        
        if (-not (Test-Path "evaluation_suite/results/raw_data/complete_results.json")) {
            Write-Host "ERROR: No results found. Run benchmarks first." -ForegroundColor Red
            exit 1
        }
        
        python evaluation_suite/visualization/generate_all_graphs.py
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host ""
            Write-Host "Graphs saved to: evaluation_suite/results/graphs/" -ForegroundColor Green
            
            # Open graphs directory
            $openDir = Read-Host "Open graphs directory? (y/n)"
            if ($openDir -eq "y") {
                Start-Process "evaluation_suite/results/graphs"
            }
        }
    }
    "6" {
        Write-Host "Exiting..." -ForegroundColor Yellow
        exit 0
    }
    default {
        Write-Host "Invalid choice" -ForegroundColor Red
        exit 1
    }
}

# Check if benchmarks completed
if ($LASTEXITCODE -eq 0 -and $choice -ne "5") {
    Write-Host ""
    Write-Host "=" * 80 -ForegroundColor Green
    Write-Host "BENCHMARKS COMPLETE!" -ForegroundColor Green
    Write-Host "=" * 80 -ForegroundColor Green
    Write-Host ""
    Write-Host "Results saved to:" -ForegroundColor White
    Write-Host "  - Raw data: evaluation_suite/results/raw_data/" -ForegroundColor Cyan
    Write-Host "  - Summary: evaluation_suite/results/summary_report.md" -ForegroundColor Cyan
    Write-Host "  - Logs: evaluation_suite/results/logs/benchmark.log" -ForegroundColor Cyan
    Write-Host ""
    
    # Ask to generate visualizations
    $genViz = Read-Host "Generate visualizations now? (y/n)"
    if ($genViz -eq "y") {
        Write-Host ""
        Write-Host "Generating visualizations..." -ForegroundColor Cyan
        python evaluation_suite/visualization/generate_all_graphs.py
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host ""
            Write-Host "Graphs saved to: evaluation_suite/results/graphs/" -ForegroundColor Green
        }
    }
    
    # Ask to view summary
    $viewSummary = Read-Host "View summary report? (y/n)"
    if ($viewSummary -eq "y") {
        Get-Content "evaluation_suite/results/summary_report.md" | Write-Host
    }
    
} elseif ($LASTEXITCODE -ne 0 -and $choice -ne "5") {
    Write-Host ""
    Write-Host "=" * 80 -ForegroundColor Red
    Write-Host "BENCHMARKS FAILED" -ForegroundColor Red
    Write-Host "=" * 80 -ForegroundColor Red
    Write-Host ""
    Write-Host "Check logs: evaluation_suite/results/logs/benchmark.log" -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "Done!" -ForegroundColor Green
