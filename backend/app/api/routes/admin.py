from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database.connection import get_db
from app.models.job import PrintJob, JobStatus
from app.models.payment import Payment, PaymentStatus
from app.models.printer import Printer
from app.models.pricing import PricingRule
from app.schemas.admin import (
    AdminAnalyticsResponse,
    AdminJobListResponse,
    AdminPaymentListResponse
)
from app.schemas.pricing import PricingRuleResponse, PricingRuleUpdate
from app.schemas.job import JobResponse
from app.schemas.payment import PaymentResponse
from app.services.auth_service import require_admin_user, get_current_user

router = APIRouter(prefix="/admin", tags=["Admin Operations"])


@router.get("/analytics", response_model=AdminAnalyticsResponse)
def get_analytics(db: Session = Depends(get_db)):
    """Computes aggregate analytics and system health."""
    total_jobs = db.query(func.count(PrintJob.id)).scalar() or 0
    completed_jobs = db.query(func.count(PrintJob.id)).filter(PrintJob.status == JobStatus.COMPLETED).scalar() or 0
    failed_jobs = db.query(func.count(PrintJob.id)).filter(PrintJob.status == JobStatus.FAILED).scalar() or 0
    pending_jobs = total_jobs - (completed_jobs + failed_jobs)

    # Revenue from verified payments
    total_revenue = db.query(func.sum(Payment.amount)).filter(Payment.status == PaymentStatus.VERIFIED).scalar() or 0.0
    total_pages = db.query(func.sum(PrintJob.sheets_used)).filter(PrintJob.status == JobStatus.COMPLETED).scalar() or 0

    active_printers = db.query(func.count(Printer.id)).filter(Printer.is_online == True).scalar() or 0

    return AdminAnalyticsResponse(
        total_jobs=total_jobs,
        completed_jobs=completed_jobs,
        failed_jobs=failed_jobs,
        pending_jobs=pending_jobs,
        total_revenue=float(total_revenue),
        total_pages_printed=int(total_pages),
        active_printers_count=active_printers,
        system_health="Operational" if active_printers > 0 else "Degraded"
    )


@router.get("/jobs", response_model=AdminJobListResponse)
def get_admin_jobs(limit: int = 50, db: Session = Depends(get_db)):
    """Lists recent jobs with administrative audit details."""
    jobs = db.query(PrintJob).order_by(PrintJob.created_at.desc()).limit(limit).all()
    total = db.query(func.count(PrintJob.id)).scalar() or 0
    return AdminJobListResponse(
        jobs=[JobResponse.model_validate(j) for j in jobs],
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
    return PricingRuleResponse.model_validate(rule)

