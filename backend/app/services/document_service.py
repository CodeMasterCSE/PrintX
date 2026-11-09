import hashlib
import io
import os
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Tuple, Dict, Any, Optional

import fitz  # PyMuPDF
from fastapi import UploadFile, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import logger
from app.models.document import Document, DocumentStatus
from app.models.user import User


class DocumentValidationError(Exception):
    def __init__(self, message: str, status_code: int = status.HTTP_400_BAD_REQUEST):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class DocumentService:
    MAGIC_HEADER = b"%PDF-"

    @classmethod
    def validate_and_extract_pdf(cls, file_bytes: bytes, original_filename: str) -> Dict[str, Any]:
        """
        Validates file signature, structure, encryption, and extracts page count & metadata.
        Raises DocumentValidationError if invalid.
        """
        # 1. File size validation
        file_size = len(file_bytes)
        if file_size == 0:
            raise DocumentValidationError("The uploaded file is empty (0 bytes).")
        if file_size > settings.max_upload_size_bytes:
            raise DocumentValidationError(
                f"File size exceeds the {settings.MAX_UPLOAD_SIZE_MB}MB maximum limit.",
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
            )

        # 2. Magic byte signature validation
        if not file_bytes.startswith(cls.MAGIC_HEADER):
            raise DocumentValidationError(
                "Invalid document signature. Only valid PDF documents are accepted."
            )

        # 3. PyMuPDF parsing and integrity verification
        try:
            doc = fitz.open(stream=file_bytes, filetype="pdf")
        except Exception as e:
            logger.warning(f"Corrupt PDF upload attempt: {original_filename} - {str(e)}")
            raise DocumentValidationError("Corrupted or malformed PDF structure. Unable to process.")

        # 4. Password / Encryption check
        if doc.is_encrypted or doc.needs_pass:
            doc.close()
            raise DocumentValidationError(
                "Password-protected or encrypted PDFs are not supported for self-service printing. Please remove the password before uploading."
            )

        page_count = doc.page_count
        if page_count < 1:
            doc.close()
            raise DocumentValidationError("The PDF does not contain any printable pages.")

        # 5. Page dimension and color detection
        is_color = False
        try:
            for page_index in range(min(page_count, 10)):  # Check first 10 pages for color usage
                page = doc[page_index]
                # Check for color image list or drawing color commands
                images = page.get_images()
                if images:
                    for img in images:
                        xref = img[0]
                        base_image = doc.extract_image(xref)
                        if base_image and base_image.get("colorspace", 1) > 1:
                            is_color = True
                            break
                if is_color:
                    break
        except Exception:
            # Color detection is an optimization; default to false if extraction fails
            is_color = False

        metadata = doc.metadata or {}
        doc.close()

        sha256_hash = hashlib.sha256(file_bytes).hexdigest()

        return {
            "page_count": page_count,
            "file_size": file_size,
            "sha256": sha256_hash,
            "is_color": is_color,
            "title": metadata.get("title") or original_filename,
            "author": metadata.get("author") or "Unknown"
        }

    @classmethod
    def save_document(
        cls,
        db: Session,
        file_bytes: bytes,
        original_filename: str,
        user: Optional[User] = None
    ) -> Document:
        """
        Validates the PDF bytes, writes to secure storage, and creates a Document database record.
        """
        info = cls.validate_and_extract_pdf(file_bytes, original_filename)

        storage_dir = settings.resolved_storage_path
        stored_filename = f"{uuid.uuid4().hex}.pdf"
        target_path = storage_dir / stored_filename

        # Write sanitized file to disk
        target_path.write_bytes(file_bytes)

        # Set expiration retention policy (default 24 hours)
        expires_at = datetime.now(timezone.utc) + timedelta(hours=settings.DOCUMENT_RETENTION_HOURS)

        document = Document(
            filename=stored_filename,
            original_filename=Path(original_filename).name[:250],  # Prevent path traversal
            mime_type="application/pdf",
            file_size_bytes=info["file_size"],
            page_count=info["page_count"],
            is_encrypted=False,
            is_color=info["is_color"],
            storage_path=str(target_path),
            sha256_checksum=info["sha256"],
            status=DocumentStatus.VALIDATED,
            expires_at=expires_at,
            user_id=user.id if user else None
        )

        db.add(document)
        db.commit()
        db.refresh(document)
        logger.info(f"Successfully processed document: id={document.id}, pages={document.page_count}, size={document.file_size_bytes}B")
        return document

    @classmethod
    def generate_preview(cls, document: Document, page_number: int = 1) -> bytes:
        """
        Generates a PNG thumbnail preview for the specified page number.
        """
        file_path = Path(document.storage_path)
        if not file_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Physical document file not found on disk."
            )

        try:
            doc = fitz.open(str(file_path))
            if page_number < 1 or page_number > doc.page_count:
                page_number = 1
            page = doc[page_number - 1]
            # Render at 120 DPI for crisp, lightweight thumbnail preview
            pix = page.get_pixmap(dpi=120)
            img_bytes = pix.tobytes("png")
            doc.close()
            return img_bytes
        except Exception as e:
            logger.error(f"Failed to generate preview for document {document.id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Unable to generate document preview."
            )

    @classmethod
    def delete_document(cls, db: Session, document: Document) -> None:
        """
        Deletes physical file and marks/removes database record.
        """
        file_path = Path(document.storage_path)
        if file_path.exists():
            try:
                file_path.unlink()
            except Exception as e:
                logger.warning(f"Could not remove physical file {file_path}: {str(e)}")

        db.delete(document)
        db.commit()
        logger.info(f"Purged document {document.id}")

