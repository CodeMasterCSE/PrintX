# PrintX - Master Setup Script for Windows 11
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host " PrintX Platform - Initial Environment Setup" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

# 1. Verify Python
Write-Host "`n[1/3] Checking Python 3.11+ Installation..." -ForegroundColor Yellow
python --version
if ($LASTEXITCODE -ne 0) {
    Write-Error "Python is not installed or not in PATH."
    exit 1
}

# 2. Install Backend Python Dependencies
Write-Host "`n[2/3] Installing Backend Dependencies..." -ForegroundColor Yellow
python -m pip install -r backend/requirements.txt
if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to install Python dependencies."
    exit 1
}

# 3. Install Frontend Node Dependencies
Write-Host "`n[3/3] Installing Frontend Dependencies..." -ForegroundColor Yellow
npm install --prefix frontend
if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to install npm packages."
    exit 1
}

Write-Host "`n==========================================" -ForegroundColor Green
Write-Host " Setup Completed Successfully!" -ForegroundColor Green
Write-Host " Run 'scripts/run-all.ps1' to launch PrintX." -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green

