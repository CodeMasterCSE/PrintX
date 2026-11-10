from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class AgentPrinterInfo(BaseModel):
    name: str
    driver_name: Optional[str] = None
    port_name: Optional[str] = None
    is_default: bool = False
    is_online: bool = True
    is_virtual: bool = False
    status: str = "online"
    status_details: Optional[str] = None
    queue_length: int = 0


class PrintJobSubmission(BaseModel):
    job_id: str
    job_number: str
    pdf_path: str
    printer_name: str
    copies: int = Field(default=1, ge=1, le=10)
    color_mode: str = "grayscale"  # "grayscale" | "color"
    page_range: str = "all"
    fit_to_page: bool = True
    duplex: bool = False  # Fixed to False for HP Smart Tank 585
    idempotency_key: str
    auth_token: Optional[str] = None


class SpoolerJobStatus(BaseModel):
    spooler_job_id: int
    document_name: str
    status_code: int
    status_text: str
    pages_printed: int
    total_pages: int
    is_completed: bool = False
    is_error: bool = False
    error_message: Optional[str] = None


class HeartbeatPayload(BaseModel):
    agent_id: str
    version: str = "1.0.0"
    printer_name: str
    printer_status: str
    queue_length: int
    is_online: bool

