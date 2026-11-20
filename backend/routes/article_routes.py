from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from database import get_db
import models
import schemas
import auth

router = APIRouter(prefix="/api/articles", tags=["articles"])


@router.post("/", response_model=schemas.ArticleOut)
def create_article(
    payload: schemas.ArticleCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    owner_id = payload.owner_id or current_user.id
    # Jewellers can register on behalf of customers; customers only for themselves
    if current_user.role == models.UserRole.customer and owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Customers can only register their own articles")

    article = models.GoldArticle(
        owner_id=owner_id,
        registered_by_id=current_user.id,
        article_name=payload.article_name,
        description=payload.description,
        hallmark=payload.hallmark,
    )
    db.add(article)
    db.commit()
    db.refresh(article)
    return article


@router.get("/", response_model=List[schemas.ArticleOut])
def list_articles(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    if current_user.role == models.UserRole.customer:
        return db.query(models.GoldArticle).filter(models.GoldArticle.owner_id == current_user.id).all()
    return db.query(models.GoldArticle).all()


@router.get("/{article_id}", response_model=schemas.ArticleOut)
def get_article(
    article_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    article = db.query(models.GoldArticle).filter(models.GoldArticle.id == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    if current_user.role == models.UserRole.customer and article.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    return article

