from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.models.kiosk import Kiosk
from app.models.pricing import PricingRule
from app.schemas.kiosk import KioskResponse, KioskConfigResponse

router = APIRouter(prefix="/kiosks", tags=["Kiosks"])


@router.get("", response_model=List[KioskResponse])
def list_kiosks(db: Session = Depends(get_db)):
    """List all deployed physical kiosks."""
    kiosks = db.query(Kiosk).filter(Kiosk.is_active == True).all()
    return [KioskResponse.model_validate(k) for k in kiosks]


@router.get("/{kiosk_id}", response_model=KioskResponse)
def get_kiosk(kiosk_id: str, db: Session = Depends(get_db)):
    """Get kiosk metadata and assigned printer."""
    kiosk = db.query(Kiosk).filter((Kiosk.id == kiosk_id) | (Kiosk.code == kiosk_id)).first()
    if not kiosk:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kiosk not found")
    return KioskResponse.model_validate(kiosk)


@router.get("/{kiosk_id}/configuration", response_model=KioskConfigResponse)
def get_kiosk_configuration(kiosk_id: str, db: Session = Depends(get_db)):
    """Returns kiosk configuration for student portal initial load."""
    kiosk = db.query(Kiosk).filter((Kiosk.id == kiosk_id) | (Kiosk.code == kiosk_id)).first()
    if not kiosk:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kiosk not found")

    pricing = db.query(PricingRule).filter(PricingRule.is_active == True).first()
    per_page_bw = pricing.per_page_bw if pricing else 2.0
    per_page_color = pricing.per_page_color if pricing else 10.0

    printer_name = kiosk.printer.name if kiosk.printer else "HP Smart Tank 580-590 series"
    supports_color = kiosk.printer.supports_color if kiosk.printer else True

    return KioskConfigResponse(
        kiosk_id=kiosk.id,
        code=kiosk.code,
        name=kiosk.name,
        location=kiosk.location,
        printer_name=printer_name,
        supports_color=supports_color,
        supports_duplex=False,  # Enforced single-sided for HP Smart Tank 585
        per_page_bw=per_page_bw,
        per_page_color=per_page_color
    )

