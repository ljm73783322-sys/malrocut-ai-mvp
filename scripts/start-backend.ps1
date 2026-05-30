param(
    [int]$Port = 8000
)

$ErrorActionPreference = "Stop"

try {
    [Console]::InputEncoding = [System.Text.Encoding]::UTF8
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
    $OutputEncoding = [System.Text.Encoding]::UTF8
} catch {
    Write-Host "WARN UTF-8 console setup could not be applied."
}

$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

Write-Host "== Malrocut Backend Starter ==" -ForegroundColor Cyan

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
$BackendDir = Join-Path $ProjectRoot "backend"
$VenvDir = Join-Path $BackendDir ".venv"
$PythonExe = Join-Path $VenvDir "Scripts\python.exe"
$ActivateScript = Join-Path $VenvDir "Scripts\Activate.ps1"

if (-not (Test-Path (Join-Path $ProjectRoot "frontend") -PathType Container)) {
    Write-Host "ERROR: Project root check failed. Frontend folder not found under: $ProjectRoot" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $BackendDir -PathType Container)) {
    Write-Host "ERROR: Backend folder not found: $BackendDir" -ForegroundColor Red
    exit 1
}

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "ERROR: Python is not installed or not in PATH." -ForegroundColor Red
    Write-Host "Please install Python 3.10+ and try again." -ForegroundColor Yellow
    exit 1
}

Set-Location $BackendDir
Write-Host "Backend directory: $BackendDir" -ForegroundColor Gray

if (-not (Test-Path $PythonExe)) {
    Write-Host "Creating backend virtual environment..." -ForegroundColor Yellow
    python -m venv .venv
}

if (Test-Path $ActivateScript) {
    Write-Host "Activating virtual environment..." -ForegroundColor Green
    . $ActivateScript
} else {
    Write-Host "ERROR: Activate.ps1 not found: $ActivateScript" -ForegroundColor Red
    exit 1
}

if (Test-Path "requirements.txt") {
    Write-Host "Installing backend requirements..." -ForegroundColor Yellow
    python -m pip install -r requirements.txt
} else {
    Write-Host "WARNING: backend/requirements.txt not found. Skipping dependency install." -ForegroundColor Yellow
}

if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
    Write-Host "WARNING: ffmpeg not found in PATH. Rendering may fail." -ForegroundColor Yellow
} else {
    Write-Host "ffmpeg found." -ForegroundColor Green
}

if (-not (Get-Command ffprobe -ErrorAction SilentlyContinue)) {
    Write-Host "WARNING: ffprobe not found in PATH. Video inspection may fail." -ForegroundColor Yellow
} else {
    Write-Host "ffprobe found." -ForegroundColor Green
}

Write-Host ""
Write-Host "Starting FastAPI backend..." -ForegroundColor Cyan
Write-Host "Backend URL: http://127.0.0.1:$Port" -ForegroundColor Green
Write-Host "API Docs: http://127.0.0.1:$Port/docs" -ForegroundColor Green
Write-Host "Health: http://127.0.0.1:$Port/api/health" -ForegroundColor Green
Write-Host ""

python -m uvicorn app.main:app --reload --host 127.0.0.1 --port $Port
