# Run the automated test-suite (Windows PowerShell).   .\test.ps1
Set-Location "$PSScriptRoot\backend"
& ".\.venv\Scripts\python.exe" manage.py test -v 2
