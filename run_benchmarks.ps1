# Quick Benchmark Runner
Write-Host ("=" * 80) -ForegroundColor Cyan
Write-Host "  AGNIYA Benchmark Suite" -ForegroundColor Cyan
Write-Host ("=" * 80) -ForegroundColor Cyan
Write-Host ""

# Menu
Write-Host "Select benchmark to run:" -ForegroundColor Yellow
Write-Host "  1. AGNIYA vs Microsoft SEAL (full comparison)" -ForegroundColor White
Write-Host "  2. AGNIYA standalone (quick test)" -ForegroundColor White
Write-Host "  3. Install comparison dependencies (TenSEAL)" -ForegroundColor White
Write-Host "  4. View latest results" -ForegroundColor White
Write-Host ""

$choice = Read-Host "Enter choice (1-4)"

switch ($choice) {
    "1" {
        Write-Host "`nRunning AGNIYA vs Microsoft SEAL benchmark..." -ForegroundColor Green
        python scripts\benchmark_against_seal_openfhe.py
    }
    "2" {
        Write-Host "`nRunning AGNIYA standalone benchmark..." -ForegroundColor Green
        python scripts\benchmark_agniya_standalone.py
    }
    "3" {
        Write-Host "`nInstalling comparison dependencies..." -ForegroundColor Green
        .\install_comparison_deps.ps1
    }
    "4" {
        Write-Host "`nLatest benchmark results:" -ForegroundColor Green
        Write-Host ""
        $latestCsv = Get-ChildItem "data\benchmark_results\*.csv" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
        if ($latestCsv) {
            Write-Host "File: $($latestCsv.Name)" -ForegroundColor Cyan
            Write-Host "Date: $($latestCsv.LastWriteTime)" -ForegroundColor Cyan
            Write-Host ""
            Get-Content $latestCsv.FullName -Head 20
            Write-Host ""
            Write-Host "Full results: $($latestCsv.FullName)" -ForegroundColor Yellow
        } else {
            Write-Host "No benchmark results found." -ForegroundColor Red
            Write-Host "Run a benchmark first (option 1 or 2)." -ForegroundColor Yellow
        }
    }
    default {
        Write-Host "Invalid choice. Please select 1-4." -ForegroundColor Red
    }
}

Write-Host ""
Write-Host ("=" * 80) -ForegroundColor Cyan
Write-Host "For detailed comparison, see: BENCHMARK_RESULTS_SUMMARY.md" -ForegroundColor Cyan
Write-Host "For setup guide, see: SEAL_OPENFHE_COMPARISON.md" -ForegroundColor Cyan
Write-Host ("=" * 80) -ForegroundColor Cyan
