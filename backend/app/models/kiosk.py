from sqlalchemy import Column, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.database.connection import Base
from app.models.base import UUIDMixin, TimestampMixin


class Kiosk(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "kiosks"

    code = Column(String(50), unique=True, index=True, nullable=False)  # e.g. KIOSK-CAMPUS-01
    name = Column(String(255), nullable=False)
    location = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    qr_code_data = Column(String(500), nullable=True)

    default_printer_id = Column(String(36), ForeignKey("printers.id"), nullable=True)
    printer = relationship("Printer", back_populates="kiosks")

    print_jobs = relationship("PrintJob", back_populates="kiosk")

