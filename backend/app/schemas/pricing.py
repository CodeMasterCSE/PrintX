from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class PricingEstimateRequest(BaseModel):
    page_count: int = Field(ge=1, description="Total pages in document")
    copies: int = Field(default=1, ge=1, le=10, description="Number of copies")
    color_mode: str = Field(default="grayscale", description="'grayscale' or 'color'")
    page_range: str = Field(default="all", description="'all' or range e.g. '1-3,5'")


class PricingBreakdown(BaseModel):
    selected_pages: int
    copies: int
    total_impressions: int
    rate_per_page: float
    base_fee: float
    subtotal: float
    discount: float = 0.0
    total_amount: float
    currency: str = "INR"


class PricingEstimateResponse(BaseModel):
    breakdown: PricingBreakdown
    pricing_rule_name: str


class PricingRuleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    per_page_bw: float
    per_page_color: float
    base_fee: float
    min_order_amount: float
    is_active: bool
    created_at: datetime


class PricingRuleUpdate(BaseModel):
    per_page_bw: Optional[float] = None
    per_page_color: Optional[float] = None
    base_fee: Optional[float] = None
    min_order_amount: Optional[float] = None
    is_active: Optional[bool] = None

