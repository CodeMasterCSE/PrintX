from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import HTTPException, status

from app.models.job import PrintJob, JobStatus, PrintConfiguration, JobEvent, PaperSize, ColorMode
from app.models.document import Document, DocumentStatus
from app.models.printer import Printer
from app.models.kiosk import Kiosk
from app.models.pricing import PricingRule
from app.models.user import User
from app.schemas.job import JobCreateRequest, PrintConfigurationCreate
from app.core.logging import logger
from app.api.routes.pricing import parse_page_range


class JobTransitionError(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


# Permitted state transitions dictionary
VALID_TRANSITIONS = {
    JobStatus.CREATED: {JobStatus.DOCUMENT_VALIDATED, JobStatus.CANCELLED},
    JobStatus.DOCUMENT_VALIDATED: {JobStatus.PAYMENT_PENDING, JobStatus.CANCELLED},
    JobStatus.PAYMENT_PENDING: {JobStatus.PAYMENT_VERIFIED, JobStatus.EXPIRED, JobStatus.CANCELLED},
    JobStatus.PAYMENT_VERIFIED: {JobStatus.QUEUED, JobStatus.CANCELLED},
    JobStatus.QUEUED: {JobStatus.DISPATCHED, JobStatus.CANCELLED},
    JobStatus.DISPATCHED: {JobStatus.SUBMITTED_TO_SPOOLER, JobStatus.FAILED},
    JobStatus.SUBMITTED_TO_SPOOLER: {JobStatus.PRINTING, JobStatus.COMPLETED, JobStatus.FAILED},
    JobStatus.PRINTING: {JobStatus.COMPLETED, JobStatus.FAILED},
    JobStatus.FAILED: {JobStatus.QUEUED},  # Safe retry
    JobStatus.COMPLETED: set(),  # Terminal state
    JobStatus.CANCELLED: set(),  # Terminal state
    JobStatus.EXPIRED: set(),    # Terminal state
}


class JobService:
    @classmethod
    def generate_job_number(cls, db: Session) -> str:
        """Generates sequential, user-friendly job number e.g. PX-2026-0001."""
        year = datetime.now(timezone.utc).year
        count = db.query(func.count(PrintJob.id)).scalar() or 0
        seq = count + 1
        return f"PX-{year}-{seq:04d}"

    @classmethod
    def create_job(cls, db: Session, req: JobCreateRequest, user: Optional[User] = None) -> PrintJob:
        """
        Creates a print job with server-side validation and pricing enforcement.
        Idempotent: returns existing job if idempotency_key already exists.
        """
        # 1. Idempotency check
        existing = db.query(PrintJob).filter(PrintJob.idempotency_key == req.idempotency_key).first()
        if existing:
            logger.info(f"Idempotent job request matched existing job: {existing.job_number}")
            return existing

        # 2. Document validation
        doc = db.query(Document).filter(Document.id == req.document_id).first()
        if not doc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")
        if doc.status != DocumentStatus.VALIDATED:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Document is not validated.")

        # 3. Printer / Kiosk resolution
        printer = None
        if req.printer_id:
            printer = db.query(Printer).filter(Printer.id == req.printer_id).first()
        elif req.kiosk_id:
            kiosk = db.query(Kiosk).filter(Kiosk.id == req.kiosk_id).first()
            if kiosk and kiosk.default_printer_id:
                printer = db.query(Printer).filter(Printer.id == kiosk.default_printer_id).first()
        
        if not printer:
            printer = db.query(Printer).filter(Printer.is_default == True).first()

        # 4. Calculate authoritative price
        pricing_rule = db.query(PricingRule).filter(PricingRule.is_active == True).first()
        per_page_bw = pricing_rule.per_page_bw if pricing_rule else 2.0
        per_page_color = pricing_rule.per_page_color if pricing_rule else 10.0
        base_fee = pricing_rule.base_fee if pricing_rule else 0.0
        min_amount = pricing_rule.min_order_amount if pricing_rule else 2.0

        rate = per_page_color if req.configuration.color_mode == "color" else per_page_bw
        selected_pages = parse_page_range(req.configuration.page_range, doc.page_count)
        total_impressions = selected_pages * req.configuration.copies
        calc_price = max((total_impressions * rate) + base_fee, min_amount)

        # 5. Persist PrintConfiguration
        config = PrintConfiguration(
            paper_size=PaperSize.A4,
            color_mode=ColorMode.COLOR if req.configuration.color_mode == "color" else ColorMode.GRAYSCALE,
            copies=req.configuration.copies,
            page_range=req.configuration.page_range,
            fit_to_page=req.configuration.fit_to_page,
            duplex=False  # HP Smart Tank 585 single-sided
        )
        db.add(config)
        db.flush()

        # 6. Create PrintJob
        job_number = cls.generate_job_number(db)
        job = PrintJob(
            job_number=job_number,
            status=JobStatus.PAYMENT_PENDING,
            price=round(calc_price, 2),
            total_pages=selected_pages,
            sheets_used=total_impressions,
            idempotency_key=req.idempotency_key,
            user_id=user.id if user else None,
            document_id=doc.id,
            printer_id=printer.id if printer else None,
            kiosk_id=req.kiosk_id,
            configuration_id=config.id
        )
        db.add(job)
        db.flush()

        # Initial event
        event = JobEvent(
            job_id=job.id,
            previous_status=None,
            new_status=JobStatus.PAYMENT_PENDING.value,
            message=f"Job created. Awaiting UPI payment of ₹{job.price:.2f}."
        )
        db.add(event)

        db.commit()
        db.refresh(job)
        logger.info(f"Created print job {job.job_number} (Price: ₹{job.price:.2f})")
        return job

    @classmethod
    def transition_status(
        cls,
        db: Session,
        job: PrintJob,
        new_status: JobStatus,
        message: Optional[str] = None,
        spooler_job_id: Optional[int] = None,
        error_message: Optional[str] = None
    ) -> PrintJob:
        """Enforces deterministic state transitions and logs an audit event."""
        current_status = job.status
        allowed = VALID_TRANSITIONS.get(current_status, set())

        if new_status not in allowed:
            err = f"Illegal state transition from {current_status.value} to {new_status.value}."
            logger.warning(f"Job {job.job_number}: {err}")
            raise JobTransitionError(err)

        job.status = new_status
        if spooler_job_id is not None:
            job.spooler_job_id = spooler_job_id
        if error_message is not None:
            job.error_message = error_message

        event = JobEvent(
            job_id=job.id,
            previous_status=current_status.value,
            new_status=new_status.value,
            message=message or f"Status changed to {new_status.value}"
        )
        db.add(event)
        db.commit()
        db.refresh(job)
        logger.info(f"Job {job.job_number} transitioned: {current_status.value} -> {new_status.value}")
        return job

    @classmethod
    def pull_next_queued_job(cls, db: Session, printer_id: Optional[str] = None) -> Optional[PrintJob]:
        """Returns next job that is PAYMENT_VERIFIED or QUEUED."""
        query = db.query(PrintJob).filter(
            PrintJob.status.in_([JobStatus.PAYMENT_VERIFIED, JobStatus.QUEUED])
        )
        if printer_id:
            query = query.filter(PrintJob.printer_id == printer_id)
        
        job = query.order_by(PrintJob.created_at.asc()).first()
        return job

    @classmethod
    def cancel_job(cls, db: Session, job: PrintJob, reason: str = "User requested cancellation") -> PrintJob:
        """Cancels a job if it has not yet reached physical printing."""
        if job.status in (JobStatus.SUBMITTED_TO_SPOOLER, JobStatus.PRINTING, JobStatus.COMPLETED):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot cancel job in '{job.status.value}' state. Paper is already in transit."
            )
        return cls.transition_status(db, job, JobStatus.CANCELLED, message=reason)

    @classmethod
    def retry_failed_job(cls, db: Session, job: PrintJob) -> PrintJob:
        """Safely retries a failed job without double charging."""
        if job.status != JobStatus.FAILED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only failed print jobs are eligible for retry."
            )
        return cls.transition_status(db, job, JobStatus.QUEUED, message="Job re-enqueued for agent retry.")

