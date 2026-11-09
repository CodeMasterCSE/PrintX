# PrintX — Smart Self-Service Printing Platform

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Platform: Windows 11](https://img.shields.io/badge/Platform-Windows%2011-0078D6.svg)](https://microsoft.com/windows)
[![Python: 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg)](https://fastapi.tiangolo.com)
[![React: 18+](https://img.shields.io/badge/React-18%2B-61DAFB.svg)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-5+-3178C6.svg)](https://www.typescriptlang.org)

PrintX is an enterprise-grade, open-source self-service document printing platform designed to eliminate queues and human intermediaries at university campuses, libraries, coworking spaces, and retail print centers.

Students scan a QR code at a PrintX kiosk, upload their documents, configure preferences (A4, single-sided, color/grayscale, custom page ranges), review transparent per-page pricing, complete instant UPI payments, and receive their prints directly from the connected printer (targeting the HP Smart Tank 585 series).

---

## 🏛️ System Architecture Overview

```
                               +-----------------------------+
                               |     Student Web Client      |
                               |  (React + TS + Tailwind)    |
                               +--------------+--------------+
                                              |
                                              | HTTPS / JSON
                                              v
+---------------------------------------------------------------------------------------+
|                                    PrintX Backend                                      |
|                                   (FastAPI + Pydantic)                                |
|                                                                                       |
|  +-------------------+  +-------------------+  +-------------------+  +------------+  |
|  | Document Service  |  |  Pricing Engine   |  |  Payment Service  |  | Job Engine |  |
|  | (PyMuPDF / Fitz)  |  |  (Rules & Fees)   |  | (UPI Provider API)|  | (State M/C)|  |
|  +---------+---------+  +---------+---------+  +---------+---------+  +-----+------+  |
|            |                      |                      |                  |         |
|  +---------v----------------------v----------------------v------------------v------+  |
|  |                             SQLAlchemy Data Access Layer                        |  |
|  |                      (SQLite [Dev] -> PostgreSQL [Production])                  |  |
|  +---------------------------------------------------------------------------------+  |
+-------------------------------------------+-------------------------------------------+
                                            |
                                            | Authenticated Polling / Heartbeat
                                            v
+---------------------------------------------------------------------------------------+
|                                Windows Print Controller                                |
|                              (Native Windows 11 Agent)                                |
|                                                                                       |
|  +-------------------------+  +-------------------------+  +-----------------------+  |
|  |    Printer Discovery    |  |     Print Executor      |  |   Spooler Monitor     |  |
|  |      (pywin32 API)      |  |    (SumatraPDF CLI)     |  |  (Job Queue Telemetry)|  |
|  +-------------------------+  +-------------------------+  +-----------------------+  |
+-------------------------------------------+-------------------------------------------+
                                            |
                                            v
+---------------------------------------------------------------------------------------+
|                                  Windows Print Spooler                                 |
+-------------------------------------------+-------------------------------------------+
                                            | USB / Network
                                            v
+---------------------------------------------------------------------------------------+
|                          HP Smart Tank 585 Physical Printer                           |
+---------------------------------------------------------------------------------------+
```

---

## 🚀 Key Modules & Directory Structure

```
PrintX/
├── backend/                  # FastAPI backend service
│   ├── app/                  # Application core, API routes, models, schemas, services
│   ├── tests/                # Automated pytest unit & integration tests
│   └── requirements.txt      # Python dependencies
├── frontend/                 # Vite + React + TypeScript web application
│   ├── src/                  # Components, pages, hooks, styling, state management
│   ├── tests/                # Vitest component & flow tests
│   └── package.json          # Frontend dependencies
├── windows-agent/            # Native Windows 11 print execution agent
│   ├── app/                  # Spooler monitor, SumatraPDF executor, win32 printer API
│   ├── tests/                # Mocked Windows API & spooler tests
│   └── requirements.txt      # Agent dependencies
├── docs/                     # Architecture, security threat model, and API specs
├── scripts/                  # Automated Windows PowerShell launch & setup scripts
└── PROGRESS.md               # Real-time implementation tracking & test status
```

---

## 🔒 Security Principles
- **No Direct Spooler Exposure:** Windows print controller is never exposed to public internet. It connects outbound using mutual authentication tokens.
- **Server-Side Truth:** Document page counts, price calculations, and payment confirmations are never trusted from the client.
- **Strict File Sanitization:** Magic-byte inspection, PDF structure validation, encryption checks, and size caps prevent malicious file execution.
- **Idempotency & Duplicate Prevention:** Cryptographic checksums and unique job idempotency keys ensure no physical document prints twice.

---

## ⚡ Quick Start: Running PrintX

### 1. Launch All Services (One Command)
In Windows 11 PowerShell, run from the root directory:
```powershell
.\run.ps1
```
This launches all three services in dedicated PowerShell windows:
- **Backend API:** `http://127.0.0.1:8000` (Interactive Swagger Docs: `http://127.0.0.1:8000/docs`)
- **Student Web Application:** `http://localhost:5173`
- **Windows Print Agent:** Connected to native Windows Spooler and HP Smart Tank 585

### 2. Service Endpoints & Portal URLs
| Interface | URL | Purpose |
|:---|:---|:---|
| **Kiosk Entry** | [http://localhost:5173/print?device=KIOSK-01](http://localhost:5173/print?device=KIOSK-01) | Main 6-step self-service flow (QR destination) |
| **User Dashboard** | [http://localhost:5173/dashboard](http://localhost:5173/dashboard) | Job history, status tracking, receipts |
| **Admin Dashboard** | [http://localhost:5173/admin](http://localhost:5173/admin) | Queue depths, revenue, printer telemetry, rates |
| **Backend Swagger** | [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) | Interactive OpenAPI documentation |

### 3. Default Demo Accounts
- **Admin:** `admin@printx.local` / `Admin@PrintX2026!`
- **Student:** `student@printx.local` / `Student@PrintX2026!`

### 4. Running Individual Components
If you prefer running components individually in separate terminal tabs:

**Backend Service:**
```powershell
cd backend
$env:PYTHONPATH = "."
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

**Frontend Web App:**
```powershell
cd frontend
npm run dev
```

**Windows Print Agent:**
```powershell
cd windows-agent
$env:PYTHONPATH = "."
python -m app.main
```

### 5. Running Automated Tests (41 Tests)
```powershell
# Backend (30 tests)
python -m pytest backend/tests -v

# Windows Agent (8 tests)
$env:PYTHONPATH = "windows-agent"; python -m pytest windows-agent/tests -v

# Frontend (3 tests)
npm test --prefix frontend
```


