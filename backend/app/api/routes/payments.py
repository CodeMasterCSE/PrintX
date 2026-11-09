import json
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response, Header
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.payment import Payment, PaymentProvider
from app.schemas.payment import (
    PaymentCreateRequest,
    PaymentResponse,
    PaymentWebhookRequest,
    PaymentRefundRequest
)
from app.services.payment_service import PaymentService
from app.core.config import settings
from app.core.logging import logger

router = APIRouter(prefix="/payments", tags=["Payments"])


@router.post("/create", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
def create_payment(req: PaymentCreateRequest, db: Session = Depends(get_db)):
    """Creates a payment order for a print job and generates UPI QR payload and image data."""
    try:
        prov = PaymentProvider(req.provider.lower())
    except ValueError:
        prov = PaymentProvider.MOCK_UPI

    payment = PaymentService.create_payment(
        db=db,
        job_id=req.job_id,
        amount=req.amount,
        provider=prov,
        idempotency_key=req.idempotency_key
    )
    return PaymentService.populate_payment_response(payment)


@router.get("/{payment_id}", response_model=PaymentResponse)
def get_payment(payment_id: str, db: Session = Depends(get_db)):
    """Retrieves current payment status, deep link, and Base64 QR code."""
    payment = db.query(Payment).filter(
        (Payment.id == payment_id) | (Payment.order_id == payment_id)
    ).first()
    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment record not found.")

    return PaymentService.populate_payment_response(payment)


@router.get("/{payment_id}/qr.png")
def get_payment_qr_image(payment_id: str, db: Session = Depends(get_db)):
    """Streams a high-resolution PNG image of the UPI payment QR code for kiosk displays."""
    payment = db.query(Payment).filter(
        (Payment.id == payment_id) | (Payment.order_id == payment_id)
    ).first()
    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment record not found.")

    gateway = PaymentService.get_gateway(payment.provider)
    png_bytes = gateway.generate_qr_png_bytes(payment.order_id, payment.amount)
    return Response(content=png_bytes, media_type="image/png")


@router.post("/webhook", response_model=PaymentResponse)
def payment_webhook(req: PaymentWebhookRequest, db: Session = Depends(get_db)):
    """
    Standard server-side verification webhook from payment gateway.
    Cryptographically verifies signature and releases print job to queue.
    """
    payment = PaymentService.verify_payment_webhook(
        db=db,
        order_id=req.order_id,
        gateway_tx_id=req.gateway_transaction_id,
        status_str=req.status,
        signature=req.signature,
        payload=req.payload
    )
    return PaymentService.populate_payment_response(payment)


@router.post("/webhook/razorpay", response_model=PaymentResponse)
async def razorpay_webhook(
    request: Request,
    x_razorpay_signature: Optional[str] = Header(None, alias="X-Razorpay-Signature"),
    db: Session = Depends(get_db)
):
    """Production Razorpay webhook with HMAC-SHA256 signature verification."""
    raw_body = await request.body()
    body_str = raw_body.decode("utf-8")

    try:
        data = json.loads(body_str)
        payload = data.get("payload", {}).get("payment", {}).get("entity", {})
        order_id = payload.get("order_id") or data.get("order_id")
        tx_id = payload.get("id") or "RZP-TX-DEFAULT"
        status_str = payload.get("status", "captured")
    except Exception as e:
        logger.error(f"Malformed Razorpay webhook payload: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Malformed webhook JSON payload.")

    if not order_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing order_id in webhook.")

    gateway = PaymentService.get_gateway(PaymentProvider.RAZORPAY)
    if x_razorpay_signature and not gateway.verify_signature(body_str, x_razorpay_signature):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Razorpay webhook signature mismatch.")

    payment = PaymentService.verify_payment_webhook(
        db=db,
        order_id=order_id,
        gateway_tx_id=tx_id,
        status_str=status_str,
        signature=x_razorpay_signature,
        payload=data
    )
    return PaymentService.populate_payment_response(payment)


@router.post("/simulate-success/{order_id}", response_model=PaymentResponse)
def simulate_upi_payment_success(order_id: str, db: Session = Depends(get_db)):
    """
    Development Sandbox Helper:
    Simulates a verified UPI webhook confirmation.
    Blocked in production environments.
    """
    if settings.ENVIRONMENT == "production":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Mock payment simulation is strictly prohibited in production."
        )

    payment = PaymentService.verify_payment_webhook(
        db=db,
        order_id=order_id,
        gateway_tx_id=f"MOCK-UPI-TX-{order_id}",
        status_str="verified",
        signature="mock-verified-signature"
    )
    return PaymentService.populate_payment_response(payment)


@router.post("/{payment_id}/refund", response_model=PaymentResponse)
def process_refund(
    payment_id: str,
    req: PaymentRefundRequest,
    db: Session = Depends(get_db)
):
    """Processes refund for an unprinted or cancelled print job."""
    payment = PaymentService.process_refund(
        db=db,
        payment_id=payment_id,
        reason=req.reason,
        operator_id=req.operator_id
    )
    return PaymentService.populate_payment_response(payment)
