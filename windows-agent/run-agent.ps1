# PrintX - Run Windows Print Agent (Windows 11 PowerShell)
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host " Starting PrintX Windows 11 Agent..." -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

$env:PYTHONPATH = "."
python -m app.main

