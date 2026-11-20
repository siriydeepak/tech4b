from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from database import get_db
import models
import schemas
import auth
import calculations

router = APIRouter(prefix="/api/exchange", tags=["exchange"])


@router.post("/calculate", response_model=schemas.ExchangeCalculateResponse)
def calculate(payload: schemas.ExchangeCalculateRequest):
    """Stateless calculation — no DB write."""
    result = calculations.compute_exchange(
        gross_weight=payload.gross_weight,
        non_gold_weight=payload.non_gold_weight,
        purity_percentage=payload.purity_percentage,
        reference_rate=payload.reference_rate,
        deductions=payload.deductions,
    )
    return schemas.ExchangeCalculateResponse(
        **result,
        deductions=payload.deductions,
    )


@router.post("/transactions", response_model=schemas.TransactionOut)
def create_transaction(
    payload: schemas.TransactionCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_role(models.UserRole.jeweller, models.UserRole.admin)),
):
    result = calculations.compute_exchange(
        gross_weight=payload.gross_weight,
        non_gold_weight=payload.non_gold_weight,
        purity_percentage=payload.purity_percentage,
        reference_rate=payload.reference_rate,
        deductions=payload.deductions,
    )

    txn = models.ExchangeTransaction(
        jeweller_id=current_user.id,
        customer_id=payload.customer_id,
        article_id=payload.article_id,
        gross_weight=result["gross_weight"],
        non_gold_weight=result["non_gold_weight"],
        net_gold_weight=result["net_gold_weight"],
        purity_percentage=result["purity_percentage"],
        reference_rate=result["reference_rate"],
        fine_gold_equivalent=result["fine_gold_equivalent"],
        metal_value=result["metal_value"],
        total_deductions=result["total_deductions"],
        final_value=result["final_value"],
        notes=payload.notes,
        status=models.TransactionStatus.confirmed,
    )
    db.add(txn)
    db.flush()   # get txn.id before deductions

    for d in payload.deductions:
        db.add(models.TransactionDeduction(
            transaction_id=txn.id,
            label=d.label,
            amount=d.amount,
        ))

    db.commit()
    db.refresh(txn)
    return txn


@router.get("/transactions", response_model=List[schemas.TransactionOut])
def list_transactions(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    q = db.query(models.ExchangeTransaction)
    if current_user.role == models.UserRole.customer:
        q = q.filter(models.ExchangeTransaction.customer_id == current_user.id)
    elif current_user.role == models.UserRole.jeweller:
        q = q.filter(models.ExchangeTransaction.jeweller_id == current_user.id)
    return q.order_by(models.ExchangeTransaction.created_at.desc()).all()


@router.get("/transactions/{txn_id}", response_model=schemas.TransactionOut)
def get_transaction(
    txn_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    txn = db.query(models.ExchangeTransaction).filter(
        models.ExchangeTransaction.id == txn_id
    ).first()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")
    # Authorization: only jeweller, customer of the txn, or admin
    if current_user.role == models.UserRole.customer and txn.customer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    return txn

