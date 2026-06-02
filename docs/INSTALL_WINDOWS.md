# Malrocut Windows Beta Installation

Malrocut 0.1.0-beta is beta software. It is intended for early customers and testers, so some rendering behavior and setup steps may change in future releases.

## Required OS

- Windows 10 or Windows 11

## Required tools

- Python 3.10+
- Node.js LTS
- FFmpeg, including both `ffmpeg` and `ffprobe` in PATH
- Git is optional if the project folder is already provided as a ZIP or direct copy

## How to run

1. Open PowerShell.
2. Change directory to the project folder:
   ```powershell
   cd C:\path\to\malrocut-ai-mvp
   ```
3. Allow scripts for this PowerShell session only:
   ```powershell
   Set-ExecutionPolicy -Scope Process Bypass
   ```
4. Check the environment:
   ```powershell
   .\scripts\check-env.ps1
   ```
5. Start Malrocut:
   ```powershell
   .\scripts\start-malrocut.ps1
   ```

## URLs

- Backend URL: http://127.0.0.1:8000
- Frontend URL: http://localhost:3000
- API docs URL: http://127.0.0.1:8000/docs
- Health URL: http://127.0.0.1:8000/api/health

## Common troubleshooting

### ffmpeg not found

Install FFmpeg and make sure the folder containing `ffmpeg.exe` and `ffprobe.exe` is in your Windows PATH. The environment check reports missing FFmpeg as WARN because the app can start, but rendering may fail until FFmpeg is available.

### npm not found

Install Node.js LTS from the official Node.js website. Reopen PowerShell after installation so PATH changes are loaded.

### Python not found

Install Python 3.10 or newer. During installation, enable the option to add Python to PATH. Reopen PowerShell after installation.

### Port already in use

Malrocut uses backend port 8000 and frontend port 3000 by default. If either port is already in use, stop the other program or restart your computer and try again.

### Korean text garbled in PowerShell

The startup scripts attempt to use UTF-8 automatically. If Korean text is still garbled, run this before starting Malrocut:

```powershell
chcp 65001
$OutputEncoding = [System.Text.Encoding]::UTF8
```

## Beta note

This package is a beta release. Use short videos first, keep original files backed up, and verify the rendered output before commercial delivery.
