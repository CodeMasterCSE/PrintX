# PrintX - Master Launch Script for Windows 11
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host " Launching PrintX Full Stack Platform..." -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

# Start Backend in separate PowerShell process
Write-Host "Launching Backend on http://127.0.0.1:8000..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd backend; .\run-backend.ps1"

# Start Frontend in separate PowerShell process
Write-Host "Launching Frontend on http://localhost:5173..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd frontend; .\run-frontend.ps1"

# Start Windows Agent in separate PowerShell process
Write-Host "Launching Windows Print Controller Agent..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd windows-agent; .\run-agent.ps1"

Write-Host "`nPrintX full stack services launched in separate consoles." -ForegroundColor Cyan
Write-Host "Student Portal:   http://localhost:5173" -ForegroundColor White
Write-Host "Kiosk Entry URL:  http://localhost:5173/print?device=KIOSK-01" -ForegroundColor Yellow
Write-Host "Admin Dashboard:  http://localhost:5173/admin" -ForegroundColor White
Write-Host "User Dashboard:   http://localhost:5173/dashboard" -ForegroundColor White
Write-Host "Backend API:      http://127.0.0.1:8000" -ForegroundColor White
Write-Host "Swagger Docs:     http://127.0.0.1:8000/docs" -ForegroundColor White

