from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from app.schemas.job import JobResponse
from app.schemas.payment import PaymentResponse
from app.schemas.printer import PrinterResponse
from app.schemas.kiosk import KioskResponse


class AdminAnalyticsResponse(BaseModel):
    total_jobs: int
    completed_jobs: int
    failed_jobs: int
    pending_jobs: int
    total_revenue: float
    daily_revenue: float = 0.0
    weekly_revenue: float = 0.0
    monthly_revenue: float = 0.0
    total_pages_printed: int
    active_printers_count: int
    active_agents_count: int = 1
    total_spooler_queue_depth: int = 0
    system_health: str


class AdminJobListResponse(BaseModel):
    jobs: List[JobResponse]
    total: int


class AdminPaymentListResponse(BaseModel):
    payments: List[PaymentResponse]
    total: int


class SystemSettingItem(BaseModel):
    key: str
    value: str
    description: Optional[str] = None
    updated_at: Optional[datetime] = None


class SystemSettingsResponse(BaseModel):
    settings: List[SystemSettingItem]


class SystemSettingsUpdateRequest(BaseModel):
    settings: Dict[str, str]


class AdminKioskCreateRequest(BaseModel):
    code: str
    name: str
    location: str
    default_printer_id: Optional[str] = None


class AdminPrinterToggleRequest(BaseModel):
    is_online: bool
