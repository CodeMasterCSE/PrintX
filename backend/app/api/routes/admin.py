from datetime import datetime, timezone, timedelta
import secrets
import uuid
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
from app.models.user import User
from app.schemas.admin import (
    AdminAnalyticsResponse,
    AdminJobListResponse,
    AdminPaymentListResponse,
    SystemSettingsResponse,
    SystemSettingItem,
    SystemSettingsUpdateRequest,
    AdminKioskCreateRequest,
    AdminPrinterToggleRequest,
    AdminAgentRegisterRequest,
    AdminAgentRegisterResponse,
    DocumentPurgeRequest,
    DocumentPurgeResponse,
    DiscoveredPrinterItem,
    AdminPrinterCreateRequest
)
from app.schemas.pricing import PricingRuleResponse, PricingRuleUpdate
from app.schemas.job import JobResponse
from app.schemas.payment import PaymentResponse
from app.schemas.kiosk import KioskResponse
from app.schemas.printer import PrinterResponse
from app.services.auth_service import require_admin_user, get_current_user
from app.services.job_service import JobService
from app.services.document_service import DocumentService
from app.core.security import get_password_hash
from app.core.logging import logger

try:
    import win32print
    HAS_WIN32PRINT = True
except ImportError:
    win32print = None
    HAS_WIN32PRINT = False

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


@router.get("/printers/discover", response_model=List[DiscoveredPrinterItem])
def discover_system_printers(db: Session = Depends(get_db)):
    """
    Scans the host system using Windows Print Spooler APIs (win32print)
    to discover connected physical printers (USB and Wi-Fi/Network).
    Identifies connection types and flags already-registered devices.
    """
    discovered: List[DiscoveredPrinterItem] = []
    registered_printers = {p.name: p for p in db.query(Printer).all()}

    if not HAS_WIN32PRINT:
        return []

    flags = win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
    try:
        raw_printers = win32print.EnumPrinters(flags)
    except Exception as e:
        logger.error(f"Failed to enumerate Windows printers: {e}")
        return []

    VIRTUAL_DRIVERS = {
        "microsoft print to pdf", "onenote", "onenote (desktop)",
        "onenote for windows 10", "fax", "microsoft xps document writer"
    }

    for p in raw_printers:
        p_name = p[2]
        handle = None
        driver_name = p_name
        port_name = "Local"
        try:
            handle = win32print.OpenPrinter(p_name)
            details = win32print.GetPrinter(handle, 2)
            driver_name = details.get("pDriverName", p_name)
            port_name = details.get("pPortName", "Local")
        except Exception:
            pass
        finally:
            if handle:
                try:
                    win32print.ClosePrinter(handle)
                except Exception:
                    pass

        # Determine connection interface
        p_port_upper = port_name.upper()
        p_name_upper = p_name.upper()
        if "USB" in p_port_upper or "USB" in p_name_upper:
            conn_type = "USB"
        elif "WSD" in p_port_upper or "IP_" in p_port_upper or "HP" in p_port_upper or "." in port_name:
            conn_type = "Wi-Fi / Network"
        else:
            conn_type = "Local Port"

        is_virt = (p_name.lower().strip() in VIRTUAL_DRIVERS or driver_name.lower().strip() in VIRTUAL_DRIVERS)
        if is_virt:
            conn_type = "Virtual / Software"

        existing = registered_printers.get(p_name)

        discovered.append(DiscoveredPrinterItem(
            name=p_name,
            driver_name=driver_name,
            port_name=port_name,
            connection_type=conn_type,
            is_virtual=is_virt,
            is_already_added=existing is not None,
            existing_printer_id=existing.id if existing else None,
            status="online",
            supports_color=True,
            supports_duplex=False
        ))

    # Sort so physical devices (Wi-Fi and USB) appear first, and virtual/demo drivers at the bottom
    discovered.sort(key=lambda x: (x.is_virtual, x.is_already_added, x.name))
    return discovered


@router.post("/printers/add", response_model=PrinterResponse, status_code=status.HTTP_201_CREATED)
def add_printer(req: AdminPrinterCreateRequest, db: Session = Depends(get_db)):
    """Registers a newly discovered or manually configured printer."""
    existing = db.query(Printer).filter(Printer.name == req.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Printer '{req.name}' is already registered in PrintX."
        )

    printer_count = db.query(func.count(Printer.id)).scalar() or 0
    is_def = req.is_default or (printer_count == 0)

    if is_def:
        db.query(Printer).update({Printer.is_default: False})

    new_printer = Printer(
        name=req.name,
        driver_name=req.driver_name or req.name,
        port_name=req.port_name or "USB001",
        location=req.location or "Campus Kiosk",
        supports_color=req.supports_color,
        supports_duplex=req.supports_duplex,
        is_default=is_def,
        is_online=True,
        status="online",
        status_details="Ready for incoming print jobs",
        queue_length=0
    )
    db.add(new_printer)
    db.commit()
    db.refresh(new_printer)

    try:
        from app.core.events import event_broadcaster
        p_data = PrinterResponse.model_validate(new_printer).model_dump(mode="json")
        event_broadcaster.broadcast_sync("printers", "printer_update", p_data)
    except Exception:
        pass

    logger.info(f"Admin added new printer: '{new_printer.name}' (Port: {new_printer.port_name})")
    return PrinterResponse.model_validate(new_printer)


@router.delete("/printers/{printer_id}", response_model=Dict[str, str])
def delete_printer(printer_id: str, db: Session = Depends(get_db)):
    """Removes a printer from the system (decommissions demo or unused hardware)."""
    printer = db.query(Printer).filter(Printer.id == printer_id).first()
    if not printer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Printer not found.")

    active_jobs = db.query(PrintJob).filter(
        PrintJob.printer_id == printer.id,
        PrintJob.status.in_([JobStatus.SUBMITTED_TO_SPOOLER, JobStatus.PRINTING])
    ).count()

    if active_jobs > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot remove printer '{printer.name}': {active_jobs} job(s) are actively printing."
        )

    # Unlink kiosks and historical jobs
    db.query(Kiosk).filter(Kiosk.default_printer_id == printer.id).update({Kiosk.default_printer_id: None})
    db.query(PrintJob).filter(PrintJob.printer_id == printer.id).update({PrintJob.printer_id: None})

    p_name = printer.name
    was_default = printer.is_default

    db.delete(printer)
    db.commit()

    if was_default:
        next_printer = db.query(Printer).first()
        if next_printer:
            next_printer.is_default = True
            db.commit()

    try:
        from app.core.events import event_broadcaster
        event_broadcaster.broadcast_sync("printers", "printer_update", {"id": printer_id, "status": "deleted"})
    except Exception:
        pass

    logger.info(f"Admin removed printer '{p_name}' (ID: {printer_id})")
    return {"message": f"Printer '{p_name}' successfully removed."}


@router.post("/agents/register", response_model=AdminAgentRegisterResponse, status_code=status.HTTP_201_CREATED)
def register_print_agent(req: AdminAgentRegisterRequest, db: Session = Depends(get_db)):
    """
    Registers a new Windows Print Agent machine.
    Generates a unique agent_id and cryptographically secure secret token.
    The raw secret is only returned once upon initial creation.
    """
    agent_id = f"AGENT-WIN11-{uuid.uuid4().hex[:6].upper()}"
    raw_secret = f"px_sec_{secrets.token_urlsafe(32)}"
    secret_hash = get_password_hash(raw_secret)

    agent = PrintAgent(
        agent_id=agent_id,
        name=req.name,
        secret_hash=secret_hash,
        is_active=True,
        hostname=req.hostname,
        ip_address=req.ip_address,
        version="1.0.0"
    )
    db.add(agent)
    db.commit()
    db.refresh(agent)
    logger.info(f"Registered new Windows Print Agent device: {agent_id} ({agent.name})")

    return AdminAgentRegisterResponse(
        agent_id=agent.agent_id,
        name=agent.name,
        agent_secret=raw_secret,
        created_at=agent.created_at
    )


@router.get("/agents")
def list_print_agents(db: Session = Depends(get_db)):
    """Lists registered print agents and their last heartbeat timestamp."""
    agents = db.query(PrintAgent).all()
    return [
        {
            "id": a.id,
            "agent_id": a.agent_id,
            "name": a.name,
            "is_active": a.is_active,
            "last_heartbeat": a.last_heartbeat,
            "hostname": a.hostname,
            "ip_address": a.ip_address,
            "version": a.version,
            "created_at": a.created_at
        }
        for a in agents
    ]


@router.post("/documents/purge", response_model=DocumentPurgeResponse)
def purge_expired_documents(
    payload: Optional[DocumentPurgeRequest] = None,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin_user)
):
    """
    Automated Document Shredding & Privacy Retention Purge (FERPA/GDPR compliance).
    Securely wipes binary files from disk/storage for completed print jobs past retention threshold.
    Preserves financial and audit ledger entries.
    """
    retention_min = payload.retention_minutes if payload else 15
    unprinted_hours = payload.unprinted_expiry_hours if payload else 24

    result = DocumentService.purge_expired_documents(
        db=db,
        retention_minutes=retention_min,
        unprinted_expiry_hours=unprinted_hours
    )

    # Log admin action in AuditLog
    audit_entry = AuditLog(
        user_id=admin.id,
        action="DOCUMENT_PRIVACY_PURGE",
        resource_type="document",
        details=f"Shredded {result['purged_count']} expired documents ({result['freed_mb']} MB freed). Policy: {retention_min}m retention."
    )
    db.add(audit_entry)
    db.commit()

    return DocumentPurgeResponse(
        purged_count=result["purged_count"],
        freed_bytes=result["freed_bytes"],
        freed_mb=result["freed_mb"],
        errors=result["errors"],
        message=f"Privacy purge complete: {result['purged_count']} document(s) securely shredded, {result['freed_mb']} MB disk space recovered."
    )

