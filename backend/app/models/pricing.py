from sqlalchemy import Column, String, Float, Boolean
from app.database.connection import Base
from app.models.base import UUIDMixin, TimestampMixin


class PricingRule(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "pricing_rules"

    name = Column(String(100), unique=True, nullable=False)
    per_page_bw = Column(Float, default=2.00, nullable=False)     # e.g., ₹2.00 per B&W page
    per_page_color = Column(Float, default=10.00, nullable=False) # e.g., ₹10.00 per Color page
    base_fee = Column(Float, default=0.00, nullable=False)        # Convenience or service fee
    min_order_amount = Column(Float, default=2.00, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

