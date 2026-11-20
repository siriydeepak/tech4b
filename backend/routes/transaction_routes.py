"""
routes/transaction_routes.py
-----------------------------
Endpoints for AURUM Gold Exchange Transactions & Snapshotting (Dispute Replay):
  - POST /api/transactions/create
  - GET  /api/transactions/{id}/snapshot
  - GET  /api/transactions/
  - GET  /api/transactions/{id}
"""

from __future__ import annotations

from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

import auth
import models
from database import get_db
from models_v2 import TransactionStatus, TransactionV2, UserRole
from pricing_engine import get_cached_rate, seed_today_rates
from schemas_v2 import SnapshotOut, TransactionCreateRequest, TransactionOut
from valuation_engine import (
    CALC_VERSION,
    FINENESS_TO_LABEL,
    build_calculation_snapshot,
    compute_deductions,
    compute_final_offer,
    compute_pure_gold,
    compute_valuation,
)

router = APIRouter(prefix="/api/transactions", tags=["Transactions"])


@router.post("/create", response_model=TransactionOut, status_code=status.HTTP_201_CREATED)
def create_transaction(
    payload: TransactionCreateRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_role(models.UserRole.jeweller, models.UserRole.admin)),
):
    """
    Creates a new gold exchange transaction.
    Executes the valuation engine and freezes all inputs, rates, calculations,
    and deductions into an immutable snapshot JSON column for audit and dispute replay.
    """
    fineness = payload.fineness
    if fineness not in FINENESS_TO_LABEL:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported fineness {fineness}. Allowed: {list(FINENESS_TO_LABEL.keys())}",
        )
    purity_label = FINENESS_TO_LABEL[fineness]

    # Resolve benchmark 24K rate
    rate_999 = payload.rate_999
    rate_id: Optional[str] = None
    rate_date: Optional[str] = None
    rate_session: str = payload.session

    if not rate_999:
        seed_today_rates(db)
        rate_record = get_cached_rate(db, fineness=999, session=payload.session)
        if not rate_record:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not retrieve benchmark 24K gold rate",
            )
        rate_999 = rate_record["rate_per_gram"]
        rate_id = rate_record.get("id", "sim-rate-24k")
        rate_date = str(rate_record.get("date", date.today().isoformat()))
        rate_session = rate_record.get("session", payload.session)
    else:
        rate_id = f"custom-rate-{date.today().isoformat()}"
        rate_date = date.today().isoformat()

    # Perform valuation calculations
    try:
        pure_gold = compute_pure_gold(payload.net_weight, fineness)
        gross_val = compute_valuation(payload.net_weight, fineness, rate_999)
        deduction_dicts = [d.model_dump() for d in payload.deductions]
        deductions_res = compute_deductions(deduction_dicts)
        final_offer = compute_final_offer(gross_val, deductions_res["total"])
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    # Build immutable snapshot
    inputs = {
        "net_weight": payload.net_weight,
        "fineness": fineness,
        "purity_label": purity_label,
        "rate_999": rate_999,
        "rate_date": rate_date,
        "rate_session": rate_session,
    }
    result = {
        "pure_gold_grams": pure_gold,
        "gross_valuation": gross_val,
        "deductions": deductions_res["items"],
        "total_deductions": deductions_res["total"],
        "final_offer": final_offer,
    }
    snapshot = build_calculation_snapshot(
        inputs=inputs,
        result=result,
        rate_id=rate_id,
        calc_version=CALC_VERSION,
    )

    # Persist in transactions table
    txn = TransactionV2(
        customer_id=payload.customer_id,
        jeweller_id=current_user.id,
        jewellery_id=payload.jewellery_id,
        snapshot=snapshot,
        status=TransactionStatus.confirmed,
    )
    db.add(txn)
    db.commit()
    db.refresh(txn)

    return TransactionOut(
        id=txn.id,
        customer_id=txn.customer_id,
        jeweller_id=txn.jeweller_id,
        jewellery_id=txn.jewellery_id,
        status=txn.status.value,
        snapshot=txn.snapshot,
        created_at=txn.created_at,
    )


@router.get("/{txn_id}/snapshot", response_model=SnapshotOut)
def get_transaction_snapshot(
    txn_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    """
    Returns the immutable calculation snapshot for dispute replay.
    Enables side-by-side comparison of original valuation vs current market rate.
    """
    txn = db.query(TransactionV2).filter(TransactionV2.id == txn_id).first()
    if not txn:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")

    # Authorisation check: customer, jeweller, or admin
    if current_user.role == models.UserRole.customer and txn.customer_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    if current_user.role == models.UserRole.jeweller and txn.jeweller_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    return SnapshotOut(
        transaction_id=txn.id,
        snapshot=txn.snapshot or {},
    )


@router.get("/", response_model=List[TransactionOut])
def list_transactions(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    """
    Lists transactions scoped by role:
      - Customers see only their own transactions.
      - Jewellers see transactions created by their store.
      - Admins see all transactions.
    """
    q = db.query(TransactionV2)
    if current_user.role == models.UserRole.customer:
        q = q.filter(TransactionV2.customer_id == current_user.id)
    elif current_user.role == models.UserRole.jeweller:
        q = q.filter(TransactionV2.jeweller_id == current_user.id)

    txns = q.order_by(TransactionV2.created_at.desc()).all()
    return [
        TransactionOut(
            id=t.id,
            customer_id=t.customer_id,
            jeweller_id=t.jeweller_id,
            jewellery_id=t.jewellery_id,
            status=t.status.value,
            snapshot=t.snapshot,
            created_at=t.created_at,
        )
        for t in txns
    ]


@router.get("/{txn_id}", response_model=TransactionOut)
def get_transaction(
    txn_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    txn = db.query(TransactionV2).filter(TransactionV2.id == txn_id).first()
    if not txn:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")

    if current_user.role == models.UserRole.customer and txn.customer_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    if current_user.role == models.UserRole.jeweller and txn.jeweller_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    return TransactionOut(
        id=txn.id,
        customer_id=txn.customer_id,
        jeweller_id=txn.jeweller_id,
        jewellery_id=txn.jewellery_id,
        status=txn.status.value,
        snapshot=txn.snapshot,
        created_at=txn.created_at,
    )

