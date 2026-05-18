$ErrorActionPreference = "Stop"

Write-Host "== Malrocut Render Verification ==" -ForegroundColor Cyan

$repoRoot = Split-Path -Parent $PSScriptRoot
$backendDir = Join-Path $repoRoot "backend"
$venvPython = Join-Path $backendDir ".venv\Scripts\python.exe"

if (Test-Path $venvPython) {
    $pythonExe = $venvPython
    Write-Host "Using backend venv: $pythonExe" -ForegroundColor Green
} else {
    $pythonExe = "python"
    Write-Host "No backend .venv found. Using system python." -ForegroundColor Yellow
    Write-Host "권장: backend\.venv를 만들고 의존성을 설치하세요." -ForegroundColor Yellow
}

Push-Location $repoRoot
try {
    & $pythonExe ".\scripts\verify_render.py"
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Render verification passed" -ForegroundColor Green
        exit 0
    } else {
        Write-Host "❌ Render verification failed" -ForegroundColor Red
        exit $LASTEXITCODE
    }
}
catch {
    Write-Host "❌ Render verification failed" -ForegroundColor Red
    Write-Host "원인:" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}
finally {
    Pop-Location
}
