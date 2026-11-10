from typing import Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict
from app.schemas.printer import PrinterResponse


class KioskBase(BaseModel):
    code: str
    name: str
    location: str
    is_active: bool = True


class KioskResponse(KioskBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    default_printer_id: Optional[str] = None
    printer: Optional[PrinterResponse] = None
    qr_code_data: Optional[str] = None
    created_at: datetime


class KioskConfigResponse(BaseModel):
    kiosk_id: str
    code: str
    name: str
    location: str
    printer_name: Optional[str] = None
    supports_color: bool = True
    supports_duplex: bool = False
    per_page_bw: float
    per_page_color: float
    lan_ip: Optional[str] = None
    mobile_portal_url: Optional[str] = None


