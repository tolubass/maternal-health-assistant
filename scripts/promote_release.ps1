<#
.SYNOPSIS
    Tag and optionally push a versioned release.

.DESCRIPTION
    Bumps the version in versions.json, creates a git commit, and tags it.
    Optionally pushes the tag to the remote so Render auto-deploys.

.PARAMETER Version
    Semantic version string, e.g. "1.1.0"

.PARAMETER Push
    If set, pushes the main branch and the new tag to origin.

.EXAMPLE
    .\scripts\promote_release.ps1 -Version "1.1.0"
    .\scripts\promote_release.ps1 -Version "1.1.0" -Push

.NOTES
    Requires git to be configured with push access to origin.
    The RENDER_DEPLOY_HOOK_URL GitHub secret must be set for auto-deploy to trigger.
#>
param(
    [Parameter(Mandatory)]
    [ValidatePattern('^\d+\.\d+\.\d+$')]
    [string]$Version,

    [switch]$Push
)

$ErrorActionPreference = "Stop"
$Root   = Split-Path -Parent $PSScriptRoot
$Tag    = "v$Version"
$VFile  = Join-Path $Root "versions.json"

# Update versions.json
$json = Get-Content $VFile -Raw | ConvertFrom-Json
$json.app = $Version
$json | ConvertTo-Json -Depth 5 | Set-Content $VFile -Encoding utf8NoBOM

Write-Host "Updated versions.json: app = $Version" -ForegroundColor Cyan

# Stage, commit, tag
git -C $Root add "versions.json"
git -C $Root commit -m "chore: release $Tag"
git -C $Root tag -a $Tag -m "Release $Tag"
Write-Host "Created tag: $Tag" -ForegroundColor Green

if ($Push) {
    git -C $Root push origin main
    git -C $Root push origin $Tag
    Write-Host "Pushed main and $Tag to remote. Render deploy will trigger automatically." -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "To publish, run:" -ForegroundColor Yellow
    Write-Host "  git push origin main && git push origin $Tag" -ForegroundColor Gray
}
