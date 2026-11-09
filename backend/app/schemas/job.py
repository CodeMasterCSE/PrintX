from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from app.schemas.document import DocumentResponse
from app.schemas.printer import PrinterResponse
from app.schemas.payment import PaymentResponse


class PrintConfigurationCreate(BaseModel):
    paper_size: str = "A4"
    color_mode: str = "grayscale"  # "grayscale" | "color"
    copies: int = Field(default=1, ge=1, le=10)
    page_range: str = "all"
    fit_to_page: bool = True
    duplex: bool = False  # Fixed to False for MVP (HP Smart Tank 585)


class PrintConfigurationResponse(PrintConfigurationCreate):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime


class JobCreateRequest(BaseModel):
    document_id: str
    printer_id: Optional[str] = None
    kiosk_id: Optional[str] = None
    configuration: PrintConfigurationCreate
    idempotency_key: str


class JobEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    previous_status: Optional[str] = None
    new_status: str
    message: Optional[str] = None
    created_at: datetime


class JobRetryRequest(BaseModel):
    force_retry: bool = False
    operator_notes: Optional[str] = None


class JobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    job_number: str
    status: str
    price: float
    total_pages: int
    sheets_used: int
    error_message: Optional[str] = None
    spooler_job_id: Optional[int] = None
    idempotency_key: str
    queue_position: Optional[int] = None
    estimated_wait_seconds: Optional[int] = None
    document_id: str
    document: Optional[DocumentResponse] = None
    printer_id: Optional[str] = None
    printer: Optional[PrinterResponse] = None
    configuration: Optional[PrintConfigurationResponse] = None
    payment: Optional[PaymentResponse] = None
    events: Optional[List[JobEventResponse]] = None
    created_at: datetime
    updated_at: datetime


class JobListResponse(BaseModel):
    total: int
    items: List[JobResponse]
    limit: int
    offset: int


class ReconciliationResult(BaseModel):
    recovered_dispatched: int
    recovered_spooling: int
    expired_pending: int
    total_processed: int


class JobStatusUpdate(BaseModel):
    status: str
    spooler_job_id: Optional[int] = None
    error_message: Optional[str] = None
    message: Optional[str] = None

