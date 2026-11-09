from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.models.pricing import PricingRule
from app.schemas.pricing import (
    PricingEstimateRequest,
    PricingEstimateResponse,
    PricingBreakdown,
    PricingRuleResponse
)

router = APIRouter(prefix="/pricing", tags=["Pricing"])


def parse_page_range(page_range: str, max_pages: int) -> int:
    """Calculates total selected pages from 'all' or custom range like '1-3,5'."""
    if not page_range or page_range.strip().lower() == "all":
        return max_pages

    selected = set()
    parts = page_range.split(",")
    for part in parts:
        part = part.strip()
        if "-" in part:
            try:
                start, end = part.split("-")
                start_page = max(1, int(start.strip()))
                end_page = min(max_pages, int(end.strip()))
                for p in range(start_page, end_page + 1):
                    selected.add(p)
            except ValueError:
                continue
        else:
            try:
                p = int(part)
                if 1 <= p <= max_pages:
                    selected.add(p)
            except ValueError:
                continue

    return len(selected) if selected else max_pages


@router.get("/rules", response_model=List[PricingRuleResponse])
def get_pricing_rules(db: Session = Depends(get_db)):
    """Retrieves all active pricing tier rules."""
    rules = db.query(PricingRule).filter(PricingRule.is_active == True).all()
    return [PricingRuleResponse.model_validate(r) for r in rules]


@router.post("/estimate", response_model=PricingEstimateResponse)
def estimate_pricing(request: PricingEstimateRequest, db: Session = Depends(get_db)):
    """Calculates authoritative printing price breakdown on the server."""
    rule = db.query(PricingRule).filter(PricingRule.is_active == True).first()
    if not rule:
        # Default fallback rule if database hasn't been seeded yet
        per_page_bw = 2.0
        per_page_color = 10.0
        base_fee = 0.0
        min_order = 2.0
        rule_name = "Default Standard"
    else:
        per_page_bw = rule.per_page_bw
        per_page_color = rule.per_page_color
        base_fee = rule.base_fee
        min_order = rule.min_order_amount
        rule_name = rule.name

    rate = per_page_color if request.color_mode.lower() == "color" else per_page_bw
    selected_pages = parse_page_range(request.page_range, request.page_count)
    total_impressions = selected_pages * request.copies
    subtotal = (total_impressions * rate) + base_fee
    total_amount = max(subtotal, min_order)

    breakdown = PricingBreakdown(
        selected_pages=selected_pages,
        copies=request.copies,
        total_impressions=total_impressions,
        rate_per_page=rate,
        base_fee=base_fee,
        subtotal=subtotal,
        discount=0.0,
        total_amount=round(total_amount, 2),
        currency="INR"
    )

    return PricingEstimateResponse(
        breakdown=breakdown,
        pricing_rule_name=rule_name
    )

