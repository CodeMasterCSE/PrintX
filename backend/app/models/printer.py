import enum
from sqlalchemy import Column, String, Boolean, Integer, DateTime
from sqlalchemy.orm import relationship
from app.database.connection import Base
from app.models.base import UUIDMixin, TimestampMixin


class PrinterStatus(str, enum.Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    BUSY = "busy"
    ERROR = "error"
    PAPER_JAM = "paper_jam"
    OUT_OF_PAPER = "out_of_paper"
    LOW_INK = "low_ink"


class Printer(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "printers"

    name = Column(String(255), unique=True, index=True, nullable=False)
    driver_name = Column(String(255), nullable=True)
    port_name = Column(String(255), nullable=True)
    location = Column(String(255), nullable=True)
    is_online = Column(Boolean, default=True, nullable=False)
    is_default = Column(Boolean, default=False, nullable=False)
    supports_color = Column(Boolean, default=True, nullable=False)
    supports_duplex = Column(Boolean, default=False, nullable=False)  # False for HP Smart Tank 585
    status = Column(String(50), default=PrinterStatus.ONLINE.value, nullable=False)
    status_details = Column(String(500), nullable=True)
    queue_length = Column(Integer, default=0, nullable=False)
    last_heartbeat = Column(DateTime(timezone=True), nullable=True)

    kiosks = relationship("Kiosk", back_populates="printer")
    print_jobs = relationship("PrintJob", back_populates="printer")

