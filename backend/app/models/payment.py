import enum
from sqlalchemy import Column, String, Float, Enum, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database.connection import Base
from app.models.base import UUIDMixin, TimestampMixin


class PaymentStatus(str, enum.Enum):
    PENDING = "pending"
    VERIFIED = "verified"
    FAILED = "failed"
    EXPIRED = "expired"
    REFUNDED = "refunded"


class PaymentProvider(str, enum.Enum):
    MOCK_UPI = "mock_upi"
    RAZORPAY = "razorpay"
    CASHFREE = "cashfree"
    UPI_DIRECT = "upi_direct"


class Payment(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "payments"

    order_id = Column(String(100), unique=True, index=True, nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String(10), default="INR", nullable=False)
    status = Column(Enum(PaymentStatus), default=PaymentStatus.PENDING, index=True, nullable=False)
    provider = Column(Enum(PaymentProvider), default=PaymentProvider.MOCK_UPI, nullable=False)
    payment_method = Column(String(50), default="upi", nullable=False)
    gateway_transaction_id = Column(String(100), nullable=True, index=True)
    gateway_signature = Column(String(255), nullable=True)
    idempotency_key = Column(String(100), unique=True, index=True, nullable=False)

    user_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    user = relationship("User", back_populates="payments")

    print_job = relationship("PrintJob", back_populates="payment", uselist=False)
    events = relationship("PaymentEvent", back_populates="payment", cascade="all, delete-orphan")


class PaymentEvent(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "payment_events"

    payment_id = Column(String(36), ForeignKey("payments.id"), nullable=False)
    payment = relationship("Payment", back_populates="events")

    event_type = Column(String(100), nullable=False)  # e.g., ORDER_CREATED, WEBHOOK_RECEIVED, VERIFIED
    payload = Column(Text, nullable=True)

