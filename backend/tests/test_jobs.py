import pytest
from datetime import datetime, timezone, timedelta
from app.models.job import JobStatus, PrintJob, JobEvent
from tests.test_documents import create_sample_pdf
from app.core.config import settings
from app.services.job_service import JobService


def upload_test_doc(client):
    pdf_bytes = create_sample_pdf(num_pages=2, title="Job Test Document")
    files = {"file": ("job_doc.pdf", pdf_bytes, "application/pdf")}
    res = client.post("/api/v1/documents/upload", files=files)
    return res.json()["document"]["id"]


def test_create_print_job(client):
    doc_id = upload_test_doc(client)
    payload = {
        "document_id": doc_id,
        "configuration": {
            "paper_size": "A4",
            "color_mode": "grayscale",
            "copies": 1,
            "page_range": "all",
            "fit_to_page": True,
            "duplex": False
        },
        "idempotency_key": "job-idemp-001"
    }
    response = client.post("/api/v1/jobs", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "PAYMENT_PENDING"
    assert data["job_number"].startswith("PX-")
    # 2 pages @ ₹2.00 = ₹4.00
    assert data["price"] == 4.0
    assert data["total_pages"] == 2


def test_create_job_idempotency(client):
    doc_id = upload_test_doc(client)
    payload = {
        "document_id": doc_id,
        "configuration": {
            "paper_size": "A4",
            "color_mode": "grayscale",
            "copies": 1,
            "page_range": "all",
            "fit_to_page": True,
            "duplex": False
        },
        "idempotency_key": "job-idemp-duplicate-check"
    }
    res1 = client.post("/api/v1/jobs", json=payload)
    assert res1.status_code == 201
    job1_id = res1.json()["id"]

    res2 = client.post("/api/v1/jobs", json=payload)
    assert res2.status_code == 201
    job2_id = res2.json()["id"]

    assert job1_id == job2_id


def test_cancel_job_before_dispatch(client):
    doc_id = upload_test_doc(client)
    payload = {
        "document_id": doc_id,
        "configuration": {
            "paper_size": "A4",
            "color_mode": "grayscale",
            "copies": 1,
            "page_range": "all",
            "fit_to_page": True,
            "duplex": False
        },
        "idempotency_key": "job-idemp-cancel-01"
    }
    create_res = client.post("/api/v1/jobs", json=payload)
    job_id = create_res.json()["id"]

    cancel_res = client.post(f"/api/v1/jobs/{job_id}/cancel")
    assert cancel_res.status_code == 200
    assert cancel_res.json()["status"] == "CANCELLED"


def test_agent_pull_job_requires_payment(client):
    doc_id = upload_test_doc(client)
    payload = {
        "document_id": doc_id,
        "configuration": {
            "paper_size": "A4",
            "color_mode": "grayscale",
            "copies": 1,
            "page_range": "all",
            "fit_to_page": True,
            "duplex": False
        },
        "idempotency_key": "job-unpaid-pull"
    }
    client.post("/api/v1/jobs", json=payload)

    # Agent polls for jobs with valid auth headers
    headers = {
        "X-Agent-ID": "AGENT-WIN11-01",
        "X-Agent-Secret": settings.AGENT_SECRET_KEY
    }
    pull_res = client.post("/api/v1/jobs/agent/pull", headers=headers)
    assert pull_res.status_code == 200
    # Because job is still in PAYMENT_PENDING, agent MUST NOT receive it
    assert pull_res.json()["job"] is None


def test_agent_endpoint_rejects_unauthorized_call(client):
    # Attempting to pull without agent headers must yield 401
    res = client.post("/api/v1/jobs/agent/pull")
    assert res.status_code == 401


def test_job_full_state_machine_lifecycle(client, db_session):
    doc_id = upload_test_doc(client)
    payload = {
        "document_id": doc_id,
        "configuration": {
            "paper_size": "A4",
            "color_mode": "grayscale",
            "copies": 1,
            "page_range": "all",
            "fit_to_page": True,
            "duplex": False
        },
        "idempotency_key": "lifecycle-test-01"
    }
    create_res = client.post("/api/v1/jobs", json=payload)
    job_id = create_res.json()["id"]

    headers = {
        "X-Agent-ID": "AGENT-WIN11-01",
        "X-Agent-Secret": settings.AGENT_SECRET_KEY
    }

    # Simulate payment verification
    job = db_session.query(PrintJob).filter(PrintJob.id == job_id).first()
    JobService.transition_status(db_session, job, JobStatus.PAYMENT_VERIFIED, "Payment verified")
    JobService.transition_status(db_session, job, JobStatus.QUEUED, "Enqueued for agent")

    # Agent updates to DISPATCHED
    res1 = client.patch(f"/api/v1/jobs/{job_id}/status", json={"status": "DISPATCHED"}, headers=headers)
    assert res1.status_code == 200
    assert res1.json()["status"] == "DISPATCHED"

    # Agent updates to SUBMITTED_TO_SPOOLER
    res2 = client.patch(
        f"/api/v1/jobs/{job_id}/status",
        json={"status": "SUBMITTED_TO_SPOOLER", "spooler_job_id": 42},
        headers=headers
    )
    assert res2.status_code == 200
    assert res2.json()["status"] == "SUBMITTED_TO_SPOOLER"
    assert res2.json()["spooler_job_id"] == 42

    # Agent updates to PRINTING
    res3 = client.patch(f"/api/v1/jobs/{job_id}/status", json={"status": "PRINTING"}, headers=headers)
    assert res3.status_code == 200
    assert res3.json()["status"] == "PRINTING"

    # Agent updates to COMPLETED
    res4 = client.patch(f"/api/v1/jobs/{job_id}/status", json={"status": "COMPLETED"}, headers=headers)
    assert res4.status_code == 200
    assert res4.json()["status"] == "COMPLETED"

    # Verify audit timeline
    job_detail = client.get(f"/api/v1/jobs/{job_id}").json()
    events = job_detail.get("events", [])
    assert len(events) >= 5
    statuses = [e["new_status"] for e in events]
    assert "QUEUED" in statuses
    assert "DISPATCHED" in statuses
    assert "SUBMITTED_TO_SPOOLER" in statuses
    assert "COMPLETED" in statuses


def test_cannot_cancel_job_once_submitted_to_spooler(client, db_session):
    doc_id = upload_test_doc(client)
    payload = {
        "document_id": doc_id,
        "configuration": {
            "paper_size": "A4",
            "color_mode": "grayscale",
            "copies": 1,
            "page_range": "all",
            "fit_to_page": True,
            "duplex": False
        },
        "idempotency_key": "cancel-spooler-test"
    }
    create_res = client.post("/api/v1/jobs", json=payload)
    job_id = create_res.json()["id"]

    job = db_session.query(PrintJob).filter(PrintJob.id == job_id).first()
    JobService.transition_status(db_session, job, JobStatus.PAYMENT_VERIFIED)
    JobService.transition_status(db_session, job, JobStatus.QUEUED)
    JobService.transition_status(db_session, job, JobStatus.DISPATCHED)
    JobService.transition_status(db_session, job, JobStatus.SUBMITTED_TO_SPOOLER)

    # Attempt cancellation when paper is already in mechanical transit
    cancel_res = client.post(f"/api/v1/jobs/{job_id}/cancel")
    assert cancel_res.status_code == 400
    assert "Paper is already in transit" in cancel_res.json()["detail"]


def test_safe_retry_pre_spooler_failure(client, db_session):
    doc_id = upload_test_doc(client)
    payload = {
        "document_id": doc_id,
        "configuration": {
            "paper_size": "A4",
            "color_mode": "grayscale",
            "copies": 1,
            "page_range": "all",
            "fit_to_page": True,
            "duplex": False
        },
        "idempotency_key": "pre-spooler-fail-retry"
    }
    create_res = client.post("/api/v1/jobs", json=payload)
    job_id = create_res.json()["id"]

    job = db_session.query(PrintJob).filter(PrintJob.id == job_id).first()
    JobService.transition_status(db_session, job, JobStatus.PAYMENT_VERIFIED)
    JobService.transition_status(db_session, job, JobStatus.QUEUED)
    JobService.transition_status(db_session, job, JobStatus.DISPATCHED)
    # Fail before spooler (e.g. network dropped)
    JobService.transition_status(db_session, job, JobStatus.FAILED, error_message="Network dropped")

    # Safe retry without force_retry must succeed because paper was never in spooler
    retry_res = client.post(f"/api/v1/jobs/{job_id}/retry")
    assert retry_res.status_code == 200
    assert retry_res.json()["status"] == "QUEUED"


def test_duplicate_safeguard_post_spooler_failure(client, db_session):
    doc_id = upload_test_doc(client)
    payload = {
        "document_id": doc_id,
        "configuration": {
            "paper_size": "A4",
            "color_mode": "grayscale",
            "copies": 1,
            "page_range": "all",
            "fit_to_page": True,
            "duplex": False
        },
        "idempotency_key": "post-spooler-fail-retry"
    }
    create_res = client.post("/api/v1/jobs", json=payload)
    job_id = create_res.json()["id"]

    job = db_session.query(PrintJob).filter(PrintJob.id == job_id).first()
    JobService.transition_status(db_session, job, JobStatus.PAYMENT_VERIFIED)
    JobService.transition_status(db_session, job, JobStatus.QUEUED)
    JobService.transition_status(db_session, job, JobStatus.DISPATCHED)
    JobService.transition_status(db_session, job, JobStatus.SUBMITTED_TO_SPOOLER)
    JobService.transition_status(db_session, job, JobStatus.FAILED, error_message="Paper jam reported")

    # 1. Blind retry must be REJECTED by duplicate print safeguard
    blind_retry = client.post(f"/api/v1/jobs/{job_id}/retry")
    assert blind_retry.status_code == 400
    assert "DUPLICATE PRINT SAFEGUARD" in blind_retry.json()["detail"]

    # 2. Operator verified forced retry succeeds
    forced_retry = client.post(
        f"/api/v1/jobs/{job_id}/retry",
        json={"force_retry": True, "operator_notes": "Verified tray is clear of paper."}
    )
    assert forced_retry.status_code == 200
    assert forced_retry.json()["status"] == "QUEUED"
    assert "retry-" in forced_retry.json()["idempotency_key"]


def test_queue_position_and_wait_calculation(client, db_session):
    doc_id = upload_test_doc(client)
    payload1 = {
        "document_id": doc_id,
        "configuration": {
            "paper_size": "A4",
            "color_mode": "grayscale",
            "copies": 1,
            "page_range": "all",
            "fit_to_page": True,
            "duplex": False
        },
        "idempotency_key": "queue-pos-01"
    }
    job1_res = client.post("/api/v1/jobs", json=payload1).json()
    job1 = db_session.query(PrintJob).filter(PrintJob.id == job1_res["id"]).first()
    JobService.transition_status(db_session, job1, JobStatus.PAYMENT_VERIFIED)
    JobService.transition_status(db_session, job1, JobStatus.QUEUED)

    payload2 = {
        "document_id": doc_id,
        "configuration": {
            "paper_size": "A4",
            "color_mode": "grayscale",
            "copies": 2,
            "page_range": "all",
            "fit_to_page": True,
            "duplex": False
        },
        "idempotency_key": "queue-pos-02"
    }
    job2_res = client.post("/api/v1/jobs", json=payload2).json()
    job2 = db_session.query(PrintJob).filter(PrintJob.id == job2_res["id"]).first()
    JobService.transition_status(db_session, job2, JobStatus.PAYMENT_VERIFIED)
    JobService.transition_status(db_session, job2, JobStatus.QUEUED)

    # Check queue positions
    job1_check = client.get(f"/api/v1/jobs/{job1.id}").json()
    job2_check = client.get(f"/api/v1/jobs/{job2.id}").json()

    assert job1_check["queue_position"] == 1
    assert job2_check["queue_position"] == 2
    assert job2_check["estimated_wait_seconds"] >= job1_check["estimated_wait_seconds"]


def test_crash_recovery_reconciliation(client, db_session):
    doc_id = upload_test_doc(client)
    payload = {
        "document_id": doc_id,
        "configuration": {
            "paper_size": "A4",
            "color_mode": "grayscale",
            "copies": 1,
            "page_range": "all",
            "fit_to_page": True,
            "duplex": False
        },
        "idempotency_key": "crash-recovery-job"
    }
    res = client.post("/api/v1/jobs", json=payload).json()
    job = db_session.query(PrintJob).filter(PrintJob.id == res["id"]).first()
    JobService.transition_status(db_session, job, JobStatus.PAYMENT_VERIFIED)
    JobService.transition_status(db_session, job, JobStatus.QUEUED)
    JobService.transition_status(db_session, job, JobStatus.DISPATCHED)

    # Set updated_at to 10 minutes ago
    job.updated_at = datetime.now(timezone.utc) - timedelta(minutes=10)
    db_session.commit()

    # Trigger reconciliation
    rec_res = client.post("/api/v1/jobs/reconcile", params={"dispatched_timeout_seconds": 60})
    assert rec_res.status_code == 200
    rec_data = rec_res.json()
    assert rec_data["recovered_dispatched"] >= 1

    # Verify job is now marked FAILED
    updated_job = client.get(f"/api/v1/jobs/{job.id}").json()
    assert updated_job["status"] == "FAILED"
    assert "Crash recovery" in updated_job["error_message"] or "timeout" in updated_job["error_message"]


def test_search_and_filter_jobs(client):
    doc_id = upload_test_doc(client)
    key = "unique-search-key-999"
    payload = {
        "document_id": doc_id,
        "configuration": {
            "paper_size": "A4",
            "color_mode": "grayscale",
            "copies": 1,
            "page_range": "all",
            "fit_to_page": True,
            "duplex": False
        },
        "idempotency_key": key
    }
    created = client.post("/api/v1/jobs", json=payload).json()

    # Search by key
    search_res = client.get(f"/api/v1/jobs?search={key}").json()
    assert len(search_res) == 1
    assert search_res[0]["id"] == created["id"]
