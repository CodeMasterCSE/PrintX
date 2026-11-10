# PrintX - Master Launch Script for Windows 11
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host " Launching PrintX Full Stack Platform..." -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

# Detect active Wi-Fi or LAN IPv4 address for mobile access
$lanIp = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.IPAddress -notmatch '^127\.' -and $_.IPAddress -notmatch '^169\.254\.' -and $_.InterfaceAlias -notmatch 'vEthernet' } | Select-Object -First 1).IPAddress
if (-not $lanIp) { $lanIp = "192.168.29.16" }

# Start Backend in separate PowerShell process
Write-Host "Launching Backend on http://0.0.0.0:8000..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd backend; .\run-backend.ps1"

# Start Frontend in separate PowerShell process
Write-Host "Launching Frontend on http://0.0.0.0:5173..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd frontend; .\run-frontend.ps1"

# Start Windows Agent in separate PowerShell process
Write-Host "Launching Windows Print Controller Agent..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd windows-agent; .\run-agent.ps1"

Write-Host "`nPrintX full stack services launched in separate consoles." -ForegroundColor Cyan
Write-Host "Student Portal:   http://localhost:5173" -ForegroundColor White
Write-Host "Mobile Phone URL: http://${lanIp}:5173/print?device=KIOSK-01" -ForegroundColor Yellow
Write-Host "Kiosk Standby UI: http://${lanIp}:5173/kiosk/KIOSK-01" -ForegroundColor Cyan
Write-Host "Admin Dashboard:  http://localhost:5173/admin" -ForegroundColor White
Write-Host "User Dashboard:   http://localhost:5173/dashboard" -ForegroundColor White
Write-Host "Backend API:      http://${lanIp}:8000" -ForegroundColor White
Write-Host "Swagger Docs:     http://${lanIp}:8000/docs" -ForegroundColor White

