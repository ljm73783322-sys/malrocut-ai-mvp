$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$jobsDir = Join-Path $repoRoot "backend\storage\jobs"

if (-not (Test-Path $jobsDir)) {
    Write-Host "BUG: jobs directory not found: $jobsDir" -ForegroundColor Red
    exit 1
}

$latestJobDir = Get-ChildItem -Path $jobsDir -Directory |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1

if (-not $latestJobDir) {
    Write-Host "BUG: no job directories found in $jobsDir" -ForegroundColor Red
    exit 1
}

Write-Host "Latest job folder: $($latestJobDir.FullName)" -ForegroundColor Cyan
Write-Host ""
Write-Host "== File list ==" -ForegroundColor Cyan
Get-ChildItem -Path $latestJobDir.FullName | Format-Table Name, Length, LastWriteTime -AutoSize

$jobJsonPath = Join-Path $latestJobDir.FullName "job.json"
$inputPath = Join-Path $latestJobDir.FullName "input.mp4"
$outputPath = Join-Path $latestJobDir.FullName "edited_video.mp4"
$subtitlePath = Join-Path $latestJobDir.FullName "subtitle.srt"
$editCmdPath = Join-Path $latestJobDir.FullName "edit_command.json"

$jobStatus = $null
$jobError = $null
$hashEqual = $null
$apiWarn = $false

Write-Host "`n== job.json (UTF-8) ==" -ForegroundColor Cyan
if (Test-Path $jobJsonPath) {
    $jobText = Get-Content -Path $jobJsonPath -Raw -Encoding UTF8
    Write-Host $jobText
    try {
        $jobObj = $jobText | ConvertFrom-Json
        $jobStatus = $jobObj.status
        $jobError = $jobObj.error
    } catch {
        Write-Host "WARN: job.json JSON parse failed: $($_.Exception.Message)" -ForegroundColor Yellow
    }
} else {
    Write-Host "BUG: job.json missing" -ForegroundColor Red
}

Write-Host "`n== Hash compare ==" -ForegroundColor Cyan
if ((Test-Path $inputPath) -and (Test-Path $outputPath)) {
    $inHash = (Get-FileHash -Path $inputPath -Algorithm SHA256).Hash
    $outHash = (Get-FileHash -Path $outputPath -Algorithm SHA256).Hash
    $hashEqual = ($inHash -eq $outHash)
    Write-Host "input.mp4  SHA256: $inHash"
    Write-Host "edited.mp4 SHA256: $outHash"
    Write-Host "same_hash = $hashEqual"
} else {
    Write-Host "WARN: input.mp4 or edited_video.mp4 is missing." -ForegroundColor Yellow
}

Write-Host "`n== subtitle.srt (UTF-8) ==" -ForegroundColor Cyan
if (Test-Path $subtitlePath) {
    Get-Content -Path $subtitlePath -Raw -Encoding UTF8 | Write-Host
} else {
    Write-Host "WARN: subtitle.srt missing" -ForegroundColor Yellow
}

Write-Host "`n== edit_command.json (UTF-8) ==" -ForegroundColor Cyan
if (Test-Path $editCmdPath) {
    Get-Content -Path $editCmdPath -Raw -Encoding UTF8 | Write-Host
} else {
    Write-Host "WARN: edit_command.json missing" -ForegroundColor Yellow
}

Write-Host "`n== /status API ==" -ForegroundColor Cyan
if ($jobObj -and $jobObj.job_id) {
    $statusUrl = "http://127.0.0.1:8000/api/jobs/$($jobObj.job_id)/status"
    try {
        $apiStatus = Invoke-RestMethod -Method Get -Uri $statusUrl -TimeoutSec 3
        $apiStatus | ConvertTo-Json -Depth 5 | Write-Host
    } catch {
        $apiWarn = $true
        Write-Host "WARN: API status 조회 불가 ($statusUrl)" -ForegroundColor Yellow
    }
} else {
    $apiWarn = $true
    Write-Host "WARN: job_id unavailable; API status check skipped." -ForegroundColor Yellow
}

Write-Host "`n== Final Verdict ==" -ForegroundColor Cyan
if (-not (Test-Path $jobJsonPath)) {
    Write-Host "BUG: job.json missing" -ForegroundColor Red
    exit 2
}
if ($jobStatus -eq "completed" -and $hashEqual -eq $false) {
    Write-Host "PASS: completed + hash differs + job.json present" -ForegroundColor Green
    if ($apiWarn) { Write-Host "WARN: API status 조회 불가" -ForegroundColor Yellow }
    exit 0
}
if ($jobStatus -eq "failed" -and $jobError) {
    Write-Host "FAIL: failed + error present" -ForegroundColor Red
    if ($apiWarn) { Write-Host "WARN: API status 조회 불가" -ForegroundColor Yellow }
    exit 1
}
if ($jobStatus -eq "completed" -and $hashEqual -eq $true) {
    Write-Host "BUG: completed but input/output hashes are equal" -ForegroundColor Red
    exit 3
}

Write-Host "WARN: API status unavailable or verdict conditions not met" -ForegroundColor Yellow
exit 4
