from typing import Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class PrinterBase(BaseModel):
    name: str
    driver_name: Optional[str] = None
    port_name: Optional[str] = None
    location: Optional[str] = None
    is_online: bool = True
    is_default: bool = False
    supports_color: bool = True
    supports_duplex: bool = False


class PrinterResponse(PrinterBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    status: str
    status_details: Optional[str] = None
    queue_length: int
    last_heartbeat: Optional[datetime] = None
    created_at: datetime


class PrinterStatusUpdate(BaseModel):
    status: str
    status_details: Optional[str] = None
    queue_length: Optional[int] = None
    is_online: Optional[bool] = None

