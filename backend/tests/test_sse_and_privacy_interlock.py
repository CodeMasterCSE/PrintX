import pytest
import io
from datetime import datetime, timezone, timedelta
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.document import Document, DocumentStatus
from app.models.job import PrintJob, JobStatus, PrintConfiguration, PaperSize, ColorMode
from app.models.printer import Printer, PrinterStatus
from app.models.user import User, UserRole
from app.models.payment import Payment, PaymentStatus
from app.models.audit import AuditLog
from app.services.document_service import DocumentService
from app.services.job_service import JobService
from app.storage.storage_provider import get_storage_provider
from app.core.security import hash_password, create_access_token
from app.core.events import event_broadcaster, format_sse


# --- Option B: Real-Time SSE Stream Tests ---

def test_job_sse_stream_initial_snapshot(client: TestClient, db_session: Session):
    """Verifies GET /api/v1/jobs/{job_id}/stream returns SSE event stream with initial job_update."""
    doc = DocumentService.save_document(
        db=db_session,
        file_bytes=b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 595.28 841.89]\n>>\nendobj\nxref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \ntrailer\n<<\n/Size 4\n/Root 1 0 R\n>>\nstartxref\n190\n%%EOF",
        original_filename="sse_test.pdf"
    )

    from app.schemas.job import JobCreateRequest, PrintConfigurationCreate
    req = JobCreateRequest(
        document_id=doc.id,
        idempotency_key="SSE-JOB-001",
        configuration=PrintConfigurationCreate(
            paper_size="A4",
            color_mode="grayscale",
            copies=1,
            page_range="all"
        )
    )
    job = JobService.create_job(db_session, req)

    # Stream the SSE endpoint with max_events=1
    response = client.get(f"/api/v1/jobs/{job.id}/stream?max_events=1")
    assert response.status_code == status.HTTP_200_OK
    assert "text/event-stream" in response.headers["content-type"]
    assert "event: job_update" in response.text
    assert job.job_number in response.text


def test_printer_sse_stream_initial_snapshot(client: TestClient, db_session: Session):
    """Verifies GET /api/v1/printers/stream returns SSE stream with printer_snapshot."""
    response = client.get("/api/v1/printers/stream?max_events=1")
    assert response.status_code == status.HTTP_200_OK
    assert "text/event-stream" in response.headers["content-type"]
    assert "event: printer_snapshot" in response.text


def test_format_sse():
    """Verifies SSE format helper conforms to W3C EventSource standard."""
    raw = format_sse("job_update", {"status": "PRINTING", "progress": 50})
    assert raw.startswith("event: job_update\n")
    assert '"status": "PRINTING"' in raw
    assert raw.endswith("\n\n")


# --- Option C: Automated Document Shredding & Privacy Purge Tests ---

def test_document_privacy_purge_completed_job(db_session: Session):
    """
    Verifies that documents for COMPLETED jobs past retention window
    have their binary file physically wiped from storage, Document.status set to PURGED,
    and storage_path set to [PURGED], while preserving the immutable PrintJob record.
    """
    pdf_bytes = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 595.28 841.89]\n>>\nendobj\nxref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \ntrailer\n<<\n/Size 4\n/Root 1 0 R\n>>\nstartxref\n190\n%%EOF"
    doc = DocumentService.save_document(db_session, pdf_bytes, "confidential_exam.pdf")

    # Confirm physical file exists on disk/storage before purge
    from pathlib import Path
    raw_path_before = doc.storage_path
    assert Path(raw_path_before).exists() is True

    # Create and advance a print job to COMPLETED
    from app.schemas.job import JobCreateRequest, PrintConfigurationCreate
    req = JobCreateRequest(
        document_id=doc.id,
        idempotency_key="PURGE-JOB-001",
        configuration=PrintConfigurationCreate(
            paper_size="A4",
            color_mode="grayscale",
            copies=1,
            page_range="all"
        )
    )
    job = JobService.create_job(db_session, req)
    JobService.transition_status(db_session, job, JobStatus.PAYMENT_VERIFIED)
    JobService.transition_status(db_session, job, JobStatus.QUEUED)
    JobService.transition_status(db_session, job, JobStatus.DISPATCHED)
    JobService.transition_status(db_session, job, JobStatus.SUBMITTED_TO_SPOOLER)
    JobService.transition_status(db_session, job, JobStatus.COMPLETED)

    # Artificially set job updated_at to 20 minutes ago (retention window is 15 minutes)
    twenty_min_ago = datetime.now(timezone.utc) - timedelta(minutes=20)
    job.updated_at = twenty_min_ago
    db_session.commit()

    # Execute privacy purge
    result = DocumentService.purge_expired_documents(db_session, retention_minutes=15)
    assert result["purged_count"] >= 1
    assert result["freed_bytes"] > 0

    # Verify physical file was shredded
    db_session.refresh(doc)
    assert doc.status == DocumentStatus.PURGED
    assert doc.storage_path == "[PURGED]"
    assert Path(raw_path_before).exists() is False

    # Verify PrintJob immutable financial receipt is still 100% intact!
    db_session.refresh(job)
    assert job.status == JobStatus.COMPLETED
    assert job.job_number is not None
    assert job.price == 2.0


def test_purged_document_preview_and_download_return_410_gone(client: TestClient, db_session: Session):
    """Verifies that attempting to download or preview a purged document yields HTTP 410 Gone."""
    pdf_bytes = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 595.28 841.89]\n>>\nendobj\nxref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \ntrailer\n<<\n/Size 4\n/Root 1 0 R\n>>\nstartxref\n190\n%%EOF"
    doc = DocumentService.save_document(db_session, pdf_bytes, "wipe_test.pdf")

    # Mark document as purged
    doc.status = DocumentStatus.PURGED
    doc.storage_path = "[PURGED]"
    db_session.commit()

    # Attempt preview
    prev_resp = client.get(f"/api/v1/documents/{doc.id}/preview")
    assert prev_resp.status_code == status.HTTP_410_GONE
    assert "purged" in prev_resp.json()["detail"].lower()

    # Attempt download
    down_resp = client.get(f"/api/v1/documents/{doc.id}/download")
    assert down_resp.status_code == status.HTTP_410_GONE
    assert "purged" in down_resp.json()["detail"].lower()


def test_admin_manual_document_purge_endpoint(client: TestClient, db_session: Session):
    """Verifies POST /api/v1/admin/documents/purge executes shredding and logs an AuditLog."""
    admin = db_session.query(User).filter(User.role == UserRole.ADMIN).first()
    token = create_access_token(admin.id, role=admin.role.value)
    headers = {"Authorization": f"Bearer {token}"}

    # Upload and complete a job
    pdf_bytes = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 595.28 841.89]\n>>\nendobj\nxref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \ntrailer\n<<\n/Size 4\n/Root 1 0 R\n>>\nstartxref\n190\n%%EOF"
    doc = DocumentService.save_document(db_session, pdf_bytes, "admin_shred.pdf")

    from app.schemas.job import JobCreateRequest, PrintConfigurationCreate
    req = JobCreateRequest(
        document_id=doc.id,
        idempotency_key="ADMIN-SHRED-001",
        configuration=PrintConfigurationCreate(
            paper_size="A4",
            color_mode="grayscale",
            copies=1,
            page_range="all"
        )
    )
    job = JobService.create_job(db_session, req)
    JobService.transition_status(db_session, job, JobStatus.PAYMENT_VERIFIED)
    JobService.transition_status(db_session, job, JobStatus.QUEUED)
    JobService.transition_status(db_session, job, JobStatus.DISPATCHED)
    JobService.transition_status(db_session, job, JobStatus.SUBMITTED_TO_SPOOLER)
    JobService.transition_status(db_session, job, JobStatus.COMPLETED)
    job.updated_at = datetime.now(timezone.utc) - timedelta(minutes=30)
    db_session.commit()

    resp = client.post(
        "/api/v1/admin/documents/purge",
        json={"retention_minutes": 15, "unprinted_expiry_hours": 24},
        headers=headers
    )
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert data["purged_count"] >= 1
    assert "Privacy purge complete" in data["message"]

    # Verify audit log was written
    audit = db_session.query(AuditLog).filter(AuditLog.action == "DOCUMENT_PRIVACY_PURGE").first()
    assert audit is not None


# --- Option C: Real-Time Paper-Out Hardware Interlock Tests ---

def test_paper_out_blocks_payment_checkout(client: TestClient, db_session: Session):
    """
    Verifies that when a printer's status is 'out_of_paper', payment order creation
    is blocked with HTTP 400 and an informative error message to prevent lost funds.
    """
    # Find target printer and set status to 'out_of_paper'
    printer = db_session.query(Printer).filter(Printer.is_default == True).first()
    assert printer is not None
    printer.status = "out_of_paper"
    db_session.commit()

    # Create a job
    pdf_bytes = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 595.28 841.89]\n>>\nendobj\nxref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \ntrailer\n<<\n/Size 4\n/Root 1 0 R\n>>\nstartxref\n190\n%%EOF"
    doc = DocumentService.save_document(db_session, pdf_bytes, "interlock_test.pdf")

    from app.schemas.job import JobCreateRequest, PrintConfigurationCreate
    req = JobCreateRequest(
        document_id=doc.id,
        idempotency_key="INTERLOCK-JOB-001",
        printer_id=printer.id,
        configuration=PrintConfigurationCreate(
            paper_size="A4",
            color_mode="grayscale",
            copies=1,
            page_range="all"
        )
    )
    job = JobService.create_job(db_session, req)

    # Attempt to create payment order
    resp = client.post("/api/v1/payments/create", json={
        "job_id": job.id,
        "amount": job.price,
        "provider": "mock_upi",
        "idempotency_key": f"PAY-{job.id}"
    })

    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert "out of paper" in resp.json()["detail"].lower()


def test_offline_printer_blocks_payment_checkout(client: TestClient, db_session: Session):
    """Verifies that when a printer is offline, payment creation is blocked."""
    printer = db_session.query(Printer).filter(Printer.is_default == True).first()
    assert printer is not None
    printer.is_online = False
    printer.status = "offline"
    db_session.commit()

    pdf_bytes = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 595.28 841.89]\n>>\nendobj\nxref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \ntrailer\n<<\n/Size 4\n/Root 1 0 R\n>>\nstartxref\n190\n%%EOF"
    doc = DocumentService.save_document(db_session, pdf_bytes, "offline_test.pdf")

    from app.schemas.job import JobCreateRequest, PrintConfigurationCreate
    req = JobCreateRequest(
        document_id=doc.id,
        idempotency_key="OFFLINE-JOB-001",
        printer_id=printer.id,
        configuration=PrintConfigurationCreate(
            paper_size="A4",
            color_mode="grayscale",
            copies=1,
            page_range="all"
        )
    )
    job = JobService.create_job(db_session, req)

    resp = client.post("/api/v1/payments/create", json={
        "job_id": job.id,
        "amount": job.price,
        "provider": "mock_upi",
        "idempotency_key": f"PAY-OFFLINE-{job.id}"
    })

    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert "offline" in resp.json()["detail"].lower()


def test_printer_status_update_endpoint(client: TestClient, db_session: Session):
    """Verifies POST /api/v1/printers/{id}/status updates hardware status and restores checkout."""
    printer = db_session.query(Printer).filter(Printer.is_default == True).first()
    assert printer is not None

    # Update to out_of_paper
    resp = client.post(f"/api/v1/printers/{printer.id}/status", json={
        "status": "out_of_paper",
        "status_details": "Tray 1 empty"
    })
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["status"] == "out_of_paper"

    # Restore to online
    resp = client.post(f"/api/v1/printers/{printer.id}/status", json={
        "status": "online",
        "status_details": "Ready",
        "is_online": True
    })
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["status"] == "online"
    assert resp.json()["is_online"] is True
