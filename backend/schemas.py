from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, List
from datetime import datetime
from models import UserRole, VerificationStatus, TransactionStatus


# ── Auth ──────────────────────────────────────────────────────────────────────

class UserRegister(BaseModel):
    email: EmailStr
    full_name: str = Field(..., min_length=2, max_length=100)
    password: str = Field(..., min_length=6)
    role: UserRole = UserRole.customer
    phone: Optional[str] = None
    business_name: Optional[str] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserOut"


class UserOut(BaseModel):
    id: str
    email: str
    full_name: str
    role: UserRole
    phone: Optional[str]
    business_name: Optional[str]
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


Token.model_rebuild()


# ── Gold Articles ─────────────────────────────────────────────────────────────

class ArticleCreate(BaseModel):
    article_name: str = Field(..., min_length=2, max_length=200)
    description: Optional[str] = None
    hallmark: Optional[str] = None
    owner_id: Optional[str] = None   # jeweller can register on behalf of customer


class ArticleOut(BaseModel):
    id: str
    owner_id: str
    article_name: str
    description: Optional[str]
    hallmark: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Measurement ───────────────────────────────────────────────────────────────

class MeasurementCreate(BaseModel):
    article_id: str
    gross_weight: float = Field(..., gt=0)
    non_gold_weight: float = Field(..., ge=0)
    purity_percentage: float = Field(..., gt=0, le=100)
    notes: Optional[str] = None

    @field_validator("non_gold_weight")
    @classmethod
    def non_gold_less_than_gross(cls, v, info):
        gross = info.data.get("gross_weight")
        if gross is not None and v >= gross:
            raise ValueError("Non-gold weight must be less than gross weight")
        return v


class MeasurementOut(BaseModel):
    id: str
    article_id: str
    gross_weight: float
    non_gold_weight: float
    net_gold_weight: float
    purity_percentage: float
    notes: Optional[str]
    measured_at: datetime
    measured_by_id: str

    model_config = {"from_attributes": True}


# ── Verification ──────────────────────────────────────────────────────────────

class VerificationCreate(BaseModel):
    article_id: str
    purity_confirmed: Optional[float] = Field(None, gt=0, le=100)
    status: VerificationStatus = VerificationStatus.verified
    remarks: Optional[str] = None


class VerificationOut(BaseModel):
    id: str
    article_id: str
    verified_by_id: str
    status: VerificationStatus
    purity_confirmed: Optional[float]
    remarks: Optional[str]
    verified_at: datetime

    model_config = {"from_attributes": True}


# ── Exchange ──────────────────────────────────────────────────────────────────

class DeductionIn(BaseModel):
    label: str = Field(..., min_length=1, max_length=100)
    amount: float = Field(..., ge=0)


class DeductionOut(BaseModel):
    id: str
    label: str
    amount: float

    model_config = {"from_attributes": True}


class ExchangeCalculateRequest(BaseModel):
    gross_weight: float = Field(..., gt=0)
    non_gold_weight: float = Field(..., ge=0)
    purity_percentage: float = Field(..., gt=0, le=100)
    reference_rate: float = Field(..., gt=0)
    deductions: List[DeductionIn] = []

    @field_validator("non_gold_weight")
    @classmethod
    def validate_non_gold(cls, v, info):
        gross = info.data.get("gross_weight")
        if gross is not None and v >= gross:
            raise ValueError("Non-gold weight must be less than gross weight")
        return v


class ExchangeCalculateResponse(BaseModel):
    gross_weight: float
    non_gold_weight: float
    net_gold_weight: float
    purity_percentage: float
    reference_rate: float
    fine_gold_equivalent: float
    metal_value: float
    deductions: List[DeductionIn]
    total_deductions: float
    final_value: float


class TransactionCreate(BaseModel):
    customer_id: str
    article_id: Optional[str] = None
    gross_weight: float = Field(..., gt=0)
    non_gold_weight: float = Field(..., ge=0)
    purity_percentage: float = Field(..., gt=0, le=100)
    reference_rate: float = Field(..., gt=0)
    deductions: List[DeductionIn] = []
    notes: Optional[str] = None

    @field_validator("non_gold_weight")
    @classmethod
    def validate_non_gold(cls, v, info):
        gross = info.data.get("gross_weight")
        if gross is not None and v >= gross:
            raise ValueError("Non-gold weight must be less than gross weight")
        return v


class TransactionOut(BaseModel):
    id: str
    jeweller_id: str
    customer_id: str
    article_id: Optional[str]
    gross_weight: float
    non_gold_weight: float
    net_gold_weight: float
    purity_percentage: float
    reference_rate: float
    fine_gold_equivalent: float
    metal_value: float
    total_deductions: float
    final_value: float
    status: TransactionStatus
    notes: Optional[str]
    created_at: datetime
    deductions: List[DeductionOut] = []

    model_config = {"from_attributes": True}

