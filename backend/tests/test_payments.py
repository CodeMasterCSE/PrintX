import pytest
from tests.test_documents import create_sample_pdf


def setup_test_job(client, num_pages: int = 3, copies: int = 1, color_mode: str = "grayscale"):
    pdf_bytes = create_sample_pdf(num_pages=num_pages, title="Payment Test Doc")
    files = {"file": ("pay_doc.pdf", pdf_bytes, "application/pdf")}
    upload_res = client.post("/api/v1/documents/upload", files=files)
    doc_id = upload_res.json()["document"]["id"]

    job_res = client.post("/api/v1/jobs", json={
        "document_id": doc_id,
        "configuration": {
            "paper_size": "A4",
            "color_mode": color_mode,
            "copies": copies,
            "page_range": "all",
            "fit_to_page": True,
            "duplex": False
        },
        "idempotency_key": f"pay-job-idemp-{doc_id}"
    })
    return job_res.json()


def test_create_payment_order(client):
    job = setup_test_job(client, num_pages=2, copies=1, color_mode="grayscale")
    # 2 pages * ₹2.00 = ₹4.00
    expected_price = 4.0

    payload = {
        "job_id": job["id"],
        "amount": expected_price,
        "provider": "mock_upi",
        "idempotency_key": "pay-order-001"
    }
    response = client.post("/api/v1/payments/create", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "pending"
    assert data["amount"] == expected_price
    assert data["provider"] == "mock_upi"
    assert "upi://pay?" in data["upi_qr_data"]
    assert "am=4.00" in data["upi_qr_data"]


def test_reject_client_side_price_tampering(client):
    job = setup_test_job(client, num_pages=5, copies=1, color_mode="grayscale")
    # Correct price is ₹10.00. Malicious client attempts to pay ₹1.00:
    tampered_payload = {
        "job_id": job["id"],
        "amount": 1.00,
        "provider": "mock_upi",
        "idempotency_key": "tampered-pay-01"
    }
    response = client.post("/api/v1/payments/create", json=tampered_payload)
    assert response.status_code == 400
    assert "Amount mismatch" in response.json()["detail"]


def test_payment_webhook_verification_enqueues_job(client):
    job = setup_test_job(client, num_pages=2, copies=1, color_mode="grayscale")
    pay_res = client.post("/api/v1/payments/create", json={
        "job_id": job["id"],
        "amount": 4.0,
        "provider": "mock_upi",
        "idempotency_key": f"pay-verify-{job['id']}"
    })
    order_id = pay_res.json()["order_id"]

    # Trigger verified webhook
    webhook_payload = {
        "order_id": order_id,
        "gateway_transaction_id": "UPI-GATEWAY-TX-998877",
        "status": "verified",
        "signature": "mock-verified-signature"
    }
    webhook_res = client.post("/api/v1/payments/webhook", json=webhook_payload)
    assert webhook_res.status_code == 200
    assert webhook_res.json()["status"] == "verified"

    # Verify that associated PrintJob is now QUEUED
    job_res = client.get(f"/api/v1/jobs/{job['id']}")
    assert job_res.status_code == 200
    assert job_res.json()["status"] == "QUEUED"


def test_duplicate_webhook_idempotency(client):
    job = setup_test_job(client, num_pages=1, copies=1, color_mode="grayscale")
    pay_res = client.post("/api/v1/payments/create", json={
        "job_id": job["id"],
        "amount": 2.0,
        "provider": "mock_upi",
        "idempotency_key": f"pay-dup-{job['id']}"
    })
    order_id = pay_res.json()["order_id"]

    webhook_payload = {
        "order_id": order_id,
        "gateway_transaction_id": "TX-1",
        "status": "verified",
        "signature": "mock-verified-signature"
    }
    # First callback
    res1 = client.post("/api/v1/payments/webhook", json=webhook_payload)
    assert res1.status_code == 200

    # Duplicate callback
    res2 = client.post("/api/v1/payments/webhook", json=webhook_payload)
    assert res2.status_code == 200
    assert res2.json()["status"] == "verified"
