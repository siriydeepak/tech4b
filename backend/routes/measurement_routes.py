from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from database import get_db
import models
import schemas
import auth

router = APIRouter(prefix="/api/measurements", tags=["measurements"])


@router.post("/", response_model=schemas.MeasurementOut)
def create_measurement(
    payload: schemas.MeasurementCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_role(models.UserRole.jeweller, models.UserRole.admin)),
):
    article = db.query(models.GoldArticle).filter(models.GoldArticle.id == payload.article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    net = round(payload.gross_weight - payload.non_gold_weight, 4)
    record = models.MeasurementRecord(
        article_id=payload.article_id,
        measured_by_id=current_user.id,
        gross_weight=payload.gross_weight,
        non_gold_weight=payload.non_gold_weight,
        net_gold_weight=net,
        purity_percentage=payload.purity_percentage,
        notes=payload.notes,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.get("/article/{article_id}", response_model=List[schemas.MeasurementOut])
def list_measurements(
    article_id: str,
    db: Session = Depends(get_db),
    _: models.User = Depends(auth.get_current_user),
):
    return db.query(models.MeasurementRecord).filter(
        models.MeasurementRecord.article_id == article_id
    ).order_by(models.MeasurementRecord.measured_at.desc()).all()

