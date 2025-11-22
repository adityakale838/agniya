# Archive old markdown files (keep README.md and core patent docs), move CSVs to backup, update .gitignore, and commit locally
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$repo = Get-Location
$backupDocs = Join-Path $repo "backup\docs_backup_$timestamp"
$backupData = Join-Path $repo "backup\data_archive_$timestamp"

# Files to KEEP (relative to repo root)
$keep = @(
    'RESEARCH_AND_PATENT_SUMMARY.md',
    'PATENT_BENCHMARK_GUIDE.md',
    'results\summary.md',
    'results\methods.md',
    'docs\REAL_WORLD_DATASETS.md',
    'README.md'
)

# Candidate markdown files found earlier; archive everything except $keep
$all = @(
    'TIER2_FIX_SUMMARY.md',
    'SIMPLIFICATION_COMPLETE.md',
    'VALIDATION_CHECKLIST.md',
    'UPLOAD_FIX.md',
    'PROJECT_STATUS_FINAL.md',
    'PRIOR_ART_ANALYSIS.md',
    'PATENT_QUICK_START.md',
    'PATENT_FILING_PACKAGE.md',
    'PATENT_APPLICATION_TEMPLATE.md',
    'webapp\README.md',
    'IMPLEMENTATION_SUMMARY.md',
    'FUTURE_WORK.md',
    'DEMO_GUIDE.md',
    'CHANGELOG_NOV_10.md',
    'CACHING_ALTERNATIVES.md',
    'CACHE_PERFORMANCE_FIX.md',
    'BENCHMARK_SUMMARY.md',
    'docs\AGNIYA_RESEARCH_SUMMARY.md',
    'docs\ENTROPY_AWARE_EXECUTION.md',
    'docs\COMPLETE_PROJECT_GUIDE.md',
    'docs\ADVANCED_STRUCTURES_SUMMARY.md',
    'docs\ADVANCED_RESEARCH_METHODS.md',
    'docs\FUTURE_ROADMAP.md',
    'docs\PRESENTATION_OPTIONS.md',
    'docs\PROJECT_STATUS_COMPLETE.md',
    'docs\PERFORMANCE_COMPARISON.md',
    'docs\NEW_OPTIMIZATIONS_USAGE.md',
    'docs\NEW_OPTIMIZATIONS_SUMMARY.md',
    'docs\README.md',
    'docs\TIER2_FIX.md',
    'docs\RESEARCH_ROADMAP_SUMMARY.md',
    'results\real_world\REAL_WORLD_SUMMARY.md',
    'data\benchmark_results\patent_comparison.md',
    'data\benchmark_results\speedup_analysis.md'
)

# Compute list to archive (exclude keep and ensure file exists)
$toArchive = @()
foreach ($f in $all) {
    if ($keep -contains $f) { continue }
    $full = Join-Path $repo $f
    if (Test-Path $full) { $toArchive += $f } else { Write-Output "Not found (skipping): $f" }
}

# Create backup dirs
New-Item -ItemType Directory -Force -Path $backupDocs | Out-Null
New-Item -ItemType Directory -Force -Path $backupData | Out-Null

# Archive markdown files (preserve relative paths)
foreach ($f in $toArchive) {
    $src = Join-Path $repo $f
    if (-not (Test-Path $src)) { Write-Output "Missing: $f"; continue }
    $dest = Join-Path $backupDocs $f
    $destDir = Split-Path $dest -Parent
    New-Item -ItemType Directory -Force -Path $destDir | Out-Null
    Copy-Item -Path $src -Destination $dest -Force
    Remove-Item -Path $src -Force
    Write-Output "Archived: $f -> $dest"
}

# Move CSVs from data/real_world to backupData
$csvPattern = Join-Path $repo "data\real_world\*.csv"
$csvs = Get-ChildItem -Path $csvPattern -File -ErrorAction SilentlyContinue
if ($csvs) {
    foreach ($c in $csvs) {
        $dest = Join-Path $backupData $c.Name
        Move-Item -Path $c.FullName -Destination $dest -Force
        Write-Output "Moved CSV: $($c.Name) -> $dest"
    }
} else {
    Write-Output "No CSVs found in data\real_world"
}

# Update .gitignore to ignore data/real_world/*.csv (append if not present)
$gitignore = Join-Path $repo ".gitignore"
$ignoreLine = 'data/real_world/*.csv'
if (Test-Path $gitignore) {
    $content = Get-Content $gitignore -ErrorAction SilentlyContinue
    if ($content -notcontains $ignoreLine) {
        Add-Content -Path $gitignore -Value "`n$ignoreLine"
        Write-Output "Appended to .gitignore: $ignoreLine"
    } else {
        Write-Output ".gitignore already contains: $ignoreLine"
    }
} else {
    Set-Content -Path $gitignore -Value $ignoreLine
    Write-Output "Created .gitignore with: $ignoreLine"
}

# Stage changes and commit locally
Write-Output "Staging changes..."
git add -A

# Commit message
$msg = "chore(docs): archive old markdown files; move large CSVs to backup; keep patent docs + README"

# Commit only if there are staged changes
$staged = git diff --cached --name-only
if ($staged) {
    git commit -m $msg
    Write-Output "Committed changes locally: $msg"
} else {
    Write-Output "No changes staged. Nothing to commit."
}

Write-Output "Archive + move complete. Backup locations:"
Write-Output "  Docs backup: $backupDocs"
Write-Output "  Data backup: $backupData"
