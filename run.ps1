# Start the Django development server (Windows PowerShell).   .\run.ps1
# 0.0.0.0 lets the Android emulator (10.0.2.2) and phones on your Wi-Fi reach the server.
Set-Location "$PSScriptRoot\backend"
& ".\.venv\Scripts\python.exe" manage.py runserver 0.0.0.0:8000
