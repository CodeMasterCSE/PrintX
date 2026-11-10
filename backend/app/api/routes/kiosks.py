import io
import qrcode
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.models.kiosk import Kiosk
from app.models.pricing import PricingRule
from app.schemas.kiosk import KioskResponse, KioskConfigResponse
from app.core.config import settings

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


@router.get("/{kiosk_id}/qr.png")
def get_kiosk_qr_png(
    kiosk_id: str,
    request: Request,
    base_url: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Streams a high-resolution PNG QR code for this kiosk."""
    kiosk = db.query(Kiosk).filter((Kiosk.id == kiosk_id) | (Kiosk.code == kiosk_id)).first()
    if not kiosk:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kiosk not found")

    target_base = base_url or settings.SERVER_PUBLIC_URL
    if not base_url and request.headers.get("host"):
        target_base = f"http://{request.headers.get('host')}"
    portal_url = f"{target_base}/print?device={kiosk.code}"
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=2,
    )
    qr.add_data(portal_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#0f172a", back_color="#ffffff")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return Response(content=buf.getvalue(), media_type="image/png")


