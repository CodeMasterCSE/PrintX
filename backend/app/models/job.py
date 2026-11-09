import enum
from sqlalchemy import Column, String, Integer, Boolean, Float, ForeignKey, Enum, Text
from sqlalchemy.orm import relationship
from app.database.connection import Base
from app.models.base import UUIDMixin, TimestampMixin


class JobStatus(str, enum.Enum):
    CREATED = "CREATED"
    DOCUMENT_VALIDATED = "DOCUMENT_VALIDATED"
    PAYMENT_PENDING = "PAYMENT_PENDING"
    PAYMENT_VERIFIED = "PAYMENT_VERIFIED"
    QUEUED = "QUEUED"
    DISPATCHED = "DISPATCHED"
    SUBMITTED_TO_SPOOLER = "SUBMITTED_TO_SPOOLER"
    PRINTING = "PRINTING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"


class ColorMode(str, enum.Enum):
    GRAYSCALE = "grayscale"
    COLOR = "color"


class PaperSize(str, enum.Enum):
    A4 = "A4"


class PrintConfiguration(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "print_configurations"

    paper_size = Column(Enum(PaperSize), default=PaperSize.A4, nullable=False)
    color_mode = Column(Enum(ColorMode), default=ColorMode.GRAYSCALE, nullable=False)
    copies = Column(Integer, default=1, nullable=False)
    page_range = Column(String(100), default="all", nullable=False)
    fit_to_page = Column(Boolean, default=True, nullable=False)
    duplex = Column(Boolean, default=False, nullable=False)  # Always False for MVP

    print_job = relationship("PrintJob", back_populates="configuration", uselist=False)


class PrintJob(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "print_jobs"

    job_number = Column(String(50), unique=True, index=True, nullable=False)  # Human-readable e.g. PX-2026-0001
    status = Column(Enum(JobStatus), default=JobStatus.CREATED, index=True, nullable=False)
    price = Column(Float, nullable=False)
    total_pages = Column(Integer, default=1, nullable=False)
    sheets_used = Column(Integer, default=1, nullable=False)
    error_message = Column(Text, nullable=True)
    spooler_job_id = Column(Integer, nullable=True)
    idempotency_key = Column(String(100), unique=True, index=True, nullable=False)

    user_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    user = relationship("User", back_populates="print_jobs")

    document_id = Column(String(36), ForeignKey("documents.id"), nullable=False)
    document = relationship("Document", back_populates="print_jobs")

    printer_id = Column(String(36), ForeignKey("printers.id"), nullable=True)
    printer = relationship("Printer", back_populates="print_jobs")

    kiosk_id = Column(String(36), ForeignKey("kiosks.id"), nullable=True)
    kiosk = relationship("Kiosk", back_populates="print_jobs")

    configuration_id = Column(String(36), ForeignKey("print_configurations.id"), nullable=False)
    configuration = relationship("PrintConfiguration", back_populates="print_job")

    payment_id = Column(String(36), ForeignKey("payments.id"), nullable=True)
    payment = relationship("Payment", back_populates="print_job")

    events = relationship("JobEvent", back_populates="job", cascade="all, delete-orphan", order_by="JobEvent.created_at.asc()")


class JobEvent(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "job_events"

    job_id = Column(String(36), ForeignKey("print_jobs.id"), nullable=False)
    job = relationship("PrintJob", back_populates="events")

    previous_status = Column(String(50), nullable=True)
    new_status = Column(String(50), nullable=False)
    message = Column(String(500), nullable=True)

