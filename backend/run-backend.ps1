# PrintX - Run Backend Service (Windows 11 PowerShell)
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host " Starting PrintX Backend API Service..." -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

$env:PYTHONPATH = "."
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

