from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.payment import Payment, PaymentProvider
from app.schemas.payment import (
    PaymentCreateRequest,
    PaymentResponse,
    PaymentWebhookRequest
)
from app.services.payment_service import PaymentService, MockUpiGateway

router = APIRouter(prefix="/payments", tags=["Payments"])


@router.post("/create", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
def create_payment(req: PaymentCreateRequest, db: Session = Depends(get_db)):
    """Creates a payment order for a print job and generates UPI QR payload."""
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

    resp = PaymentResponse.model_validate(payment)
    gateway = PaymentService.get_gateway(payment.provider)
    resp.upi_qr_data = gateway.generate_upi_qr_data(payment.order_id, payment.amount)
    return resp


@router.get("/{payment_id}", response_model=PaymentResponse)
def get_payment(payment_id: str, db: Session = Depends(get_db)):
    """Retrieves current payment status."""
    payment = db.query(Payment).filter(
        (Payment.id == payment_id) | (Payment.order_id == payment_id)
    ).first()
    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment record not found.")

    resp = PaymentResponse.model_validate(payment)
    gateway = PaymentService.get_gateway(payment.provider)
    resp.upi_qr_data = gateway.generate_upi_qr_data(payment.order_id, payment.amount)
    return resp


@router.post("/webhook", response_model=PaymentResponse)
def payment_webhook(req: PaymentWebhookRequest, db: Session = Depends(get_db)):
    """
    Server-side verification webhook from payment gateway.
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
    return PaymentResponse.model_validate(payment)


@router.post("/simulate-success/{order_id}", response_model=PaymentResponse)
def simulate_upi_payment_success(order_id: str, db: Session = Depends(get_db)):
    """
    Development Sandbox Helper:
    Simulates a verified UPI webhook confirmation.
    Clearly marked for local testing.
    """
    payment = PaymentService.verify_payment_webhook(
        db=db,
        order_id=order_id,
        gateway_tx_id=f"MOCK-UPI-TX-{order_id}",
        status_str="verified",
        signature="mock-verified-signature"
    )
    return PaymentResponse.model_validate(payment)

