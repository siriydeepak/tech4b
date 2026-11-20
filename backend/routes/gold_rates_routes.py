"""
routes/gold_rates_routes.py
----------------------------
Endpoints for daily IBJA gold rates:
  - GET /api/gold-rates/latest
  - GET /api/gold-rates/history
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from database import get_db
from models_v2 import GoldRate, RateSession
from pricing_engine import get_all_cached_rates, get_history_rates, seed_today_rates
from schemas_v2 import GoldRateOut, GoldRatesHistoryResponse, GoldRatesLatestResponse

router = APIRouter(prefix="/api/gold-rates", tags=["Gold Rates"])


@router.get("/latest", response_model=GoldRatesLatestResponse)
def get_latest_rates(
    session: Optional[str] = Query(None, description="AM or PM (defaults to current active session)"),
    db: Session = Depends(get_db),
):
    """
    Returns the latest IBJA gold benchmark rates for all standards (24K, 22K, 18K, 14K).
    Automatically seeds today's rates if not yet populated.
    """
    # Ensure today's rates are seeded
    seed_today_rates(db)

    rate_session = RateSession(session.upper()) if session and session.upper() in ("AM", "PM") else None
    today = date.today()

    rates = get_all_cached_rates(db, target_date=today, session=rate_session)

    rate_outs = [GoldRateOut.model_validate(r) for r in rates]
    active_session = rates[0].session.value if rates else (session or "AM")
    active_date = rates[0].date if rates else today

    return GoldRatesLatestResponse(
        date=active_date,
        session=active_session,
        rates=rate_outs,
    )


@router.get("/history", response_model=GoldRatesHistoryResponse)
def get_rate_history(
    days: int = Query(7, ge=1, le=90, description="Number of days of history to fetch"),
    db: Session = Depends(get_db),
):
    """
    Returns historical gold rates over the requested window (up to 90 days).
    """
    # Ensure current rates exist
    seed_today_rates(db)

    history_records = get_history_rates(db, days=days)
    rate_outs = [GoldRateOut.model_validate(r) for r in history_records]

    return GoldRatesHistoryResponse(
        days=days,
        rates=rate_outs,
    )

