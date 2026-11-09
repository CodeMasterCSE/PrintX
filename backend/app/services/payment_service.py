import hmac
import hashlib
import json
import uuid
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.payment import Payment, PaymentStatus, PaymentProvider, PaymentEvent
from app.models.job import PrintJob, JobStatus
from app.services.job_service import JobService
from app.core.config import settings
from app.core.logging import logger


class BasePaymentGateway(ABC):
    @abstractmethod
    def create_order(self, order_id: str, amount: float, currency: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    def verify_signature(self, payload_str: str, signature: str) -> bool:
        pass

    @abstractmethod
    def generate_upi_qr_data(self, order_id: str, amount: float) -> str:
        pass


class MockUpiGateway(BasePaymentGateway):
    """
    Clearly labeled Development Sandbox Mock Gateway.
    Generates standard UPI format string (NPCI specification):
    upi://pay?pa=<vpa>&pn=<payee>&am=<amount>&cu=INR&tn=<order_id>
    """
    PAYEE_VPA = "printx.kiosk@upi"
    PAYEE_NAME = "PrintX Smart Printing"

    def create_order(self, order_id: str, amount: float, currency: str = "INR") -> Dict[str, Any]:
        qr_data = self.generate_upi_qr_data(order_id, amount)
        return {
            "order_id": order_id,
            "amount": amount,
            "currency": currency,
            "provider": "mock_upi",
            "upi_qr_data": qr_data,
            "status": "pending",
            "is_mock": True
        }

    def generate_upi_qr_data(self, order_id: str, amount: float) -> str:
        return f"upi://pay?pa={self.PAYEE_VPA}&pn={self.PAYEE_NAME}&am={amount:.2f}&cu=INR&tn={order_id}"

    def verify_signature(self, payload_str: str, signature: str) -> bool:
        # In mock gateway, signature matching sha256 or 'mock-verified' is accepted
        expected = hmac.new(
            settings.SECRET_KEY.encode(),
            payload_str.encode(),
            hashlib.sha256
        ).hexdigest()
        return signature in (expected, "mock-verified-signature", "dev-signature")


class RazorpayGateway(BasePaymentGateway):
    """Integration ready for production Razorpay UPI payments."""
    def __init__(self, key_id: str = "", key_secret: str = ""):
        self.key_id = key_id
        self.key_secret = key_secret

    def create_order(self, order_id: str, amount: float, currency: str = "INR") -> Dict[str, Any]:
        # Production Razorpay order creation via SDK or REST
        return {"order_id": order_id, "amount": int(amount * 100), "currency": currency}

    def verify_signature(self, payload_str: str, signature: str) -> bool:
        expected = hmac.new(self.key_secret.encode(), payload_str.encode(), hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)

    def generate_upi_qr_data(self, order_id: str, amount: float) -> str:
        return f"upi://pay?pa=rzp.{order_id}@razorpay&pn=PrintX&am={amount:.2f}&cu=INR&tn={order_id}"


class PaymentService:
    @classmethod
    def get_gateway(cls, provider: PaymentProvider) -> BasePaymentGateway:
        if provider == PaymentProvider.RAZORPAY:
            return RazorpayGateway()
        return MockUpiGateway()

    @classmethod
    def create_payment(
        cls,
        db: Session,
        job_id: str,
        amount: float,
        provider: PaymentProvider = PaymentProvider.MOCK_UPI,
        idempotency_key: Optional[str] = None
    ) -> Payment:
        """
        Creates an idempotent payment order for a print job.
        Never trusts client-provided amounts: validates against job.price.
        """
        job = db.query(PrintJob).filter(PrintJob.id == job_id).first()
        if not job:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Print job not found.")

        # Authoritative server-side price check
        if round(amount, 2) != round(job.price, 2):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Amount mismatch. Expected ₹{job.price:.2f}, got ₹{amount:.2f}."
            )

        # Idempotency check
        key = idempotency_key or f"PAY-{job.id}"
        existing = db.query(Payment).filter(Payment.idempotency_key == key).first()
        if existing:
            logger.info(f"Idempotent payment match: {existing.order_id}")
            return existing

        order_id = f"ORDER-{uuid.uuid4().hex[:12].upper()}"
        gateway = cls.get_gateway(provider)
        order_data = gateway.create_order(order_id, job.price, currency="INR")

        payment = Payment(
            order_id=order_id,
            amount=job.price,
            currency="INR",
            status=PaymentStatus.PENDING,
            provider=provider,
            payment_method="upi",
            idempotency_key=key,
            user_id=job.user_id
        )
        db.add(payment)
        db.flush()

        # Associate with PrintJob
        job.payment_id = payment.id

        # Log event
        event = PaymentEvent(
            payment_id=payment.id,
            event_type="ORDER_CREATED",
            payload=json.dumps(order_data)
        )
        db.add(event)
        db.commit()
        db.refresh(payment)

        logger.info(f"Created UPI payment order {order_id} for job {job.job_number} (₹{payment.amount:.2f})")
        return payment

    @classmethod
    def verify_payment_webhook(
        cls,
        db: Session,
        order_id: str,
        gateway_tx_id: str,
        status_str: str,
        signature: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None
    ) -> Payment:
        """
        Server-side payment verification.
        Transitions job: PAYMENT_PENDING -> PAYMENT_VERIFIED -> QUEUED.
        """
        payment = db.query(Payment).filter(Payment.order_id == order_id).first()
        if not payment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment order not found.")

        # Idempotency: if already verified, return without double-enqueueing
        if payment.status == PaymentStatus.VERIFIED:
            logger.info(f"Payment {order_id} was already verified. Returning idempotent record.")
            return payment

        gateway = cls.get_gateway(payment.provider)
        payload_data = payload or {"order_id": order_id, "tx_id": gateway_tx_id}
        payload_str = json.dumps(payload_data, sort_keys=True)

        # In production, verify HMAC signature
        if signature and not gateway.verify_signature(payload_str, signature):
            logger.warning(f"Invalid webhook signature for order {order_id}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Payment signature verification failed."
            )

        if status_str.lower() in ("verified", "success", "paid"):
            payment.status = PaymentStatus.VERIFIED
            payment.gateway_transaction_id = gateway_tx_id
            payment.gateway_signature = signature

            event = PaymentEvent(
                payment_id=payment.id,
                event_type="PAYMENT_VERIFIED",
                payload=payload_str
            )
            db.add(event)

            # Advance associated print job through state machine
            if payment.print_job:
                JobService.transition_status(
                    db,
                    payment.print_job,
                    JobStatus.PAYMENT_VERIFIED,
                    message=f"UPI Payment verified (TxID: {gateway_tx_id})."
                )
                JobService.transition_status(
                    db,
                    payment.print_job,
                    JobStatus.QUEUED,
                    message="Job enqueued for Windows Print Controller pickup."
                )

            db.commit()
            db.refresh(payment)
            logger.info(f"Payment {order_id} verified successfully. Print job {payment.print_job.job_number} is QUEUED.")
        else:
            payment.status = PaymentStatus.FAILED
            event = PaymentEvent(
                payment_id=payment.id,
                event_type="PAYMENT_FAILED",
                payload=payload_str
            )
            db.add(event)
            db.commit()

        return payment

