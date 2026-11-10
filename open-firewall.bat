@echo off
title PrintX - Open Firewall for Mobile Access
color 0A

:: Check for Administrator elevation
net session >nul 2>&1
if %errorLevel% == 0 (
    goto :admin
) else (
    echo ============================================================
    echo  PrintX: Requesting Administrator Elevation...
    echo ============================================================
    echo  A Windows UAC prompt will appear. Please click 'Yes' to allow.
    powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process cmd -ArgumentList '/c \"\"%~dpnx0\"\"' -Verb RunAs"
    exit /b
)

:admin
cls
echo ============================================================
echo   PrintX - Configuring Windows Defender Firewall for LAN
echo ============================================================
echo.
echo Removing any existing outdated PrintX rules...
netsh advfirewall firewall delete rule name="PrintX Frontend (Port 3000)" >nul 2>&1
netsh advfirewall firewall delete rule name="PrintX Frontend (Port 5173)" >nul 2>&1
netsh advfirewall firewall delete rule name="PrintX Backend (Port 8000)" >nul 2>&1
netsh advfirewall firewall delete rule name="PrintX-3000" >nul 2>&1
netsh advfirewall firewall delete rule name="PrintX-5173" >nul 2>&1
netsh advfirewall firewall delete rule name="PrintX-8000" >nul 2>&1

echo Adding Inbound Rule for Frontend (TCP Port 3000 - Primary)...
netsh advfirewall firewall add rule name="PrintX Frontend (Port 3000)" dir=in action=allow protocol=TCP localport=3000 profile=any

echo Adding Inbound Rule for Frontend (TCP Port 5173 - Fallback)...
netsh advfirewall firewall add rule name="PrintX Frontend (Port 5173)" dir=in action=allow protocol=TCP localport=5173 profile=any

echo Adding Inbound Rule for Backend (TCP Port 8000)...
netsh advfirewall firewall add rule name="PrintX Backend (Port 8000)" dir=in action=allow protocol=TCP localport=8000 profile=any

echo.
echo ============================================================
echo  SUCCESS: Windows Firewall ports 3000, 5173 and 8000 are OPEN!
echo ============================================================
echo.
echo  Mobile phones on your Wi-Fi network (JioFiber) can now access:
echo    http://192.168.29.16:5173/print?device=KIOSK-01
echo.
echo  NOTE: If you have McAfee installed (even if expired),
echo  make sure McAfee Firewall is set to Turn Off or uninstalled.
echo ============================================================
echo.
pause
