$ErrorActionPreference = "Stop"

try {
    [Console]::InputEncoding = [System.Text.Encoding]::UTF8
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
    $OutputEncoding = [System.Text.Encoding]::UTF8
} catch {
    Write-Host "WARN UTF-8 console setup could not be applied."
}

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$CheckScript = Join-Path $ScriptDir "check-env.ps1"
$BackendScript = Join-Path $ScriptDir "start-backend.ps1"
$FrontendScript = Join-Path $ScriptDir "start-frontend.ps1"

Write-Host "Malrocut is starting..." -ForegroundColor Cyan

& $CheckScript
if ($LASTEXITCODE -ne 0) {
    Write-Host "Malrocut could not start because critical environment checks failed." -ForegroundColor Red
    Write-Host "Fix the FAIL items above, then run .\scripts\start-malrocut.ps1 again." -ForegroundColor Yellow
    exit 1
}

Start-Process powershell.exe -ArgumentList @("-NoExit", "-ExecutionPolicy", "Bypass", "-File", $BackendScript)
Start-Process powershell.exe -ArgumentList @("-NoExit", "-ExecutionPolicy", "Bypass", "-File", $FrontendScript)

Start-Sleep -Seconds 6
Start-Process "http://localhost:3000"

Write-Host "Malrocut is starting..." -ForegroundColor Green
Write-Host "If the browser does not open, visit http://localhost:3000" -ForegroundColor Green
Write-Host "Backend docs: http://127.0.0.1:8000/docs" -ForegroundColor Green
