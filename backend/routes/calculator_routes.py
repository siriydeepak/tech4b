"""
routes/calculator_routes.py
----------------------------
Gold Exchange Calculator endpoint:
  - POST /api/calculator/evaluate
Stateless financial evaluation with itemised deductions and pure gold equivalent.
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from pricing_engine import get_cached_rate, seed_today_rates
from schemas_v2 import CalculatorRequest, CalculatorResponse, DeductionItem
from valuation_engine import (
    CALC_VERSION,
    FINENESS_TO_LABEL,
    compute_deductions,
    compute_final_offer,
    compute_pure_gold,
    compute_valuation,
)

router = APIRouter(prefix="/api/calculator", tags=["Calculator"])


@router.post("/evaluate", response_model=CalculatorResponse)
def evaluate_exchange(
    payload: CalculatorRequest,
    db: Session = Depends(get_db),
):
    """
    Evaluates exchange value of gold item:
      Pure Gold (g) = Wn * (P / 999)
      Valuation V   = Wn * R999 * (P / 999)
      Final Offer   = V - D
    No database records are created.
    """
    fineness = payload.fineness
    if fineness not in FINENESS_TO_LABEL:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported fineness {fineness}. Allowed: {list(FINENESS_TO_LABEL.keys())}",
        )
    purity_label = FINENESS_TO_LABEL[fineness]

    # Resolve benchmark 24K rate (R999)
    rate_999 = payload.rate_999
    rate_id: Optional[str] = None
    rate_date: Optional[str] = None
    rate_session: Optional[str] = payload.session

    if not rate_999:
        seed_today_rates(db)
        rate_record = get_cached_rate(db, fineness=999, session=payload.session)
        if not rate_record:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not retrieve benchmark 24K gold rate",
            )
        rate_999 = rate_record["rate_per_gram"]
        rate_id = rate_record.get("id")
        rate_date = str(rate_record.get("date", date.today().isoformat()))
        rate_session = rate_record.get("session", payload.session)
    else:
        rate_date = date.today().isoformat()

    try:
        pure_gold = compute_pure_gold(payload.net_weight, fineness)
        gross_val = compute_valuation(payload.net_weight, fineness, rate_999)
        deduction_dicts = [d.model_dump() for d in payload.deductions]
        deductions_res = compute_deductions(deduction_dicts)
        final_offer = compute_final_offer(gross_val, deductions_res["total"])
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    return CalculatorResponse(
        net_weight=payload.net_weight,
        fineness=fineness,
        purity_label=purity_label,
        rate_999=rate_999,
        rate_id=rate_id,
        rate_date=rate_date,
        rate_session=rate_session,
        pure_gold_grams=pure_gold,
        gross_valuation=gross_val,
        deductions=[DeductionItem(**d) for d in deductions_res["items"]],
        total_deductions=deductions_res["total"],
        final_offer=final_offer,
        calc_version=CALC_VERSION,
    )

