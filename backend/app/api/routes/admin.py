from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database.connection import get_db
from app.models.job import PrintJob, JobStatus
from app.models.payment import Payment, PaymentStatus
from app.models.printer import Printer
from app.models.agent import PrintAgent
from app.models.kiosk import Kiosk
from app.models.pricing import PricingRule
from app.models.audit import SystemSetting, AuditLog
from app.schemas.admin import (
    AdminAnalyticsResponse,
    AdminJobListResponse,
    AdminPaymentListResponse,
    SystemSettingsResponse,
    SystemSettingItem,
    SystemSettingsUpdateRequest,
    AdminKioskCreateRequest,
    AdminPrinterToggleRequest
)
from app.schemas.pricing import PricingRuleResponse, PricingRuleUpdate
from app.schemas.job import JobResponse
from app.schemas.payment import PaymentResponse
from app.schemas.kiosk import KioskResponse
from app.schemas.printer import PrinterResponse
from app.services.auth_service import require_admin_user, get_current_user
from app.services.job_service import JobService
from app.core.logging import logger

router = APIRouter(prefix="/admin", tags=["Admin Operations"])

DEFAULT_SETTINGS = [
    ("MAX_UPLOAD_SIZE_MB", "50", "Maximum permissible PDF upload size in megabytes"),
    ("MAX_PAGE_COUNT", "200", "Maximum permissible pages per single print document"),
    ("DOCUMENT_RETENTION_DAYS", "7", "Storage retention threshold for completed print documents"),
    ("DEFAULT_PRINTER", "HP Smart Tank 580-590 series", "Primary Windows spooler print queue"),
    ("MAINTENANCE_MODE", "false", "Kiosk temporary maintenance lock"),
]


@router.get("/analytics", response_model=AdminAnalyticsResponse)
def get_analytics(db: Session = Depends(get_db)):
    """Computes real-time aggregate analytics, multi-tier revenue, and hardware telemetry."""
    now = datetime.now(timezone.utc)
    one_day_ago = now - timedelta(days=1)
    one_week_ago = now - timedelta(days=7)
    one_month_ago = now - timedelta(days=30)

    total_jobs = db.query(func.count(PrintJob.id)).scalar() or 0
    completed_jobs = db.query(func.count(PrintJob.id)).filter(PrintJob.status == JobStatus.COMPLETED).scalar() or 0
    failed_jobs = db.query(func.count(PrintJob.id)).filter(PrintJob.status == JobStatus.FAILED).scalar() or 0
    pending_jobs = total_jobs - (completed_jobs + failed_jobs)

    # Revenue metrics
    verified_query = db.query(Payment).filter(Payment.status == PaymentStatus.VERIFIED)
    total_revenue = db.query(func.sum(Payment.amount)).filter(Payment.status == PaymentStatus.VERIFIED).scalar() or 0.0

    daily_revenue = (
        db.query(func.sum(Payment.amount))
        .filter(Payment.status == PaymentStatus.VERIFIED, Payment.created_at >= one_day_ago)
        .scalar()
        or 0.0
    )

    weekly_revenue = (
        db.query(func.sum(Payment.amount))
        .filter(Payment.status == PaymentStatus.VERIFIED, Payment.created_at >= one_week_ago)
        .scalar()
        or 0.0
    )

    monthly_revenue = (
        db.query(func.sum(Payment.amount))
        .filter(Payment.status == PaymentStatus.VERIFIED, Payment.created_at >= one_month_ago)
        .scalar()
        or 0.0
    )

    total_pages = db.query(func.sum(PrintJob.sheets_used)).filter(PrintJob.status == JobStatus.COMPLETED).scalar() or 0

    # Hardware Telemetry
    active_printers = db.query(func.count(Printer.id)).filter(Printer.is_online == True).scalar() or 0
    active_agents = db.query(func.count(PrintAgent.id)).filter(PrintAgent.is_active == True).scalar() or 0
    total_spooler_depth = db.query(func.sum(Printer.queue_length)).scalar() or 0

    system_health = "Operational"
    if active_printers == 0:
        system_health = "Offline (No Active Printers)"
    elif failed_jobs > 0 and (failed_jobs / max(total_jobs, 1)) > 0.3:
        system_health = "Degraded (High Failure Rate)"

    return AdminAnalyticsResponse(
        total_jobs=total_jobs,
        completed_jobs=completed_jobs,
        failed_jobs=failed_jobs,
        pending_jobs=pending_jobs,
        total_revenue=float(total_revenue),
        daily_revenue=float(daily_revenue),
        weekly_revenue=float(weekly_revenue),
        monthly_revenue=float(monthly_revenue),
        total_pages_printed=int(total_pages),
        active_printers_count=active_printers,
        active_agents_count=active_agents,
        total_spooler_queue_depth=int(total_spooler_depth),
        system_health=system_health
    )


@router.get("/jobs", response_model=AdminJobListResponse)
def get_admin_jobs(limit: int = 50, db: Session = Depends(get_db)):
    """Lists recent jobs with administrative audit details."""
    jobs = db.query(PrintJob).order_by(PrintJob.created_at.desc()).limit(limit).all()
    total = db.query(func.count(PrintJob.id)).scalar() or 0
    return AdminJobListResponse(
        jobs=[JobService.populate_job_response(db, j) for j in jobs],
        total=total
    )


@router.get("/payments", response_model=AdminPaymentListResponse)
def get_admin_payments(limit: int = 50, db: Session = Depends(get_db)):
    """Lists financial transactions and gateway references."""
    payments = db.query(Payment).order_by(Payment.created_at.desc()).limit(limit).all()
    total = db.query(func.count(Payment.id)).scalar() or 0
    return AdminPaymentListResponse(
        payments=[PaymentResponse.model_validate(p) for p in payments],
        total=total
    )


@router.put("/pricing", response_model=PricingRuleResponse)
def update_pricing_rule(update: PricingRuleUpdate, db: Session = Depends(get_db)):
    """Updates authoritative per-page rates and base fees."""
    rule = db.query(PricingRule).filter(PricingRule.is_active == True).first()
    if not rule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pricing rule not found.")

    if update.per_page_bw is not None:
        rule.per_page_bw = update.per_page_bw
    if update.per_page_color is not None:
        rule.per_page_color = update.per_page_color
    if update.base_fee is not None:
        rule.base_fee = update.base_fee
    if update.min_order_amount is not None:
        rule.min_order_amount = update.min_order_amount

    db.commit()
    db.refresh(rule)
    logger.info(f"Updated pricing rule: B&W=₹{rule.per_page_bw:.2f}, Color=₹{rule.per_page_color:.2f}")
    return PricingRuleResponse.model_validate(rule)


@router.get("/settings", response_model=SystemSettingsResponse)
def get_system_settings(db: Session = Depends(get_db)):
    """Retrieves all configurable platform settings with automated baseline initialization."""
    settings_records = db.query(SystemSetting).all()
    if not settings_records:
        for k, v, desc in DEFAULT_SETTINGS:
            s = SystemSetting(key=k, value=v, description=desc)
            db.add(s)
        db.commit()
        settings_records = db.query(SystemSetting).all()

    items = [
        SystemSettingItem(
            key=s.key,
            value=s.value,
            description=s.description,
            updated_at=s.updated_at
        )
        for s in settings_records
    ]
    return SystemSettingsResponse(settings=items)


@router.put("/settings", response_model=SystemSettingsResponse)
def update_system_settings(req: SystemSettingsUpdateRequest, db: Session = Depends(get_db)):
    """Upserts system settings key-value pairs."""
    for key, value in req.settings.items():
        setting = db.query(SystemSetting).filter(SystemSetting.key == key).first()
        if setting:
            setting.value = str(value)
        else:
            setting = SystemSetting(key=key, value=str(value), description="Custom Setting")
            db.add(setting)
    db.commit()
    logger.info(f"Updated system settings: {list(req.settings.keys())}")
    return get_system_settings(db)


@router.get("/kiosks", response_model=List[KioskResponse])
def list_admin_kiosks(db: Session = Depends(get_db)):
    """Lists all registered physical kiosks."""
    kiosks = db.query(Kiosk).all()
    return [KioskResponse.model_validate(k) for k in kiosks]


@router.post("/kiosks", response_model=KioskResponse, status_code=status.HTTP_201_CREATED)
def create_admin_kiosk(req: AdminKioskCreateRequest, db: Session = Depends(get_db)):
    """Registers a new kiosk terminal."""
    existing = db.query(Kiosk).filter(Kiosk.code == req.code).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Kiosk code '{req.code}' already exists.")

    kiosk = Kiosk(
        code=req.code,
        name=req.name,
        location=req.location,
        default_printer_id=req.default_printer_id,
        is_active=True
    )
    db.add(kiosk)
    db.commit()
    db.refresh(kiosk)
    logger.info(f"Registered new kiosk: {kiosk.code} ({kiosk.name})")
    return KioskResponse.model_validate(kiosk)


@router.post("/printers/{printer_id}/toggle-status", response_model=PrinterResponse)
def toggle_printer_status(
    printer_id: str,
    req: AdminPrinterToggleRequest,
    db: Session = Depends(get_db)
):
    """Sets a printer online/offline for administrative maintenance."""
    printer = db.query(Printer).filter(Printer.id == printer_id).first()
    if not printer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Printer not found.")

    printer.is_online = req.is_online
    printer.status = "READY" if req.is_online else "MAINTENANCE"
    db.commit()
    db.refresh(printer)
    logger.info(f"Printer '{printer.name}' online status toggled to: {printer.is_online}")
    return PrinterResponse.model_validate(printer)


@router.post("/printers/{printer_id}/set-default", response_model=PrinterResponse)
def set_default_printer(printer_id: str, db: Session = Depends(get_db)):
    """Sets the designated printer as global system default."""
    target = db.query(Printer).filter(Printer.id == printer_id).first()
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Printer not found.")

    # Clear previous default
    db.query(Printer).update({Printer.is_default: False})
    target.is_default = True
    db.commit()
    db.refresh(target)
    logger.info(f"Printer '{target.name}' set as global system default.")
    return PrinterResponse.model_validate(target)
