from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel
from app.schemas.job import JobResponse
from app.schemas.payment import PaymentResponse
from app.schemas.printer import PrinterResponse


class AdminAnalyticsResponse(BaseModel):
    total_jobs: int
    completed_jobs: int
    failed_jobs: int
    pending_jobs: int
    total_revenue: float
    total_pages_printed: int
    active_printers_count: int
    system_health: str


class AdminJobListResponse(BaseModel):
    jobs: List[JobResponse]
    total: int


class AdminPaymentListResponse(BaseModel):
    payments: List[PaymentResponse]
    total: int

