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
from app.storage.storage_provider import get_storage_provider


class DocumentValidationError(Exception):
    def __init__(self, message: str, status_code: int = status.HTTP_400_BAD_REQUEST):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class DocumentService:
    MAGIC_HEADER = b"%PDF-"

    @classmethod
    def detect_file_format(cls, file_bytes: bytes) -> Optional[str]:
        """Detects whether bytes are PDF, PNG, JPEG, or WEBP."""
        if file_bytes.startswith(b"%PDF-"):
            return "pdf"
        if file_bytes.startswith(b"\xff\xd8\xff"):
            return "jpeg"
        if file_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
            return "png"
        if file_bytes.startswith(b"RIFF") and len(file_bytes) >= 12 and file_bytes[8:12] == b"WEBP":
            return "webp"
        return None

    @classmethod
    def convert_image_to_a4_pdf(cls, image_bytes: bytes, image_format: str) -> bytes:
        """
        Converts PNG, JPG, or WEBP image bytes into a standardized, single-sided A4 PDF.
        Maintains aspect ratio, centers image on page, and enforces standard margins (36 pt / 0.5 in).
        """
        try:
            img_doc = fitz.open(stream=image_bytes, filetype=image_format)
            img_rect = img_doc[0].rect
            img_w, img_h = img_rect.width, img_rect.height

            # Standard A4 dimensions in points (72 DPI)
            a4_width, a4_height = 595.28, 841.89
            margin = 36.0  # 0.5 inch margins

            avail_w = a4_width - (2 * margin)
            avail_h = a4_height - (2 * margin)

            scale = min(avail_w / img_w, avail_h / img_h)
            final_w = img_w * scale
            final_h = img_h * scale

            x0 = margin + (avail_w - final_w) / 2.0
            y0 = margin + (avail_h - final_h) / 2.0
            target_rect = fitz.Rect(x0, y0, x0 + final_w, y0 + final_h)

            pdf_doc = fitz.open()
            page = pdf_doc.new_page(width=a4_width, height=a4_height)
            page.insert_image(target_rect, stream=image_bytes)
            pdf_bytes = pdf_doc.tobytes()

            pdf_doc.close()
            img_doc.close()
            return pdf_bytes
        except Exception as e:
            logger.error(f"Image to PDF conversion failed: {e}")
            raise DocumentValidationError(f"Unable to process image: {str(e)}")

    @classmethod
    def validate_and_extract_pdf(cls, file_bytes: bytes, original_filename: str) -> Dict[str, Any]:
        """
        Validates file signature, structure, encryption, converts images to A4 PDF,
        and extracts page count & metadata.
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
        detected_fmt = cls.detect_file_format(file_bytes)
        if not detected_fmt:
            raise DocumentValidationError(
                "Invalid document signature. Accepted formats are PDF, PNG, JPG/JPEG, and WEBP."
            )

        # If image, convert to standardized A4 PDF
        is_converted_image = False
        working_bytes = file_bytes
        if detected_fmt != "pdf":
            working_bytes = cls.convert_image_to_a4_pdf(file_bytes, detected_fmt)
            is_converted_image = True

        # 3. PyMuPDF parsing and integrity verification
        try:
            doc = fitz.open(stream=working_bytes, filetype="pdf")
        except Exception as e:
            logger.warning(f"Corrupt document upload attempt: {original_filename} - {str(e)}")
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

        sha256_hash = hashlib.sha256(working_bytes).hexdigest()

        return {
            "page_count": page_count,
            "file_size": len(working_bytes),
            "sha256": sha256_hash,
            "is_color": is_color,
            "title": metadata.get("title") or original_filename,
            "author": metadata.get("author") or "Unknown",
            "pdf_bytes": working_bytes,
            "is_image": is_converted_image,
            "detected_format": detected_fmt
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
        Validates the document bytes (converting images if necessary), writes to secure storage,
        and creates a Document database record.
        """
        info = cls.validate_and_extract_pdf(file_bytes, original_filename)
        pdf_to_save = info.get("pdf_bytes", file_bytes)

        storage_provider = get_storage_provider()
        stored_path = storage_provider.save_file(pdf_to_save, original_filename)
        stored_filename = Path(stored_path).name

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
            storage_path=stored_path,
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
        storage_provider = get_storage_provider()
        try:
            file_bytes = storage_provider.get_file_bytes(document.storage_path)
            doc = fitz.open(stream=file_bytes, filetype="pdf")
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
        Deletes stored file and marks/removes database record.
        """
        storage_provider = get_storage_provider()
        storage_provider.delete_file(document.storage_path)

        db.delete(document)
        db.commit()
        logger.info(f"Purged document {document.id}")

    @classmethod
    def get_download_url(cls, document: Document) -> str:
        """Returns download / pre-signed URL."""
        storage_provider = get_storage_provider()
        return storage_provider.generate_download_url(document.storage_path, document.id)

