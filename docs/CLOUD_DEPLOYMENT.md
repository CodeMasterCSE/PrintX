# PrintX — Cloud Production Deployment & Operations Guide

This guide details the complete deployment process for transitioning PrintX from a single-machine local setup to a high-availability, production-grade **Hybrid Cloud Architecture**.

---

## 1. Hybrid Architecture Overview

In production, PrintX separates public-facing web traffic from physical hardware execution:

```
[ Student Smartphone / Laptop / Kiosk Touchscreen ]
                       │
             HTTPS (TLS 1.3)
                       ▼
          [ Cloud Reverse Proxy: Caddy / Cloudflare ]
                       │
       ┌───────────────┴───────────────┐
       ▼                               ▼
[ Cloud FastAPI Backend ]    [ Cloud Object Storage ]
(Containerized / Multi-Node)   (AWS S3 / Cloudflare R2)
       │                               ▲
       ▼                               │ Authenticated
[ Managed PostgreSQL 16 ]              │ Pre-Signed URLs
(Connection Pooling & WAL)             │
       ▲                               │
       │                               │
       │ Polling Outbound / HTTPS      │
       └───────────────────────────────┘
                       │
        [ Outbound Windows Print Agent ]
        (Windows 11 Kiosk / Micro-PC)
                       │
           Windows Print Spooler (pywin32)
                       │
              SumatraPDF Engine
                       │
             USB 2.0 Direct Cable
                       ▼
             [ HP Smart Tank 585 ]
```

### Key Security & Operational Principles
1. **Zero Open Inbound Ports on Kiosk:** The Windows 11 host never runs an open HTTP server or listening port facing the internet or campus LAN. All communication is strictly outbound HTTPS polling or WebSockets.
2. **Device Identity & Secret Isolation:** Each physical kiosk or print station has a distinct `agent_id` and cryptographically secure secret (`X-Agent-Secret`).
3. **Decoupled Document Storage:** Heavy PDF payloads are stored in S3 or Cloudflare R2 object storage. The cloud backend only dispenses short-lived, pre-signed download URLs to authorized agents.
4. **Mechanical Truth Reporting:** The Windows Print Agent tracks Windows spooler job handles and status bitflags, guaranteeing that spooler failures, paper-outs, or driver hangs reflect accurately in user telemetry.

---

## 2. Cloud Backend Deployment

### A. Prerequisites
- Linux Cloud Host (Ubuntu 22.04 LTS / Debian 12 / AWS ECS / Google Cloud Run)
- Managed PostgreSQL 16 (AWS RDS, Supabase, Neon, or self-hosted)
- Object Storage (AWS S3, Cloudflare R2, or MinIO)
- Registered Domain Name with SSL (Let's Encrypt / Cloudflare)

### B. Environment Configuration (`.env.production`)
Create a production `.env` file on the cloud server:

```ini
ENVIRONMENT=production
DEBUG=False
SECRET_KEY=generate-a-strong-64-character-random-hex-string
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=7

# Public URL
SERVER_PUBLIC_URL=https://printx.yourcampus.edu

# Database Connection (Managed PostgreSQL)
DATABASE_URL=postgresql://printx_user:SuperSecurePassword123@db-host.internal:5432/printx_prod

# Object Storage Backend (S3 or Cloudflare R2)
STORAGE_BACKEND=s3
S3_BUCKET_NAME=printx-documents-prod
S3_ENDPOINT_URL=https://<account-id>.r2.cloudflarestorage.com  # Or omit for standard AWS S3
S3_ACCESS_KEY=your_r2_access_key
S3_SECRET_KEY=your_r2_secret_key
S3_REGION_NAME=auto  # Or us-east-1, ap-south-1

# UPI Payment Gateway (Razorpay / Cashfree)
PAYMENT_GATEWAY_PROVIDER=razorpay
RAZORPAY_KEY_ID=rzp_live_xxxxxxxxxxxx
RAZORPAY_KEY_SECRET=your_production_key_secret
RAZORPAY_WEBHOOK_SECRET=your_webhook_signing_secret

# Default Hardware Profile
DEFAULT_PRINTER_NAME=HP Smart Tank 580-590 series
```

### C. Docker Deployment
PrintX includes a multi-stage, non-root `Dockerfile` in `backend/Dockerfile`.

1. **Build and Tag Container:**
```bash
docker build -t printx-backend:1.0.0 -f backend/Dockerfile .
```

2. **Run with Docker Compose:**
Deploy using the production stack defined in `docker-compose.yml`:
```bash
docker compose up -d
```

3. **Run Database Migrations (Alembic):**
Apply the complete database schema to PostgreSQL:
```bash
docker compose exec backend alembic upgrade head
```

4. **Verify Health:**
```bash
curl https://printx.yourcampus.edu/health/ready
# Expected: {"status":"ready","database":"healthy"}
```

---

## 3. Object Storage & Retention Lifecycle

### A. Cloudflare R2 / AWS S3 Configuration
1. **Bucket Creation:** Name your bucket `printx-documents-prod`.
2. **CORS Policy (if direct client uploads enabled in future):**
```json
[
  {
    "AllowedOrigins": ["https://printx.yourcampus.edu"],
    "AllowedMethods": ["GET", "PUT", "POST", "HEAD"],
    "AllowedHeaders": ["*"],
    "ExposeHeaders": ["ETag"],
    "MaxAgeSeconds": 3600
  }
]
```
3. **Automated Document Retention & Purge Policy:**
PrintX protects user privacy by purging uploaded documents after successful printing or order expiration.
Configure an S3 Lifecycle Rule:
- **Prefix:** `documents/`
- **Action:** Expire / Delete objects after **2 days** (48 hours).
- The database records retain job metadata for audit and accounting, while the binary PDF is automatically wiped from object storage.

---

## 4. Windows 11 Outbound Agent Setup

The Windows Print Agent runs directly on the Windows 11 host connected to the **HP Smart Tank 585** via USB.

### A. Register Agent Device in Cloud Backend
As an administrator, register the hardware terminal using the admin API or dashboard:
```powershell
Invoke-RestMethod -Method Post `
  -Uri "https://printx.yourcampus.edu/api/v1/admin/agents/register" `
  -Headers @{ "Authorization" = "Bearer YOUR_ADMIN_JWT_TOKEN" } `
  -ContentType "application/json" `
  -Body '{"name": "Library Kiosk 01", "hostname": "WIN11-KIOSK-01", "ip_address": "10.0.4.15"}'
```
Save the returned `agent_id` and `agent_secret`.

### B. Configure Agent Environment (`windows-agent/.env`)
On the Windows 11 machine, update `windows-agent/.env`:
```ini
BACKEND_API_URL=https://printx.yourcampus.edu
AGENT_ID=AGENT-WIN11-XXXXXX
AGENT_SECRET=px_sec_your_secret_token_here
TARGET_PRINTER_NAME=HP Smart Tank 580-590 series
FALLBACK_PRINTER_NAME=Microsoft Print to PDF
POLL_INTERVAL_SECONDS=3.0
HEARTBEAT_INTERVAL_SECONDS=15.0
TEMP_CACHE_DIR=C:\PrintX\cache
```

### C. Run as an Automatic Windows Service with NSSM

To guarantee the agent starts on system boot, survives user logoffs, and automatically restarts on unexpected crashes, use **NSSM (Non-Sucking Service Manager)**:

1. Download NSSM from [https://nssm.cc](https://nssm.cc) and place `nssm.exe` in `C:\PrintX\bin\`.
2. Open PowerShell as **Administrator**:
```powershell
# Set installation directory
$AgentDir = "C:\Users\sampa\Desktop\PrintX\windows-agent"
$PythonExe = (Get-Command python).Source

# Install Windows Service
C:\PrintX\bin\nssm.exe install PrintXAgent $PythonExe "$AgentDir\run_agent.py"
C:\PrintX\bin\nssm.exe set PrintXAgent AppDirectory $AgentDir
C:\PrintX\bin\nssm.exe set PrintXAgent Description "PrintX Windows Print Spooler Controller for HP Smart Tank 585"
C:\PrintX\bin\nssm.exe set PrintXAgent Start SERVICE_AUTO_START
C:\PrintX\bin\nssm.exe set PrintXAgent AppStdout "$AgentDir\logs\agent_stdout.log"
C:\PrintX\bin\nssm.exe set PrintXAgent AppStderr "$AgentDir\logs\agent_stderr.log"

# Start the service
C:\PrintX\bin\nssm.exe start PrintXAgent
```

3. **Verify Service Status:**
```powershell
Get-Service PrintXAgent
# Status: Running
```

### D. Alternative: Windows Task Scheduler
If running in an environment without NSSM permissions, register via Task Scheduler:
```powershell
$Action = New-ScheduledTaskAction -Execute "python.exe" -Argument "run_agent.py" -WorkingDirectory "C:\Users\sampa\Desktop\PrintX\windows-agent"
$Trigger = New-ScheduledTaskTrigger -AtStartup
$Principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)
Register-ScheduledTask -TaskName "PrintXAgentService" -Action $Action -Trigger $Trigger -Principal $Principal -Settings $Settings
```

---

## 5. Production Security Hardening

### A. Zero Inbound Exposure
- Ensure the Windows 11 Firewall blocks all inbound connection requests on public and private network profiles (`netsh advfirewall set allprofiles firewallpolicy blockinbound,allowoutbound`).
- The agent initiates 100% of network traffic via TLS 1.3 outbound requests to the backend server URL.

### B. Mutual Secret Authentication
- Every poll request `/api/v1/jobs/agent/pull` and status update `/api/v1/jobs/agent/status` must pass:
  - Header: `X-Agent-ID: AGENT-WIN11-XXXXXX`
  - Header: `X-Agent-Secret: px_sec_...`
- The backend matches the provided secret against bcrypt hashes in the database. Raw secrets are never stored in plaintext.

### C. Stale Job Reconciliation
- If a Windows agent loses power or internet connectivity midway through a job lifecycle:
  - The backend runs a periodic reconciliation routine (`JobService.reconcile_stale_jobs`).
  - Jobs lingering in `DISPATCHED` or `SUBMITTED_TO_SPOOLER` without agent heartbeats for more than 10 minutes are flagged as `STALE_RECONCILED` or `FAILED`.
  - The client is notified, and refund/retry procedures are initiated.

---

## 6. Hardware Troubleshooting Runbook (HP Smart Tank 585)

| Symptom | Root Cause | Operator Resolution |
| :--- | :--- | :--- |
| **SumatraPDF Error Code 1** | Corrupted PDF payload or invalid page syntax | Agent automatically marks job `FAILED`. Check document preview in Admin Dashboard. |
| **Spooler status: `JOB_STATUS_PAPEROUT`** | Out of paper in input tray | Reload A4 paper into rear feed. Agent detects tray recovery and resumes spooling. |
| **Spooler status: `JOB_STATUS_OFFLINE`** | USB cable disconnected or printer asleep | Check USB 2.0 connection. Press printer Power button to wake. |
| **Job stuck in `SUBMITTED_TO_SPOOLER`** | Windows Print Spooler service hung | Restart spooler via PowerShell: `Restart-Service Spooler -Force`. Agent will recover pending queue. |
| **Duplicate print attempts blocked** | Re-entry safeguard triggered | Check `processed_jobs.json`. To force a reprint after mechanical paper jam, use Admin Dashboard with "Force Reprocess". |

