# PrintX Architecture Design Document

## 1. System Vision & Purpose

PrintX provides automated, self-service printing for students, library patrons, and office workers. 
The system bridges cloud-friendly web workflows with local, physical Windows hardware management.

### Key Tenets
1. **Zero-Touch Printing:** The user scans a QR code, uploads, pays via UPI, and receives paper output without human operator intervention.
2. **Deterministic State Machine:** A print job moves through unambiguous states: `CREATED` -> `DOCUMENT_VALIDATED` -> `PAYMENT_PENDING` -> `PAYMENT_VERIFIED` -> `QUEUED` -> `DISPATCHED` -> `SUBMITTED_TO_SPOOLER` -> `PRINTING` -> `COMPLETED`.
3. **Physical Truth Awareness:** The system differentiates between "Submitted to Windows Spooler" and true physical completion, never making deceptive claims to the user.
4. **Idempotent Execution:** Every submission carries an idempotency token preventing duplicate prints due to network retries, browser refreshes, or payment webhook duplicates.

---

## 2. Component Architecture

### A. FastAPI Backend (`backend/`)
- **FastAPI 0.110+**: High-performance asynchronous REST API framework.
- **SQLAlchemy 2.0**: Modern declarative ORM supporting both SQLite (local development) and PostgreSQL (cloud production) with UUID primary keys.
- **Pydantic V2**: Strict schema validation and serialization.
- **PyMuPDF (fitz)**: Low-level PDF parsing for page counts, color space detection, dimensions, and structural integrity.
- **Security Engine**: Passlib / bcrypt password hashing, python-jose JWT authentication, role-based access control (Student vs Admin vs Agent).

### B. React + TypeScript Frontend (`frontend/`)
- **Vite 6**: Rapid hot-module replacement and optimized asset bundling.
- **Tailwind CSS 3.4**: Responsive, utility-first design system.
- **Lucide Icons**: Crisp vector UI iconography.
- **TanStack Query (React Query)**: Robust server-state caching, automatic polling during active print states, and optimistic UI updates.
- **React Router 6**: Declarative client-side routing.
- **React Hook Form + Zod**: End-to-end type-safe form validation.

### C. Windows Print Controller (`windows-agent/`)
- **pywin32 (`win32print`, `win32ui`)**: Deep Windows 11 Spooler API access for enumerating queues, inspecting job progress, paper status, and errors.
- **SumatraPDF CLI**: Production-tested headless PDF printing engine respecting page ranges, fit-to-page, copies, and orientation without GUI dialogs.
- **Heartbeat & Queue Worker**: Secure periodic polling/websocket worker pulling authorized jobs from the backend.
- **Hardware Profile**: HP Smart Tank 585 (USB connected, A4, single-sided, color and grayscale support).

---

## 3. Print Job Lifecycle & State Transitions

```
+-----------+
|  CREATED  |
+-----+-----+
      | (Upload & inspect PDF)
      v
+----------------------+
|  DOCUMENT_VALIDATED  |
+-----+----------------+
      | (Create payment order)
      v
+--------------------+
|  PAYMENT_PENDING   |
+-----+--------------+
      | (Verified UPI webhook/callback)
      v
+--------------------+
|  PAYMENT_VERIFIED  |
+-----+--------------+
      | (Enqueue for agent)
      v
+-----------+
|  QUEUED   |
+-----+-----+
      | (Agent pulls job)
      v
+--------------+
|  DISPATCHED  |
+-----+--------+
      | (SumatraPDF passes file to Spooler)
      v
+--------------------------+
|  SUBMITTED_TO_SPOOLER    |
+-----+--------------------+
      | (Spooler reports active printing)
      v
+------------+
|  PRINTING  |
+-----+------+
      | (Job leaves spooler without error)
      v
+-------------+
|  COMPLETED  |
+-------------+
```

---

## 4. Hardware Integration: HP Smart Tank 585

- **Queue Name Mapping:** Configurable via `.env`, default matching installed Windows queue: `HP Smart Tank 580-590 series` or `HP5756E5 (HP Smart Tank 580-590 series)`.
- **Testing Driver:** `Microsoft Print to PDF` can be toggled in development to test end-to-end spooling without wasting ink and paper.
- **Duplex Policy:** Physical duplex unit is absent on this model; single-sided printing is enforced at both API and Agent levels.

---

## 5. Cloud Migration Strategy

### 5.1 Outbound Agent Security
- The Windows print controller is **never exposed directly to the public internet** (no open incoming ports).
- In cloud deployments, the Windows agent initiates an outbound, authenticated TLS connection to the cloud backend (HTTPS polling or WSS WebSocket).
- Each physical kiosk / agent holds its own cryptographically unique device credentials (`X-Agent-ID` and `X-Agent-Secret`).

### 5.2 PostgreSQL Readiness
- All SQLAlchemy entities use UUID primary keys (`String(36)`) and standard ANSI SQL column types.
- Switching from local SQLite WAL to AWS RDS / Supabase / Azure Database for PostgreSQL requires only changing `DATABASE_URL="postgresql://user:password@host:5432/printx"` in `.env`.
- Alembic database migration scripts can be run directly against the target PostgreSQL instance.

### 5.3 Cloud Object Storage
- File storage interfaces through `DocumentService`: local disk storage (`STORAGE_DIR="./uploads"`) can be swapped for S3-compatible cloud object storage (AWS S3, Cloudflare R2, MinIO) with pre-signed download URLs for agent retrieval.


