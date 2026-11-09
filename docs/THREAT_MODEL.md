# PrintX Threat Model & Security Posture

## 1. System Threat Model

PrintX handles sensitive user files, financial payment records, and physical hardware control.
This document outlines threats, mitigations, and explicit security boundaries.

---

## 2. Threat Analysis & Mitigations

### 2.1 Malicious File Uploads (Exploits, Zip Bombs, Macro Injections)
- **Threat:** An attacker uploads a crafted binary disguised as a `.pdf`, a 5GB file to exhaust disk storage, or a corrupt PDF containing renderer exploits.
- **Mitigation:**
  - MIME type verification alone is rejected as insufficient.
  - Magic byte validation (`%PDF-`) is checked on the first 1024 bytes.
  - Strict upload file size limit enforced (default 50 MB, configurable via `MAX_UPLOAD_SIZE_MB`).
  - PyMuPDF structural integrity check in an isolated validation handler.
  - Encrypted / password-locked PDFs are detected and rejected before payment can occur.
  - Filenames are sanitized with UUID hashing to prevent directory traversal (`../../etc/passwd`).

### 2.2 Payment Spoofing & Frontend Tampering
- **Threat:** An attacker manipulates client-side JavaScript or sends mock payment responses to print for free.
- **Mitigation:**
  - Client-submitted prices and payment flags are **never** trusted.
  - Price calculation is strictly executed on the server based on PyMuPDF page count and server-side pricing rules.
  - Print jobs are only moved to `PAYMENT_VERIFIED` after cryptographic signature validation of the webhook or synchronous server-to-server gateway verification.
  - The Windows Print Controller performs an independent authorization check with the backend before submitting any document to the physical spooler.

### 2.3 Duplicate Print Execution & Replay Attacks
- **Threat:** Network timeouts or user double-clicking causes multiple print jobs for one payment.
- **Mitigation:**
  - Idempotency keys (`idempotency_key` UUIDs) are assigned per transaction and print job.
  - Database unique constraints prevent duplicate submissions.
  - The Windows agent tracks locally dispatched job IDs in a persistent state file.

### 2.4 Print Controller Impersonation
- **Threat:** An attacker pretends to be a Windows Print Agent to snoop on documents or intercept print jobs.
- **Mitigation:**
  - Each Print Agent possesses a unique `agent_id` and cryptographically random API secret key (`X-Agent-Secret`).
  - Agent requests are validated against registered kiosk and printer records.
  - Local controller binds strictly to loopback (`127.0.0.1`) during local development and uses authenticated HTTPS for cloud dispatch.

### 2.5 Data Retention and Privacy
- **Threat:** User PDFs left on disk forever constitute a privacy risk.
- **Mitigation:**
  - Configurable retention policy (`DOCUMENT_RETENTION_HOURS`, default 24h).
  - Background purge routine removes physical files after successful print completion or retention expiration.

