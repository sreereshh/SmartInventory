# One-time setup for Windows PowerShell.  Run from the project root:   .\setup.ps1
# If PowerShell blocks scripts, run once:  Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
$ErrorActionPreference = "Stop"
Set-Location "$PSScriptRoot\backend"

if (-not (Test-Path ".venv")) {
    Write-Host "Creating virtual environment..." -ForegroundColor Cyan
    py -3 -m venv .venv
}
& ".\.venv\Scripts\python.exe" -m pip install --upgrade pip
& ".\.venv\Scripts\python.exe" -m pip install -r requirements.txt
& ".\.venv\Scripts\python.exe" manage.py migrate
& ".\.venv\Scripts\python.exe" manage.py seed_data
Write-Host "`nSetup complete. Start the server with:  .\run.ps1" -ForegroundColor Green
Write-Host "Login: admin / Admin@12345   or   staff / Staff@12345"
