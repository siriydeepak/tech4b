from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from database import get_db
import models
import schemas
import auth

router = APIRouter(prefix="/api/verifications", tags=["verifications"])


@router.post("/", response_model=schemas.VerificationOut)
def create_verification(
    payload: schemas.VerificationCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_role(models.UserRole.jeweller, models.UserRole.admin)),
):
    article = db.query(models.GoldArticle).filter(models.GoldArticle.id == payload.article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    record = models.VerificationRecord(
        article_id=payload.article_id,
        verified_by_id=current_user.id,
        status=payload.status,
        purity_confirmed=payload.purity_confirmed,
        remarks=payload.remarks,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.get("/article/{article_id}", response_model=List[schemas.VerificationOut])
def list_verifications(
    article_id: str,
    db: Session = Depends(get_db),
    _: models.User = Depends(auth.get_current_user),
):
    return db.query(models.VerificationRecord).filter(
        models.VerificationRecord.article_id == article_id
    ).order_by(models.VerificationRecord.verified_at.desc()).all()

