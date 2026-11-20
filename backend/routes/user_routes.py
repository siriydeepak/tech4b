from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from database import get_db
import models
import schemas
import auth

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("/", response_model=List[schemas.UserOut])
def list_users(
    db: Session = Depends(get_db),
    _: models.User = Depends(auth.require_role(models.UserRole.admin, models.UserRole.jeweller)),
):
    return db.query(models.User).all()


@router.get("/customers", response_model=List[schemas.UserOut])
def list_customers(
    db: Session = Depends(get_db),
    _: models.User = Depends(auth.require_role(models.UserRole.jeweller, models.UserRole.admin)),
):
    return db.query(models.User).filter(models.User.role == models.UserRole.customer).all()


@router.get("/{user_id}", response_model=schemas.UserOut)
def get_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    if current_user.id != user_id and current_user.role not in (
        models.UserRole.admin, models.UserRole.jeweller
    ):
        raise HTTPException(status_code=403, detail="Not authorized")
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

