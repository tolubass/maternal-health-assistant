<#
.SYNOPSIS
    Re-run the full ingestion pipeline (PDFs + web scraping).

.DESCRIPTION
    Executes ingestion/run_ingestion.py followed by ingestion/scrape_web.py.
    Run from the project root with your Python environment active.

.PARAMETER WebOnly
    Skip PDF ingestion — only scrape web sources.

.PARAMETER PdfOnly
    Skip web scraping — only run the PDF ingestion pipeline.

.EXAMPLE
    .\scripts\reingest.ps1
    .\scripts\reingest.ps1 -WebOnly
    .\scripts\reingest.ps1 -PdfOnly

.NOTES
    After re-ingestion, commit the updated data/chroma_db/ to git before
    deploying to Render (no persistent disk on the free tier).
#>
param(
    [switch]$WebOnly,
    [switch]$PdfOnly
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot

Write-Host "=== Maternal Health Ingestion ===" -ForegroundColor Cyan
Write-Host "Project root: $Root" -ForegroundColor Gray

if (-not $WebOnly) {
    Write-Host ""
    Write-Host "[Step 1/2] Running PDF ingestion pipeline..." -ForegroundColor Yellow
    python "$Root\ingestion\run_ingestion.py"
    if ($LASTEXITCODE -ne 0) {
        Write-Error "PDF ingestion failed (exit code $LASTEXITCODE). Check logs above."
    }
    Write-Host "PDF ingestion complete." -ForegroundColor Green
}

if (-not $PdfOnly) {
    Write-Host ""
    Write-Host "[Step 2/2] Scraping authoritative web sources..." -ForegroundColor Yellow
    python "$Root\ingestion\scrape_web.py"
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Web scraping failed (exit code $LASTEXITCODE). Check logs above."
    }
    Write-Host "Web scraping complete." -ForegroundColor Green
}

Write-Host ""
Write-Host "=== Ingestion complete ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "NEXT STEP: Commit the updated Chroma DB before deploying to Render:" -ForegroundColor Yellow
Write-Host "  git add data/chroma_db/" -ForegroundColor Gray
Write-Host "  git commit -m 'data: update chroma_db after re-ingestion'" -ForegroundColor Gray
Write-Host "  git push origin main" -ForegroundColor Gray
