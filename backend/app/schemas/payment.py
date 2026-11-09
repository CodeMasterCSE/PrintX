from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class PaymentCreateRequest(BaseModel):
    job_id: str
    amount: float = Field(gt=0)
    provider: str = "mock_upi"
    idempotency_key: str


class PaymentEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    event_type: str
    payload: Optional[str] = None
    created_at: datetime


class PaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    order_id: str
    amount: float
    currency: str
    status: str
    provider: str
    payment_method: str
    gateway_transaction_id: Optional[str] = None
    upi_qr_data: Optional[str] = None
    qr_code_base64: Optional[str] = None
    is_mock: bool = False
    events: Optional[List[PaymentEventResponse]] = None
    created_at: datetime


class PaymentWebhookRequest(BaseModel):
    order_id: str
    gateway_transaction_id: str
    status: str
    signature: Optional[str] = None
    payload: Optional[Dict[str, Any]] = None


class PaymentRefundRequest(BaseModel):
    reason: str
    operator_id: Optional[str] = None

