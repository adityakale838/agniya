# Monitor Patent-Grade Benchmark Progress
# Run this in a separate terminal while the benchmark is running

Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "AGNIYA - Benchmark Progress Monitor" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""

$resultsDir = "g:\agniya\results"

while ($true) {
    Clear-Host
    Write-Host "================================================================" -ForegroundColor Cyan
    Write-Host "AGNIYA - Benchmark Progress Monitor" -ForegroundColor Cyan
    Write-Host "================================================================" -ForegroundColor Cyan
    Write-Host ""
    
    # Check if Python process is running
    $pythonProc = Get-Process python -ErrorAction SilentlyContinue | Where-Object { $_.CPU -gt 0 }
    if ($pythonProc) {
        Write-Host "[✓] Benchmark RUNNING" -ForegroundColor Green
        Write-Host "    Process ID: $($pythonProc.Id)" -ForegroundColor Gray
        Write-Host "    CPU Time: $([math]::Round($pythonProc.CPU, 2))s" -ForegroundColor Gray
        Write-Host ""
    } else {
        Write-Host "[!] No active Python benchmark process found" -ForegroundColor Yellow
        Write-Host ""
    }
    
    # Check files generated
    if (Test-Path $resultsDir) {
        Write-Host "Files Generated:" -ForegroundColor White
        Write-Host "----------------" -ForegroundColor Gray
        
        $files = Get-ChildItem $resultsDir -Recurse -File | Sort-Object LastWriteTime -Descending
        foreach ($file in $files) {
            $relPath = $file.FullName -replace [regex]::Escape($resultsDir + "\"), ""
            $size = if ($file.Length -lt 1KB) { "$($file.Length) B" } 
                    elseif ($file.Length -lt 1MB) { "$([math]::Round($file.Length / 1KB, 1)) KB" }
                    else { "$([math]::Round($file.Length / 1MB, 1)) MB" }
            $ago = (Get-Date) - $file.LastWriteTime
            $time = if ($ago.TotalMinutes -lt 1) { "$([math]::Floor($ago.TotalSeconds))s ago" }
                    else { "$([math]::Floor($ago.TotalMinutes))m ago" }
            
            Write-Host "  $relPath" -ForegroundColor Cyan
            Write-Host "    Size: $size | Updated: $time" -ForegroundColor Gray
        }
        Write-Host ""
        
        # Show latest results if available
        $latestCSV = Get-ChildItem "$resultsDir\csv\*.csv" -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1
        if ($latestCSV) {
            Write-Host "Latest Results Preview:" -ForegroundColor White
            Write-Host "----------------" -ForegroundColor Gray
            $content = Get-Content $latestCSV.FullName | Select-Object -First 10
            foreach ($line in $content) {
                Write-Host "  $line" -ForegroundColor Yellow
            }
            Write-Host ""
        }
    } else {
        Write-Host "[!] Results directory not created yet" -ForegroundColor Yellow
        Write-Host ""
    }
    
    Write-Host "Press Ctrl+C to stop monitoring" -ForegroundColor Gray
    Write-Host "Refreshing every 5 seconds..." -ForegroundColor Gray
    
    Start-Sleep -Seconds 5
}
