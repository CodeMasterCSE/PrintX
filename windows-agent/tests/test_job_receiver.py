import pytest
from unittest.mock import patch, MagicMock
from app.job_receiver import JobReceiver


def test_job_receiver_auth_headers():
    receiver = JobReceiver()
    headers = receiver.auth_headers
    assert "X-Agent-ID" in headers
    assert "X-Agent-Secret" in headers
    assert headers["Content-Type"] == "application/json"


def test_job_receiver_rejects_unpaid_job():
    receiver = JobReceiver()
    raw_job = {
        "id": "unpaid-123",
        "job_number": "PX-9999",
        "status": "PAYMENT_PENDING",
        "document_path": "test.pdf"
    }
    result = receiver.process_submission(raw_job)
    # Must reject jobs that are not PAYMENT_VERIFIED or QUEUED
    assert result is False


def test_job_receiver_download_remote_cloud_document(tmp_path):
    receiver = JobReceiver()
    mock_pdf_content = b"%PDF-1.4 mock pdf content"

    with patch("requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.iter_content = MagicMock(return_value=[mock_pdf_content])
        mock_get.return_value = mock_response

        downloaded_path = receiver._download_document("job-cloud-01", "https://s3.amazonaws.com/printx/test.pdf")
        assert downloaded_path is not None
        assert "job-cloud-01.pdf" in downloaded_path
