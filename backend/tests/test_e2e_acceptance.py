import io
import fitz
import pytest
from app.models.printer import Printer
from app.models.pricing import PricingRule
from app.models.job import PrintJob
from app.models.agent import PrintAgent
from app.core.security import hash_password
from app.core.config import settings


def create_sample_pdf(num_pages: int = 3, title: str = "Acceptance Test") -> bytes:
    doc = fitz.open()
    for i in range(num_pages):
        page = doc.new_page(width=595, height=842)
        page.insert_text((50, 72), f"PrintX Acceptance Criteria Test - Page {i + 1}")
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def test_full_system_acceptance_criteria_workflow(client, db_session):
    """
    Validates Section 14 Acceptance Criteria end-to-end:
    1. Upload valid PDF -> verify page count.
    2. Configure single-sided (simplex), color/grayscale, copies, and custom page range.
    3. Authoritative server-side pricing engine calculates cost.
    4. Payment order generation with UPI QR.
    5. Security: Unpaid / unauthorized requests cannot pull job.
    6. Verified payment triggers queueing.
    7. Windows Print Agent pulls authorized job and reports lifecycle transitions.
    8. Receipt retrieval with immutable audit reference.
    9. Safeguards: Duplicate webhooks and reprints are blocked.
    """

    # --- STEP 1: Verify Hardware Printer & Baseline Seeding ---
    hp_printer = db_session.query(Printer).filter(Printer.name == "HP Smart Tank 580-590 series").first()
    assert hp_printer is not None
    assert hp_printer.is_online is True

    rule = db_session.query(PricingRule).filter(PricingRule.is_active == True).first()
    assert rule is not None
    assert rule.per_page_bw == 2.0
    assert rule.per_page_color == 10.0

    # Ensure Agent is registered in database
    agent_id = "AGENT-WIN11-TEST01"
    raw_secret = "px_sec_acceptance_test_secret_123"
    test_agent = PrintAgent(
        agent_id=agent_id,
        name="Acceptance Test Agent",
        secret_hash=hash_password(raw_secret),
        is_active=True
    )
    db_session.add(test_agent)
    db_session.commit()

    agent_headers = {
        "X-Agent-ID": agent_id,
        "X-Agent-Secret": raw_secret
    }

    # --- STEP 2: Document Upload & PyMuPDF Inspection ---
    pdf_bytes = create_sample_pdf(num_pages=3, title="Thesis Chapter 1")
    upload_res = client.post(
        "/api/v1/documents/upload",
        files={"file": ("thesis_ch1.pdf", pdf_bytes, "application/pdf")}
    )
    assert upload_res.status_code == 201
    doc_data = upload_res.json()["document"]
    doc_id = doc_data["id"]
    assert doc_data["page_count"] == 3
    assert doc_data["file_size_bytes"] > 0
    assert doc_data["mime_type"] == "application/pdf"

    # --- STEP 3: Configure Printing & Create Job ---
    # Custom range: pages 1-2 (2 pages) * 2 copies = 4 printable pages
    # Mode: Grayscale (₹2.00/page) -> Total = ₹8.00
    job_payload = {
        "document_id": doc_id,
        "configuration": {
            "paper_size": "A4",
            "color_mode": "grayscale",
            "copies": 2,
            "page_range": "1-2",
            "fit_to_page": True,
            "duplex": False  # Strict simplex enforcement for HP Smart Tank 585
        },
        "idempotency_key": "job-acceptance-e2e-001"
    }
    create_job_res = client.post("/api/v1/jobs", json=job_payload)
    assert create_job_res.status_code == 201
    job = create_job_res.json()
    job_id = job["id"]
    assert job["total_pages"] == 2
    assert job["sheets_used"] == 4
    assert job["price"] == 8.00
    assert job["status"] == "PAYMENT_PENDING"

    # --- STEP 4: Initiate Payment Order ---
    pay_res = client.post("/api/v1/payments/create", json={
        "job_id": job_id,
        "amount": 8.00,
        "provider": "mock_upi",
        "idempotency_key": "pay-acceptance-e2e-001"
    })
    assert pay_res.status_code == 201
    pay_data = pay_res.json()
    order_id = pay_data["order_id"]
    payment_id = pay_data["id"]
    assert pay_data["status"] == "pending"
    assert "upi://pay?" in pay_data["upi_qr_data"]

    # --- STEP 5: Security Guard — Unpaid Job Cannot Be Pulled ---
    agent_pull_res = client.post("/api/v1/jobs/agent/pull", headers=agent_headers)
    assert agent_pull_res.status_code == 200
    assert agent_pull_res.json()["job"] is None

    # Unauthorized agent request must be rejected
    unauth_pull = client.post(
        "/api/v1/jobs/agent/pull",
        headers={"X-Agent-ID": "UNKNOWN", "X-Agent-Secret": "BAD"}
    )
    assert unauth_pull.status_code in [401, 403]

    # --- STEP 6: Verified UPI Payment Webhook ---
    webhook_res = client.post(
        "/api/v1/payments/webhook",
        json={
            "order_id": order_id,
            "gateway_transaction_id": "UPI-ACCEPT-99887766",
            "status": "verified",
            "signature": "mock-verified-signature"
        }
    )
    assert webhook_res.status_code == 200
    assert webhook_res.json()["status"] == "verified"

    # Verify job transitioned to QUEUED
    status_res = client.get(f"/api/v1/jobs/{job_id}")
    assert status_res.status_code == 200
    assert status_res.json()["status"] == "QUEUED"

    # Duplicate webhook must be idempotent
    dup_webhook = client.post(
        "/api/v1/payments/webhook",
        json={
            "order_id": order_id,
            "gateway_transaction_id": "UPI-ACCEPT-99887766",
            "status": "verified",
            "signature": "mock-verified-signature"
        }
    )
    assert dup_webhook.status_code == 200

    # --- STEP 7: Windows Agent Pulls Job & Executes Spooler Lifecycle ---
    agent_pull_res2 = client.post("/api/v1/jobs/agent/pull", headers=agent_headers)
    assert agent_pull_res2.status_code == 200
    pulled_job = agent_pull_res2.json()["job"]
    assert pulled_job is not None
    assert pulled_job["id"] == job_id
    assert pulled_job["configuration"]["duplex"] is False  # Simplex verified

    # Transition 1: SUBMITTED_TO_SPOOLER
    spooler_update = client.patch(
        f"/api/v1/jobs/{job_id}/status",
        json={
            "status": "SUBMITTED_TO_SPOOLER",
            "spooler_job_id": 1042,
            "message": "Passed to HP Smart Tank 580-590 series queue"
        },
        headers=agent_headers
    )
    assert spooler_update.status_code == 200
    assert spooler_update.json()["status"] == "SUBMITTED_TO_SPOOLER"

    # Transition 2: PRINTING
    printing_update = client.patch(
        f"/api/v1/jobs/{job_id}/status",
        json={
            "status": "PRINTING",
            "spooler_job_id": 1042,
            "message": "Printer hardware actively rendering page 1 of 4"
        },
        headers=agent_headers
    )
    assert printing_update.status_code == 200
    assert printing_update.json()["status"] == "PRINTING"

    # Transition 3: COMPLETED
    completed_update = client.patch(
        f"/api/v1/jobs/{job_id}/status",
        json={
            "status": "COMPLETED",
            "spooler_job_id": 1042,
            "message": "Paper successfully ejected into output tray"
        },
        headers=agent_headers
    )
    assert completed_update.status_code == 200
    assert completed_update.json()["status"] == "COMPLETED"

    # --- STEP 8: Official Digital Receipt Verification ---
    receipt_res = client.get(f"/api/v1/jobs/{job_id}/receipt")
    assert receipt_res.status_code == 200
    receipt = receipt_res.json()
    assert receipt["job_id"] == job_id
    assert receipt["total_price"] == 8.00
    assert receipt["pages_count"] == 2  # custom page range 1-2 has 2 pages
    assert receipt["copies"] == 2
    assert receipt["printing_mode"] == "grayscale"
    assert receipt["status"] == "COMPLETED"
    assert receipt["transaction_reference"] == "UPI-ACCEPT-99887766"

    # --- STEP 9: Safeguards Against Duplicate Prints & Illegal Refunds ---
    # Attempting to pull jobs again yields nothing
    empty_pull = client.post("/api/v1/jobs/agent/pull", headers=agent_headers)
    assert empty_pull.json()["job"] is None

    # Attempting to refund a physically printed completed job must fail
    refund_res = client.post(
        f"/api/v1/payments/{order_id}/refund",
        json={"reason": "User Changed Mind"}
    )
    assert refund_res.status_code == 400
    assert "Cannot refund a completed print job" in refund_res.json()["detail"]
