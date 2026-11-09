# PrintX — Implementation Progress & Architecture Tracker

## 1. Project Overview & Deliverables
PrintX is an open-source, production-grade smart self-service document printing platform. It empowers students and campus patrons to scan a kiosk QR code, upload documents, configure print settings (single-sided simplex for HP Smart Tank 585 hardware safety), pay via UPI, and receive physical prints via an autonomous Windows 11 Spooler controller.

---

## 2. Completed Milestones

### A. Core Architecture & Windows 11 Native Integration
- **Platform Stack:** React + TypeScript + Vite + Tailwind CSS frontend; Python 3.11+ + FastAPI backend; SQLite (WAL mode) with PostgreSQL-ready SQLAlchemy models; native Windows 11 spooler agent with `pywin32` and SumatraPDF CLI.
- **Hardware Integration:** Configured and validated for **HP Smart Tank 585** (`HP Smart Tank 580-590 series` driver).
- **Simplex Hardware Restriction:** Enforced `simplex` across UI, validation schemas, and SumatraPDF arguments (`-print-settings "simplex,fit"`) to prevent mechanical paper jams on non-duplex hardware.
- **Physical Hardware Verification:** Successfully dispatched and physically printed a 2-page test document to the HP Smart Tank 585 via USB 2.0.

### B. Document Processing & Authoritative Pricing Engine
- **PyMuPDF Validation:** PDF magic bytes (`%PDF-`), file size limits, page counts, color space inspection, and encrypted/corrupt document rejection.
- **Server-Side Pricing Engine:** Authoritative calculation protecting against client-side tampering (₹2.00/page B&W, ₹10.00/page Color, custom page ranges, copy multipliers).
- **First-Page Thumbnail Previews:** Dynamic PNG rendering via `/api/v1/documents/{id}/preview?page=1`.

### C. Deterministic Job State Machine & Safeguards
- **12 Comprehensive States:** `CREATED`, `DOCUMENT_VALIDATED`, `PAYMENT_PENDING`, `PAYMENT_VERIFIED`, `QUEUED`, `DISPATCHED`, `SUBMITTED_TO_SPOOLER`, `PRINTING`, `COMPLETED`, `FAILED`, `CANCELLED`, `REFUNDED`.
- **Live Queue Telemetry:** Real-time queue position calculation (`#1 in line`, `#2 in line`) and estimated wait times (seconds/minutes) based on active spooler backlog.
- **Duplicate Print Safeguards:** Strict protection against blind retries once a job has been submitted to the Windows Spooler. Re-entry requires explicit operator `force_retry`.
- **Crash Recovery & Reconciliation:** Server-side stale job reconciliation (`reconcile_stale_jobs`) for handling agent drops or power cuts.

### D. Provider-Independent Payment Gateway & UPI Verification
- **Payment Abstraction:** `BasePaymentGateway` interface with implementations: `MockUpiGateway`, `RazorpayGateway`, `CashfreeGateway`.
- **NPCI UPI Standards:** Generates canonical `upi://pay?pa=...&pn=...&am=...&cu=INR` payloads.
- **Dual QR Presentation:** Dynamic high-resolution PNG streaming (`/payments/{id}/qr.png`) and Base64 Data URL embedding.
- **Webhook Signature Verification:** HMAC-SHA256 signature verification with idempotency protection.
- **Refund Safeguards:** Permitted for unprinted/cancelled jobs with audit records; strictly blocked for physically printed jobs.

### E. Complete Student Web Application (`frontend/`)
- **Step 1: Upload Document:** Drag-and-drop dropzone, file picker, file size caps, page count extraction, first-page PNG preview.
- **Step 2: Configure Printing:** A4 standard, Grayscale vs Color, copies (1-10), custom page ranges, strict single-sided (simplex) banner, live cost estimate.
- **Step 3: Review Order:** Transparent cost breakdown with authoritative server validation.
- **Step 4: Payment:** Real-time UPI payment flow with dynamic QR codes, mobile deep links, mock sandbox approval controls, and active polling.
- **Step 5: Printing Status:** Truthful spooler progress stepper displaying live queue position, estimated wait times, and duplicate-safe retry controls.
- **Step 6: Digital Receipt:** Printable/downloadable proof (`window.print()`) and instant new job CTA.
- **User Dashboard (`/dashboard`):** Real-time print job table with status badges, KPI metrics, printable receipt modal, and safe retry controls.
- **Admin Dashboard (`/admin`):**
  - **Overview & Telemetry:** Gross, daily, weekly, and monthly revenue metrics, total pages printed, spooler queue depth, active print agent count, and system health status.
  - **Printer Queue Management:** Hardware status inspection, maintenance mode toggle (`READY` / `MAINTENANCE`), and global default printer designation.
  - **Kiosk Terminal Management:** Real-time campus kiosk terminal registry (`code`, `name`, `location`, bound printer, and QR URL).
  - **Platform Settings Management:** Configurable upload caps, page ceilings, retention duration, and maintenance locks.
  - **Live Pricing Rate Editor:** Real-time B&W and Color per-page price updates with database persistence.
  - **Job Audit & Lifecycle Management:** Real-time multi-filter and search across all campus jobs with error inspection.

### F. Cloud Readiness & Storage Abstraction (Phase 8 Completed)
- **Alembic Database Migrations:** Initialized in `backend/alembic/` with baseline migration `45a8d3e0e62a_initial_schema.py` covering all 12 tables and indices, stamped at `head`.
- **Docker Containerization:** Multi-stage, non-root `backend/Dockerfile` and production `docker-compose.yml` with PostgreSQL 16.
- **Pluggable Storage Abstraction:** `backend/app/storage/storage_provider.py` implementing `BaseStorageProvider`, `LocalStorageProvider`, and `S3StorageProvider` (compatible with AWS S3, Cloudflare R2, and MinIO).
- **Secure Document Download Endpoint:** `GET /api/v1/documents/{id}/download` with streaming binary response and content disposition headers.
- **Outbound Agent Device Registration:** `POST /api/v1/admin/agents/register` generating unique `agent_id` and raw secret tokens (`px_sec_...`) with bcrypt hashing in database; `GET /api/v1/admin/agents` for fleet monitoring.
- **Outbound Agent Cloud Streaming:** `windows-agent/app/job_receiver.py` transparently downloads remote cloud documents to a local disk cache before invoking SumatraPDF.
- **Production Cloud Deployment Guide:** Comprehensive operations guide in `docs/CLOUD_DEPLOYMENT.md` detailing NSSM service configuration, Task Scheduler fallback, S3 lifecycle retention rules, and hardware troubleshooting.

---

## 3. Automated Test Verification (67 Total Tests Passing)

| Component | Test Suite | Tests | Result | Duration |
|:---|:---|:---:|:---:|:---:|
| Backend Core & Auth | `backend/tests/test_auth.py` | 6 | **6 PASSED** | 0.4s |
| Document Engine | `backend/tests/test_documents.py` | 8 | **8 PASSED** | 0.3s |
| Storage Abstraction & Download | `backend/tests/test_storage.py` | 4 | **4 PASSED** | 0.2s |
| Health & Readiness | `backend/tests/test_health.py` | 3 | **3 PASSED** | 0.1s |
| Job State Machine & Safeguards | `backend/tests/test_jobs.py` | 12 | **12 PASSED** | 1.45s |
| Payment Gateway & Webhooks | `backend/tests/test_payments.py` | 9 | **9 PASSED** | 1.49s |
| Pricing Rules Engine | `backend/tests/test_pricing.py` | 4 | **4 PASSED** | 0.2s |
| Admin Operations & Agent Fleet | `backend/tests/test_admin.py` | 7 | **7 PASSED** | 0.5s |
| Windows Agent Controller | `windows-agent/tests/` | 8 | **8 PASSED** | 0.39s |
| Frontend Workflow & Config | `frontend/src/tests/` | 6 | **6 PASSED** | 2.7s |
| **Total** | | **67** | **67 PASSED (0 failures)** | |

---

## 4. Master Launch & Verification Scripts
- **Master Launch Script:** `.\run.ps1` at repository root starts backend, frontend, and windows agent in coordinated PowerShell consoles.
- **Full Setup Script:** `.\scripts\setup-all.ps1` initializes Python virtual environments, pip dependencies, npm packages, and database seeding.
- **Individual Launch Scripts:**
  - `backend/run-backend.ps1` (FastAPI on port 8000)
  - `frontend/run-frontend.ps1` (Vite on port 5173)
  - `windows-agent/run-agent.ps1` (Autonomous Spooler worker)
