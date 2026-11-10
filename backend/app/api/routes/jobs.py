from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Header, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.job import PrintJob, JobStatus
from app.models.agent import PrintAgent
from app.models.user import User
from app.schemas.job import (
    JobCreateRequest,
    JobResponse,
    JobStatusUpdate,
    JobEventResponse,
    JobRetryRequest,
    JobReceiptResponse,
    ReconciliationResult
)
from app.schemas.common import MessageResponse
from app.services.job_service import JobService, JobTransitionError
from app.services.auth_service import get_current_user
from app.storage.storage_provider import get_storage_provider
from app.core.logging import logger
from app.core.security import verify_password
from app.core.config import settings
from app.core.events import event_broadcaster

router = APIRouter(prefix="/jobs", tags=["Print Jobs"])


def verify_agent_auth(
    x_agent_id: Optional[str] = Header(None, alias="X-Agent-ID"),
    x_agent_secret: Optional[str] = Header(None, alias="X-Agent-Secret"),
    db: Session = Depends(get_db)
) -> PrintAgent:
    """Verifies that requests to agent endpoints originate from registered Windows print agents."""
    if not x_agent_id or not x_agent_secret:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing agent authentication headers."
        )

    agent = db.query(PrintAgent).filter(PrintAgent.agent_id == x_agent_id).first()
    if not agent or not agent.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Agent identity unverified or inactive."
        )

    # In local development, check configured secret or stored hash
    if x_agent_secret != settings.AGENT_SECRET_KEY and not verify_password(x_agent_secret, agent.secret_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid agent credentials."
        )

    return agent


@router.post("", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
def create_print_job(
    req: JobCreateRequest,
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_current_user)
):
    """Creates a persistent print job and calculates server-side price."""
    job = JobService.create_job(db=db, req=req, user=user)
    return JobService.populate_job_response(db, job)


@router.get("", response_model=List[JobResponse])
def list_jobs(
    status_filter: Optional[str] = None,
    search: Optional[str] = None,
    printer_id: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_current_user)
):
    """Lists print jobs with optional status filter, search by job number/idempotency key, and printer filtering."""
    query = db.query(PrintJob)
    if user:
        query = query.filter(PrintJob.user_id == user.id)
    if status_filter:
        query = query.filter(PrintJob.status == status_filter.upper())
    if printer_id:
        query = query.filter(PrintJob.printer_id == printer_id)
    if search:
        pattern = f"%{search}%"
        query = query.filter(
            (PrintJob.job_number.ilike(pattern)) |
            (PrintJob.idempotency_key.ilike(pattern))
        )
    
    jobs = query.order_by(PrintJob.created_at.desc()).offset(offset).limit(limit).all()
    return [JobService.populate_job_response(db, j) for j in jobs]


@router.post("/reconcile", response_model=ReconciliationResult)
def reconcile_stale_jobs(
    dispatched_timeout_seconds: int = 300,
    printing_timeout_seconds: int = 900,
    pending_timeout_seconds: int = 900,
    db: Session = Depends(get_db)
):
    """Triggers crash recovery reconciliation sweep across stuck or timed-out print jobs."""
    results = JobService.reconcile_stale_jobs(
        db=db,
        dispatched_timeout_seconds=dispatched_timeout_seconds,
        printing_timeout_seconds=printing_timeout_seconds,
        pending_timeout_seconds=pending_timeout_seconds
    )
    return ReconciliationResult(**results)


@router.get("/{job_id}", response_model=JobResponse)
def get_job(job_id: str, db: Session = Depends(get_db)):
    """Retrieves full job details, document info, configuration, audit timeline, and live queue position."""
    job = db.query(PrintJob).filter(PrintJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Print job not found.")
    return JobService.populate_job_response(db, job)


@router.get("/{job_id}/stream")
async def stream_job_status(
    job_id: str,
    request: Request,
    max_events: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    Real-time Server-Sent Events (SSE) telemetry stream for a print job.
    Instantly pushes job state transitions, queue movement, and completion.
    Emits an immediate snapshot on connection, and periodic keep-alives.
    """
    job = db.query(PrintJob).filter(PrintJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Print job not found.")

    initial_job_data = JobService.populate_job_response(db, job).model_dump(mode="json")

    return StreamingResponse(
        event_broadcaster.event_generator(
            channel=f"job:{job_id}",
            initial_data=initial_job_data,
            initial_event="job_update",
            request=request,
            max_events=max_events
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.get("/{job_id}/receipt", response_model=JobReceiptResponse)
def get_job_receipt(job_id: str, db: Session = Depends(get_db)):
    """Retrieves an official immutable digital receipt for a print job."""
    job = db.query(PrintJob).filter(PrintJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Print job not found.")

    tx_ref = None
    if job.payment and job.payment.gateway_transaction_id:
        tx_ref = job.payment.gateway_transaction_id
    elif job.payment:
        tx_ref = job.payment.order_id

    # Find completion timestamp from audit events if available
    completed_time = None
    for ev in job.events:
        if ev.new_status == "COMPLETED":
            completed_time = ev.created_at
            break

    # Document pages count in selected range
    pages_count = job.total_pages

    return JobReceiptResponse(
        job_id=job.id,
        job_number=job.job_number,
        transaction_reference=tx_ref,
        document_name=job.document.original_filename if job.document else "document.pdf",
        pages_count=pages_count,
        copies=job.configuration.copies if job.configuration else 1,
        printing_mode=job.configuration.color_mode.value if job.configuration else "grayscale",
        total_price=job.price,
        status=job.status.value,
        created_at=job.created_at,
        completed_at=completed_time or job.updated_at
    )



@router.post("/{job_id}/cancel", response_model=JobResponse)
def cancel_job(
    job_id: str,
    reason: Optional[str] = "User requested cancellation",
    db: Session = Depends(get_db)
):
    """Cancels a pending or queued job prior to physical printing."""
    job = db.query(PrintJob).filter(PrintJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Print job not found.")
    
    cancelled = JobService.cancel_job(db=db, job=job, reason=reason)
    return JobService.populate_job_response(db, cancelled)


@router.post("/{job_id}/retry", response_model=JobResponse)
def retry_job(
    job_id: str,
    req: Optional[JobRetryRequest] = None,
    db: Session = Depends(get_db)
):
    """Safely retries a failed print job with duplicate print protection."""
    job = db.query(PrintJob).filter(PrintJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Print job not found.")
    
    force = req.force_retry if req else False
    notes = req.operator_notes if req else None
    retried = JobService.retry_failed_job(db=db, job=job, force_retry=force, operator_notes=notes)
    return JobService.populate_job_response(db, retried)


# ================= Windows Agent Endpoints =================

@router.post("/agent/pull")
def agent_pull_next_job(
    agent: PrintAgent = Depends(verify_agent_auth),
    db: Session = Depends(get_db)
):
    """Called by Windows Print Controller to pull the next authorized print job."""
    job = JobService.pull_next_queued_job(db)
    if not job:
        return {"job": None, "message": "No jobs currently queued."}

    storage_provider = get_storage_provider()
    local_path = storage_provider.get_local_path(job.document.storage_path)
    if local_path and local_path.exists():
        doc_dispatch_path = str(local_path)
    else:
        doc_dispatch_path = storage_provider.generate_download_url(job.document.storage_path, job.document.id)

    return {
        "job": {
            "id": job.id,
            "job_number": job.job_number,
            "status": job.status.value,
            "document_path": doc_dispatch_path,
            "document_name": job.document.original_filename,
            "price": job.price,
            "idempotency_key": job.idempotency_key,
            "configuration": {
                "paper_size": job.configuration.paper_size.value,
                "color_mode": job.configuration.color_mode.value,
                "copies": job.configuration.copies,
                "page_range": job.configuration.page_range,
                "fit_to_page": job.configuration.fit_to_page,
                "duplex": job.configuration.duplex
            }
        }
    }


@router.patch("/{job_id}/status", response_model=JobResponse)
def update_job_status_from_agent(
    job_id: str,
    update: JobStatusUpdate,
    agent: PrintAgent = Depends(verify_agent_auth),
    db: Session = Depends(get_db)
):
    """Called by Windows Agent to advance state machine based on spooler events."""
    job = db.query(PrintJob).filter(PrintJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Print job not found.")

    try:
        new_status_enum = JobStatus(update.status.upper())
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid status '{update.status}'.")

    try:
        updated = JobService.transition_status(
            db=db,
            job=job,
            new_status=new_status_enum,
            message=update.message or f"Agent reported {update.status}",
            spooler_job_id=update.spooler_job_id,
            error_message=update.error_message
        )
    except JobTransitionError as jte:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=jte.message)

    return JobResponse.model_validate(updated)

