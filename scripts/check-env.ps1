$ErrorActionPreference = "Continue"

try {
    [Console]::InputEncoding = [System.Text.Encoding]::UTF8
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
    $OutputEncoding = [System.Text.Encoding]::UTF8
} catch {
    Write-Host "WARN UTF-8 console setup could not be applied."
}

$CriticalFailures = 0
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir

function Write-Check {
    param(
        [string]$Level,
        [string]$Message
    )

    $Color = "White"
    if ($Level -eq "PASS") { $Color = "Green" }
    elseif ($Level -eq "WARN") { $Color = "Yellow" }
    elseif ($Level -eq "FAIL") { $Color = "Red" }

    Write-Host ("{0} {1}" -f $Level, $Message) -ForegroundColor $Color
}

function Add-Fail {
    param([string]$Message)
    $script:CriticalFailures += 1
    Write-Check "FAIL" $Message
}

function Test-PortAvailable {
    param([int]$Port)

    try {
        $listener = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
        return ($null -eq $listener)
    } catch {
        try {
            $client = New-Object System.Net.Sockets.TcpClient
            $async = $client.BeginConnect("127.0.0.1", $Port, $null, $null)
            $connected = $async.AsyncWaitHandle.WaitOne(300, $false)
            if ($connected) {
                $client.EndConnect($async)
                $client.Close()
                return $false
            }
            $client.Close()
            return $true
        } catch {
            return $true
        }
    }
}

Write-Host "== Malrocut Windows Environment Check ==" -ForegroundColor Cyan
Write-Host ("Project root: {0}" -f $ProjectRoot)

if ($PSVersionTable.PSVersion) {
    Write-Check "PASS" ("PowerShell version: {0}" -f $PSVersionTable.PSVersion)
} else {
    Add-Fail "PowerShell version could not be detected."
}

$PythonCmd = Get-Command python -ErrorAction SilentlyContinue
if ($PythonCmd) {
    $PythonVersionText = (& python --version 2>&1 | Out-String).Trim()
    Write-Check "PASS" ("Python found: {0}" -f $PythonVersionText)
    try {
        $PythonVersionOk = (& python -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)")
        if ($LASTEXITCODE -eq 0) {
            Write-Check "PASS" "Python version is 3.10 or newer."
        } else {
            Add-Fail "Python 3.10 or newer is required."
        }
    } catch {
        Add-Fail "Python version check failed."
    }
} else {
    Add-Fail "Python was not found in PATH."
}

$NodeCmd = Get-Command node -ErrorAction SilentlyContinue
if ($NodeCmd) {
    $NodeVersion = (& node --version 2>&1 | Out-String).Trim()
    Write-Check "PASS" ("Node found: {0}" -f $NodeVersion)
} else {
    Add-Fail "Node.js was not found in PATH."
}

$NpmCmd = Get-Command npm -ErrorAction SilentlyContinue
if ($NpmCmd) {
    $NpmVersion = (& npm --version 2>&1 | Out-String).Trim()
    Write-Check "PASS" ("npm found: {0}" -f $NpmVersion)
} else {
    Add-Fail "npm was not found in PATH."
}

if (Get-Command ffmpeg -ErrorAction SilentlyContinue) {
    $FfmpegVersion = (& ffmpeg -version 2>&1 | Select-Object -First 1 | Out-String).Trim()
    Write-Check "PASS" ("ffmpeg found: {0}" -f $FfmpegVersion)
} else {
    Write-Check "WARN" "ffmpeg was not found in PATH. Rendering may fail until FFmpeg is installed."
}

if (Get-Command ffprobe -ErrorAction SilentlyContinue) {
    $FfprobeVersion = (& ffprobe -version 2>&1 | Select-Object -First 1 | Out-String).Trim()
    Write-Check "PASS" ("ffprobe found: {0}" -f $FfprobeVersion)
} else {
    Write-Check "WARN" "ffprobe was not found in PATH. Video inspection may fail until FFmpeg is installed."
}

$BackendDir = Join-Path $ProjectRoot "backend"
$FrontendDir = Join-Path $ProjectRoot "frontend"
$JobsDir = Join-Path $BackendDir "storage\jobs"

if (Test-Path $BackendDir -PathType Container) {
    Write-Check "PASS" ("Backend folder exists: {0}" -f $BackendDir)
} else {
    Add-Fail ("Backend folder is missing: {0}" -f $BackendDir)
}

if (Test-Path $FrontendDir -PathType Container) {
    Write-Check "PASS" ("Frontend folder exists: {0}" -f $FrontendDir)
} else {
    Add-Fail ("Frontend folder is missing: {0}" -f $FrontendDir)
}

try {
    if (-not (Test-Path $JobsDir -PathType Container)) {
        New-Item -ItemType Directory -Path $JobsDir -Force | Out-Null
    }
    Write-Check "PASS" ("Jobs storage is ready: {0}" -f $JobsDir)
} catch {
    Add-Fail ("Jobs storage could not be created: {0}" -f $JobsDir)
}

foreach ($Port in @(8000, 3000)) {
    if (Test-PortAvailable -Port $Port) {
        Write-Check "PASS" ("Port {0} appears available." -f $Port)
    } else {
        Write-Check "WARN" ("Port {0} appears to be in use. Stop the other app or change ports." -f $Port)
    }
}

if ($CriticalFailures -gt 0) {
    Write-Host "Environment check failed. Fix FAIL items and run this script again." -ForegroundColor Red
    exit 1
}

Write-Host "Environment check passed. WARN items should be reviewed before rendering." -ForegroundColor Green
exit 0
