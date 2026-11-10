# PrintX - Elevated Firewall Setup Script for Windows 11
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  PrintX - Configuring Windows Defender Firewall for LAN" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

# Test Administrator privileges
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "`nElevating with Administrator privileges..." -ForegroundColor Yellow
    Start-Process powershell -Verb RunAs -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`""
    exit
}

# Remove existing rules if any
netsh advfirewall firewall delete rule name="PrintX Frontend (Port 3000)" | Out-Null
netsh advfirewall firewall delete rule name="PrintX Frontend (Port 5173)" | Out-Null
netsh advfirewall firewall delete rule name="PrintX Backend (Port 8000)" | Out-Null

# Add inbound rules for ports 3000, 5173 and 8000 across all profiles
Write-Host "Adding Inbound Rule for Frontend (Port 3000)..." -ForegroundColor Green
netsh advfirewall firewall add rule name="PrintX Frontend (Port 3000)" dir=in action=allow protocol=TCP localport=3000 profile=any

Write-Host "Adding Inbound Rule for Frontend (Port 5173)..." -ForegroundColor Green
netsh advfirewall firewall add rule name="PrintX Frontend (Port 5173)" dir=in action=allow protocol=TCP localport=5173 profile=any

Write-Host "Adding Inbound Rule for Backend (Port 8000)..." -ForegroundColor Green
netsh advfirewall firewall add rule name="PrintX Backend (Port 8000)" dir=in action=allow protocol=TCP localport=8000 profile=any

Write-Host "`nSUCCESS: Ports 3000, 5173 and 8000 are now open for mobile access!" -ForegroundColor Cyan
Write-Host "Press any key to exit..."
[Console]::ReadKey() | Out-Null
