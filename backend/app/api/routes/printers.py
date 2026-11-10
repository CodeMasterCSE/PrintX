from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.models.printer import Printer
from app.schemas.printer import PrinterResponse
from app.core.events import event_broadcaster
from pydantic import BaseModel


class HeartbeatRequest(BaseModel):
    agent_id: str
    version: str = "1.0.0"
    printer_name: str
    printer_status: str
    queue_length: int
    is_online: bool


class PrinterStatusUpdateRequest(BaseModel):
    status: str
    status_details: Optional[str] = None
    is_online: Optional[bool] = None


router = APIRouter(prefix="/printers", tags=["Printers"])


@router.post("/heartbeat")
def receive_printer_heartbeat(payload: HeartbeatRequest, db: Session = Depends(get_db)):
    """Receives live queue telemetry and health status from Windows Print Agent."""
    printer = db.query(Printer).filter(Printer.name == payload.printer_name).first()
    if not printer:
        return {"status": "unregistered", "printer": payload.printer_name, "message": "Printer not yet added by Admin."}

    printer.status = payload.printer_status
    printer.queue_length = payload.queue_length
    printer.is_online = payload.is_online
    printer.last_heartbeat = datetime.now(timezone.utc)

    db.commit()
    db.refresh(printer)

    # Broadcast real-time printer update via SSE
    try:
        p_data = PrinterResponse.model_validate(printer).model_dump(mode="json")
        event_broadcaster.broadcast_sync("printers", "printer_update", p_data)
    except Exception:
        pass

    return {"status": "recorded", "printer": payload.printer_name}


@router.get("/stream")
async def stream_printer_status(
    request: Request,
    max_events: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    Real-time Server-Sent Events (SSE) telemetry stream for all registered printers.
    Instantly pushes printer status changes, paper-out detection, and queue depth.
    """
    printers = db.query(Printer).all()
    initial_snapshot = [PrinterResponse.model_validate(p).model_dump(mode="json") for p in printers]

    return StreamingResponse(
        event_broadcaster.event_generator(
            channel="printers",
            initial_data=initial_snapshot,
            initial_event="printer_snapshot",
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


@router.get("", response_model=List[PrinterResponse])
def list_printers(db: Session = Depends(get_db)):
    """List all registered printers and their live status."""
    printers = db.query(Printer).all()
    return [PrinterResponse.model_validate(p) for p in printers]


@router.get("/{printer_id}", response_model=PrinterResponse)
def get_printer(printer_id: str, db: Session = Depends(get_db)):
    """Get detailed printer telemetry."""
    printer = db.query(Printer).filter(Printer.id == printer_id).first()
    if not printer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Printer not found")
    return PrinterResponse.model_validate(printer)


@router.post("/{printer_id}/status", response_model=PrinterResponse)
def update_printer_status(
    printer_id: str,
    payload: PrinterStatusUpdateRequest,
    db: Session = Depends(get_db)
):
    """Updates printer operational status (e.g. out_of_paper, online, offline) and broadcasts real-time telemetry."""
    printer = db.query(Printer).filter(Printer.id == printer_id).first()
    if not printer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Printer not found")

    printer.status = payload.status
    if payload.status_details is not None:
        printer.status_details = payload.status_details
    if payload.is_online is not None:
        printer.is_online = payload.is_online
    printer.last_heartbeat = datetime.now(timezone.utc)

    db.commit()
    db.refresh(printer)

    # Broadcast real-time update
    try:
        p_data = PrinterResponse.model_validate(printer).model_dump(mode="json")
        event_broadcaster.broadcast_sync("printers", "printer_update", p_data)
    except Exception:
        pass

    return PrinterResponse.model_validate(printer)


