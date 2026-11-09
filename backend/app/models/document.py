import enum
from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from app.database.connection import Base
from app.models.base import UUIDMixin, TimestampMixin


class DocumentStatus(str, enum.Enum):
    PENDING_VALIDATION = "pending_validation"
    VALIDATED = "validated"
    FAILED = "failed"
    PURGED = "purged"


class Document(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "documents"

    filename = Column(String(255), nullable=False)           # Sanitized stored filename
    original_filename = Column(String(255), nullable=False)  # User's uploaded filename
    mime_type = Column(String(100), default="application/pdf", nullable=False)
    file_size_bytes = Column(Integer, nullable=False)
    page_count = Column(Integer, default=0, nullable=False)
    is_encrypted = Column(Boolean, default=False, nullable=False)
    is_color = Column(Boolean, default=False, nullable=False)
    storage_path = Column(String(500), nullable=False)
    sha256_checksum = Column(String(64), index=True, nullable=False)
    status = Column(Enum(DocumentStatus), default=DocumentStatus.PENDING_VALIDATION, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)

    user_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    user = relationship("User", back_populates="documents")

    print_jobs = relationship("PrintJob", back_populates="document")

