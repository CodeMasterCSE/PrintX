from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.models.printer import Printer
from app.schemas.printer import PrinterResponse
from pydantic import BaseModel


class HeartbeatRequest(BaseModel):
    agent_id: str
    version: str = "1.0.0"
    printer_name: str
    printer_status: str
    queue_length: int
    is_online: bool


router = APIRouter(prefix="/printers", tags=["Printers"])


@router.post("/heartbeat")
def receive_printer_heartbeat(payload: HeartbeatRequest, db: Session = Depends(get_db)):
    """Receives live queue telemetry and health status from Windows Print Agent."""
    printer = db.query(Printer).filter(Printer.name == payload.printer_name).first()
    if not printer:
        # Register on first discovery if absent
        printer = Printer(
            name=payload.printer_name,
            driver_name=payload.printer_name,
            is_online=payload.is_online,
            status=payload.printer_status,
            queue_length=payload.queue_length,
            last_heartbeat=datetime.now(timezone.utc)
        )
        db.add(printer)
    else:
        printer.status = payload.printer_status
        printer.queue_length = payload.queue_length
        printer.is_online = payload.is_online
        printer.last_heartbeat = datetime.now(timezone.utc)

    db.commit()
    return {"status": "recorded", "printer": payload.printer_name}


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

