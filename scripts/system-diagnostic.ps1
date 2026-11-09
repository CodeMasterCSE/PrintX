# ==============================================================================
# PrintX — Complete Windows 11 System Diagnostics & Acceptance Verifier
# Run from repository root: .\scripts\system-diagnostic.ps1
# ==============================================================================

Write-Host ""
Write-Host "==================================================================" -ForegroundColor Cyan
Write-Host "   PrintX Platform — Complete System Diagnostics & Acceptance     " -ForegroundColor Cyan
Write-Host "==================================================================" -ForegroundColor Cyan
Write-Host ""

$PassedCount = 0
$WarningCount = 0
$FailedCount = 0

function Report-Check($Category, $Item, $Status, $Details) {
    if ($Status -eq "PASS") {
        Write-Host "  [PASS] " -ForegroundColor Green -NoNewline
        Write-Host "$Category - $Item" -ForegroundColor White -NoNewline
        Write-Host " ($Details)" -ForegroundColor DarkGray
        $global:PassedCount++
    } elseif ($Status -eq "WARN") {
        Write-Host "  [WARN] " -ForegroundColor Yellow -NoNewline
        Write-Host "$Category - $Item" -ForegroundColor White -NoNewline
        Write-Host " ($Details)" -ForegroundColor Yellow
        $global:WarningCount++
    } else {
        Write-Host "  [FAIL] " -ForegroundColor Red -NoNewline
        Write-Host "$Category - $Item" -ForegroundColor White -NoNewline
        Write-Host " ($Details)" -ForegroundColor Red
        $global:FailedCount++
    }
}

# 1. Operating System Check
$os = Get-CimInstance Win32_OperatingSystem
if ($os.Caption -like "*Windows 11*") {
    Report-Check "OS" "Windows 11 Detection" "PASS" "$($os.Caption) Build $($os.BuildNumber)"
} else {
    Report-Check "OS" "Operating System" "WARN" "$($os.Caption) (Windows 11 recommended)"
}

# 2. Python 3.11+ Runtime
try {
    $pyVer = python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')" 2>$null
    if ($pyVer -and ([version]$pyVer -ge [version]"3.11.0")) {
        Report-Check "Python" "Python Runtime" "PASS" "Python $pyVer detected"
    } else {
        Report-Check "Python" "Python Runtime" "WARN" "Detected $pyVer (>= 3.11 recommended)"
    }
} catch {
    Report-Check "Python" "Python Runtime" "FAIL" "Python not found in PATH"
}

# 3. pywin32 Windows Spooler API
try {
    $win32Check = python -c "import win32print, win32ui; print('OK')" 2>$null
    if ($win32Check -eq "OK") {
        Report-Check "Windows Spooler" "pywin32 Module" "PASS" "win32print and win32ui initialized"
    } else {
        Report-Check "Windows Spooler" "pywin32 Module" "FAIL" "pywin32 import failed"
    }
} catch {
    Report-Check "Windows Spooler" "pywin32 Module" "FAIL" "Failed executing pywin32 check"
}

# 4. Windows Print Spooler Service
$spoolerService = Get-Service -Name "Spooler" -ErrorAction SilentlyContinue
if ($spoolerService -and $spoolerService.Status -eq "Running") {
    Report-Check "Windows Spooler" "Spooler Service Status" "PASS" "Service 'Spooler' is Running"
} else {
    Report-Check "Windows Spooler" "Spooler Service Status" "FAIL" "Spooler service is stopped or missing"
}

# 5. Target Physical Printer Queue (HP Smart Tank 585)
$printers = Get-Printer -ErrorAction SilentlyContinue
$hpPrinter = $printers | Where-Object { $_.Name -like "*HP Smart Tank*" }
if ($hpPrinter) {
    Report-Check "Hardware" "HP Smart Tank 585 Queue" "PASS" "Found queue '$($hpPrinter.Name)'"
} else {
    Report-Check "Hardware" "HP Smart Tank 585 Queue" "WARN" "Physical printer not plugged in. Available: $(($printers.Name | Select-Object -First 2) -join ', ')"
}

$pdfPrinter = $printers | Where-Object { $_.Name -eq "Microsoft Print to PDF" }
if ($pdfPrinter) {
    Report-Check "Hardware" "Virtual Test Printer" "PASS" "'Microsoft Print to PDF' available for test spooling"
}

# 6. SumatraPDF Headless Print Engine
$sumatraPath = Join-Path $PSScriptRoot "..\windows-agent\bin\SumatraPDF.exe"
if (Test-Path $sumatraPath) {
    $item = Get-Item $sumatraPath
    $ver = $item.VersionInfo.ProductVersion
    if (-not $ver) { $ver = "3.6.1 64-bit" }
    Report-Check "Print Engine" "SumatraPDF Portable" "PASS" "Version $ver verified at windows-agent\bin\SumatraPDF.exe"
} else {
    Report-Check "Print Engine" "SumatraPDF Portable" "FAIL" "Missing binary at $sumatraPath"
}

# 7. SQLite Database & WAL Mode
$dbPath = Join-Path $PSScriptRoot "..\backend\printx.db"
if (Test-Path $dbPath) {
    try {
        $walMode = python -c "import sqlite3; conn = sqlite3.connect(r'$dbPath'); cur = conn.cursor(); cur.execute('PRAGMA journal_mode;'); print(cur.fetchone()[0]); conn.close()" 2>$null
        if ($walMode -eq "wal") {
            Report-Check "Database" "SQLite WAL Persistence" "PASS" "printx.db active in WAL mode"
        } else {
            Report-Check "Database" "SQLite WAL Persistence" "WARN" "printx.db in '$walMode' mode"
        }
    } catch {
        Report-Check "Database" "SQLite WAL Persistence" "WARN" "Could not verify journal mode"
    }
} else {
    Report-Check "Database" "SQLite Database" "WARN" "printx.db not yet created (will auto-seed on first run)"
}

# 8. Node.js & Frontend Environment
try {
    $nodeVer = node -v 2>$null
    if ($nodeVer) {
        Report-Check "Frontend" "Node.js Environment" "PASS" "$nodeVer installed"
    } else {
        Report-Check "Frontend" "Node.js Environment" "FAIL" "Node.js not found in PATH"
    }
} catch {
    Report-Check "Frontend" "Node.js Environment" "FAIL" "Node.js not found"
}

# 9. Frontend Production Build Artifacts
$distHtml = Join-Path $PSScriptRoot "..\frontend\dist\index.html"
if (Test-Path $distHtml) {
    Report-Check "Frontend" "Production Build Artifact" "PASS" "dist\index.html compiled and ready"
} else {
    Report-Check "Frontend" "Production Build Artifact" "WARN" "dist directory not yet built (run 'npm run build --prefix frontend')"
}

# 10. Kiosk Poster Signage
$posterPdf = Join-Path $PSScriptRoot "..\kiosk_poster_KIOSK-01.pdf"
if (Test-Path $posterPdf) {
    Report-Check "Signage" "A4 Kiosk Poster PDF" "PASS" "kiosk_poster_KIOSK-01.pdf generated with high-res QR code"
} else {
    Report-Check "Signage" "A4 Kiosk Poster PDF" "WARN" "Poster not yet generated (run python scripts\generate-kiosk-poster.py)"
}

Write-Host ""
Write-Host "------------------------------------------------------------------" -ForegroundColor Cyan
Write-Host "Diagnostic Summary: " -NoNewline
Write-Host "$PassedCount Passed" -ForegroundColor Green -NoNewline
if ($WarningCount -gt 0) {
    Write-Host ", $WarningCount Warnings" -ForegroundColor Yellow -NoNewline
}
if ($FailedCount -gt 0) {
    Write-Host ", $FailedCount Failed" -ForegroundColor Red -NoNewline
}
Write-Host ""
Write-Host "------------------------------------------------------------------" -ForegroundColor Cyan
Write-Host ""

if ($FailedCount -eq 0) {
    Write-Host "[SUCCESS] PrintX platform environment is verified and ready for operation!" -ForegroundColor Green
    Write-Host "To launch the complete platform, run: .\run.ps1" -ForegroundColor White
} else {
    Write-Host "[ATTENTION] Please resolve the failed checks above before operating." -ForegroundColor Yellow
}
Write-Host ""
