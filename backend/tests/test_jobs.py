import pytest
from app.models.job import JobStatus
from tests.test_documents import create_sample_pdf
from app.core.config import settings


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
