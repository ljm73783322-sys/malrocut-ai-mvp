$ErrorActionPreference = "Stop"

try {
    [Console]::InputEncoding = [System.Text.Encoding]::UTF8
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
    $OutputEncoding = [System.Text.Encoding]::UTF8
} catch {
    Write-Host "WARN UTF-8 console setup could not be applied."
}

Write-Host "== Malrocut Frontend Starter ==" -ForegroundColor Cyan

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
$FrontendDir = Join-Path $ProjectRoot "frontend"

if (-not (Test-Path $FrontendDir -PathType Container)) {
    Write-Host "ERROR: Frontend folder not found: $FrontendDir" -ForegroundColor Red
    exit 1
}

if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    Write-Host "ERROR: Node.js is not installed or not in PATH." -ForegroundColor Red
    exit 1
}

if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    Write-Host "ERROR: npm is not installed or not in PATH." -ForegroundColor Red
    exit 1
}

Set-Location $FrontendDir
Write-Host "Frontend directory: $FrontendDir" -ForegroundColor Gray

if (-not (Test-Path "node_modules" -PathType Container)) {
    Write-Host "node_modules not found. Running npm install..." -ForegroundColor Yellow
    npm install
}

Write-Host ""
Write-Host "Starting Next.js frontend..." -ForegroundColor Cyan
Write-Host "Frontend URL: http://localhost:3000" -ForegroundColor Green
Write-Host ""

npm run dev
