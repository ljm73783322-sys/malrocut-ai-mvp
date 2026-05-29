param(
    [int]$Port = 8000
)

$ErrorActionPreference = "Stop"

Write-Host "== Malrocut Backend Starter ==" -ForegroundColor Cyan

$ProjectRoot = "C:\projects\malrocut-ai-mvp"
$BackendDir = Join-Path $ProjectRoot "backend"
$VenvDir = Join-Path $BackendDir ".venv"
$PythonExe = Join-Path $VenvDir "Scripts\python.exe"
$ActivateScript = Join-Path $VenvDir "Scripts\Activate.ps1"

if (-not (Test-Path $BackendDir)) {
    Write-Host "ERROR: Backend folder not found: $BackendDir" -ForegroundColor Red
    exit 1
}

Set-Location $BackendDir

Write-Host "Backend directory: $BackendDir" -ForegroundColor Gray

# Python check
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "ERROR: Python is not installed or not in PATH." -ForegroundColor Red
    Write-Host "Please install Python 3.11+ and try again." -ForegroundColor Yellow
    exit 1
}

# Create virtual environment if missing
if (-not (Test-Path $PythonExe)) {
    Write-Host "Creating backend virtual environment..." -ForegroundColor Yellow
    python -m venv .venv
}

# Activate venv
if (Test-Path $ActivateScript) {
    Write-Host "Activating virtual environment..." -ForegroundColor Green
    . $ActivateScript
} else {
    Write-Host "ERROR: Activate.ps1 not found: $ActivateScript" -ForegroundColor Red
    exit 1
}

# Upgrade pip
Write-Host "Checking pip..." -ForegroundColor Gray
python -m pip install --upgrade pip

# Install dependencies
if (Test-Path "requirements.txt") {
    Write-Host "Installing backend requirements..." -ForegroundColor Yellow
    pip install -r requirements.txt
} elseif (Test-Path "..\requirements.txt") {
    Write-Host "Installing root requirements..." -ForegroundColor Yellow
    pip install -r ..\requirements.txt
} else {
    Write-Host "WARNING: requirements.txt not found. Skipping dependency install." -ForegroundColor Yellow
}

# FFmpeg check
if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
    Write-Host "WARNING: ffmpeg not found in PATH. Rendering may fail." -ForegroundColor Yellow
} else {
    Write-Host "ffmpeg found." -ForegroundColor Green
}

if (-not (Get-Command ffprobe -ErrorAction SilentlyContinue)) {
    Write-Host "WARNING: ffprobe not found in PATH. Verification may fail." -ForegroundColor Yellow
} else {
    Write-Host "ffprobe found." -ForegroundColor Green
}

# Encoding settings
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

Write-Host ""
Write-Host "Starting FastAPI backend..." -ForegroundColor Cyan
Write-Host "URL: http://127.0.0.1:$Port" -ForegroundColor Green
Write-Host "Docs: http://127.0.0.1:$Port/docs" -ForegroundColor Green
Write-Host ""

python -m uvicorn app.main:app --reload --host 127.0.0.1 --port $Port
