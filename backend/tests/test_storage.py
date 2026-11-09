import io
import fitz
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from app.storage.storage_provider import LocalStorageProvider, S3StorageProvider, get_storage_provider
from app.core.config import settings


def create_sample_pdf(num_pages: int = 2, title: str = "Test Doc") -> bytes:
    doc = fitz.open()
    for i in range(num_pages):
        page = doc.new_page(width=595, height=842)
        page.insert_text((50, 72), f"PrintX Storage Test - Page {i + 1}")
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def test_local_storage_provider_crud(tmp_path):
    provider = LocalStorageProvider(base_dir=tmp_path)

    content = b"%PDF-1.4 Mock document content for testing"
    filename = "assignment.pdf"

    # 1. Save file
    saved_path = provider.save_file(content, filename)
    assert Path(saved_path).exists()
    assert saved_path.endswith(".pdf")

    # 2. Get local path
    local_path = provider.get_local_path(saved_path)
    assert local_path is not None
    assert local_path.is_file()

    # 3. Get bytes
    retrieved_bytes = provider.get_file_bytes(saved_path)
    assert retrieved_bytes == content

    # 4. Download URL
    dl_url = provider.generate_download_url(saved_path, "doc-test-123")
    assert "/api/v1/documents/doc-test-123/download" in dl_url

    # 5. Delete file
    deleted = provider.delete_file(saved_path)
    assert deleted is True
    assert not Path(saved_path).exists()
    assert provider.get_local_path(saved_path) is None


def test_s3_storage_provider_simulated():
    provider = S3StorageProvider(
        bucket_name="printx-cloud-bucket",
        region="ap-south-1"
    )

    content = b"%PDF-1.4 Cloud PDF data"
    key = provider.save_file(content, "cloud_test.pdf")
    assert key.startswith("documents/")
    assert key.endswith(".pdf")

    # Local path should always be None for S3 objects
    assert provider.get_local_path(key) is None

    # Presigned URL / public fallback
    url = provider.generate_download_url(key, "doc-456")
    assert "printx-cloud-bucket" in url
    assert key in url

    # Deletion
    assert provider.delete_file(key) is True


def test_s3_storage_provider_with_boto3_mock():
    mock_boto_client = MagicMock()
    mock_boto_client.generate_presigned_url.return_value = "https://s3.ap-south-1.amazonaws.com/printx-bucket/presigned-url"
    mock_boto_client.get_object.return_value = {"Body": io.BytesIO(b"%PDF-1.4 Boto3 mock response")}

    provider = S3StorageProvider(
        bucket_name="printx-bucket",
        region="ap-south-1"
    )
    provider._client = mock_boto_client

    # Test save
    key = provider.save_file(b"%PDF-1.4 Sample", "test.pdf")
    assert mock_boto_client.put_object.called
    call_args = mock_boto_client.put_object.call_args[1]
    assert call_args["Bucket"] == "printx-bucket"
    assert call_args["ContentType"] == "application/pdf"

    # Test download URL
    url = provider.generate_download_url(key, "doc-id-789")
    assert url == "https://s3.ap-south-1.amazonaws.com/printx-bucket/presigned-url"
    mock_boto_client.generate_presigned_url.assert_called_with(
        "get_object",
        Params={"Bucket": "printx-bucket", "Key": key},
        ExpiresIn=3600
    )

    # Test get bytes
    data = provider.get_file_bytes(key)
    assert data == b"%PDF-1.4 Boto3 mock response"

    # Test delete
    assert provider.delete_file(key) is True
    mock_boto_client.delete_object.assert_called_with(Bucket="printx-bucket", Key=key)


def test_document_download_api_endpoint(client):
    sample_pdf_bytes = create_sample_pdf(num_pages=2, title="Download Test")
    # 1. Upload valid document
    files = {"file": ("download_test.pdf", sample_pdf_bytes, "application/pdf")}
    upload_res = client.post("/api/v1/documents/upload", files=files)
    assert upload_res.status_code == 201
    doc_id = upload_res.json()["document"]["id"]

    # 2. Download the document
    download_res = client.get(f"/api/v1/documents/{doc_id}/download")
    assert download_res.status_code == 200
    assert download_res.headers["content-type"] == "application/pdf"
    assert "download_test.pdf" in download_res.headers.get("content-disposition", "")
    assert download_res.content == sample_pdf_bytes

    # 3. Nonexistent document returns 404
    missing_res = client.get("/api/v1/documents/non-existent-uuid/download")
    assert missing_res.status_code == 404
