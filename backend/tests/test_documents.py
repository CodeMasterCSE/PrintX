import io
import fitz
import pytest
from app.models.document import Document


def create_sample_pdf(num_pages: int = 2, title: str = "Test Doc") -> bytes:
    """Creates a valid in-memory PDF with the specified number of pages."""
    doc = fitz.open()
    for i in range(num_pages):
        page = doc.new_page(width=595, height=842)  # Standard A4 dimensions
        text = f"PrintX Test Document - Page {i + 1}\nTitle: {title}"
        page.insert_text((50, 72), text, fontsize=14)
    doc.set_metadata({"title": title, "author": "PrintX Test Harness"})
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def create_encrypted_pdf() -> bytes:
    """Creates a password-protected PDF for encryption testing."""
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    page.insert_text((50, 72), "Confidential locked file", fontsize=14)
    perm = int(
        fitz.PDF_PERM_ACCESSIBILITY
        | fitz.PDF_PERM_PRINT
        | fitz.PDF_PERM_COPY
        | fitz.PDF_PERM_ANNOTATE
    )
    pdf_bytes = doc.tobytes(
        encryption=fitz.PDF_ENCRYPT_AES_256,
        user_pw="printx_secret",
        owner_pw="printx_master",
        permissions=perm,
    )
    doc.close()
    return pdf_bytes


def test_upload_valid_pdf(client):
    pdf_bytes = create_sample_pdf(num_pages=3, title="Lecture Notes")
    files = {"file": ("notes.pdf", pdf_bytes, "application/pdf")}
    
    response = client.post("/api/v1/documents/upload", files=files)
    assert response.status_code == 201
    data = response.json()
    assert "document" in data
    doc = data["document"]
    assert doc["original_filename"] == "notes.pdf"
    assert doc["page_count"] == 3
    assert doc["file_size_bytes"] == len(pdf_bytes)
    assert doc["is_encrypted"] is False
    assert len(doc["sha256_checksum"]) == 64
    assert "ready for printing" in data["message"]


def test_get_document_details(client):
    # 1. Upload
    pdf_bytes = create_sample_pdf(num_pages=1, title="Syllabus")
    files = {"file": ("syllabus.pdf", pdf_bytes, "application/pdf")}
    upload_res = client.post("/api/v1/documents/upload", files=files)
    doc_id = upload_res.json()["document"]["id"]

    # 2. Retrieve
    response = client.get(f"/api/v1/documents/{doc_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == doc_id
    assert data["page_count"] == 1
    assert data["original_filename"] == "syllabus.pdf"


def test_get_document_preview(client):
    pdf_bytes = create_sample_pdf(num_pages=2, title="Assignment")
    files = {"file": ("assignment.pdf", pdf_bytes, "application/pdf")}
    upload_res = client.post("/api/v1/documents/upload", files=files)
    doc_id = upload_res.json()["document"]["id"]

    # Request PNG preview of page 1
    response = client.get(f"/api/v1/documents/{doc_id}/preview?page=1")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    # Verify PNG magic signature bytes: \x89PNG\r\n\x1a\n
    assert response.content.startswith(b"\x89PNG\r\n\x1a\n")


def test_reject_invalid_magic_bytes(client):
    # Pretend file is named .pdf, but contains plain text without %PDF- signature
    fake_pdf = b"This is a plain text file pretending to be a PDF."
    files = {"file": ("fake.pdf", fake_pdf, "application/pdf")}
    
    response = client.post("/api/v1/documents/upload", files=files)
    assert response.status_code == 400
    assert "Invalid document signature" in response.json()["detail"]


def test_reject_corrupted_pdf(client):
    # Starts with %PDF- but followed by invalid binary noise
    corrupt_pdf = b"%PDF-1.7\r\nGARBAGE_BYTES_THAT_CANNOT_BE_PARSED_BY_FITZ\x00\xff"
    files = {"file": ("corrupt.pdf", corrupt_pdf, "application/pdf")}
    
    response = client.post("/api/v1/documents/upload", files=files)
    assert response.status_code == 400
    assert "Corrupted or malformed PDF structure" in response.json()["detail"]


def test_reject_empty_file(client):
    files = {"file": ("empty.pdf", b"", "application/pdf")}
    response = client.post("/api/v1/documents/upload", files=files)
    assert response.status_code == 400
    assert "empty (0 bytes)" in response.json()["detail"]


def test_reject_encrypted_pdf(client):
    encrypted_bytes = create_encrypted_pdf()
    files = {"file": ("locked.pdf", encrypted_bytes, "application/pdf")}
    
    response = client.post("/api/v1/documents/upload", files=files)
    assert response.status_code == 400
    assert "Password-protected or encrypted PDFs are not supported" in response.json()["detail"]


def test_delete_document(client, db_session):
    pdf_bytes = create_sample_pdf(num_pages=1, title="Temporary")
    files = {"file": ("temp.pdf", pdf_bytes, "application/pdf")}
    upload_res = client.post("/api/v1/documents/upload", files=files)
    doc_id = upload_res.json()["document"]["id"]

    # Delete
    del_res = client.delete(f"/api/v1/documents/{doc_id}")
    assert del_res.status_code == 200
    assert "deleted successfully" in del_res.json()["message"]

    # Verify 404 on subsequent get
    get_res = client.get(f"/api/v1/documents/{doc_id}")
    assert get_res.status_code == 404

