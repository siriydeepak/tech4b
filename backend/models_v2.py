"""
models_v2.py
------------
SQLAlchemy ORM models for the AURUM v2 schema.
Covers all 7 tables required by the architecture:
  users, jewellery, verifications, gold_rates, transactions, evidence, anomaly_flags

Compatible with both Supabase PostgreSQL and local SQLite (dev fallback).
"""

from __future__ import annotations

import enum
import uuid

from sqlalchemy import (
    JSON,
    Column,
    Date,
    DateTime,
    Enum as SAEnum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from database import Base


# ── Helpers ────────────────────────────────────────────────────────────────────

def gen_uuid() -> str:
    return str(uuid.uuid4())


# ── Enums ──────────────────────────────────────────────────────────────────────

class UserRole(str, enum.Enum):
    customer = "customer"
    jeweller = "jeweller"
    admin    = "admin"


class VerificationStatus(str, enum.Enum):
    pending  = "pending"
    verified = "verified"
    disputed = "disputed"


class TransactionStatus(str, enum.Enum):
    draft     = "draft"
    confirmed = "confirmed"
    completed = "completed"
    cancelled = "cancelled"


class RateSession(str, enum.Enum):
    AM = "AM"
    PM = "PM"


class EvidenceType(str, enum.Enum):
    photo         = "photo"
    xrf_cert      = "xrf_cert"
    bill          = "bill"
    scale_receipt = "scale_receipt"


class FlagType(str, enum.Enum):
    purity_mismatch           = "purity_mismatch"
    weight_variance           = "weight_variance"
    hallmark_mismatch         = "hallmark_mismatch"
    incomplete_evidence       = "incomplete_evidence"
    stale_rate                = "stale_rate"
    disproportionate_deduction = "disproportionate_deduction"


class FlagSeverity(str, enum.Enum):
    low    = "low"
    medium = "medium"
    high   = "high"


# ── 1. users ──────────────────────────────────────────────────────────────────

class UserV2(Base):
    """
    Central user table.  Mirrors Supabase auth.users (email as PK surrogate).
    'name' maps to full display name; role drives RLS policies.
    """
    __tablename__ = "users_v2"

    id              = Column(String, primary_key=True, default=gen_uuid)
    name            = Column(String, nullable=False)
    role            = Column(SAEnum(UserRole), default=UserRole.customer, nullable=False)
    email           = Column(String, unique=True, nullable=False, index=True)
    phone           = Column(String, nullable=True)
    hashed_password = Column(String, nullable=False)
    created_at      = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    jewellery_items       = relationship("JewelleryItem",    back_populates="owner",       foreign_keys="JewelleryItem.owner_id")
    verifications_done    = relationship("VerificationV2",   back_populates="verified_by", foreign_keys="VerificationV2.verified_by_id")
    customer_transactions = relationship("TransactionV2",    back_populates="customer",    foreign_keys="TransactionV2.customer_id")
    jeweller_transactions = relationship("TransactionV2",    back_populates="jeweller",    foreign_keys="TransactionV2.jeweller_id")
    uploaded_evidence     = relationship("EvidenceFile",     back_populates="uploaded_by", foreign_keys="EvidenceFile.uploaded_by_id")


# ── 2. jewellery ──────────────────────────────────────────────────────────────

class JewelleryItem(Base):
    """
    Physical gold jewellery item owned by a customer.
    purity stores the fineness integer (e.g. 916 for 22K).
    """
    __tablename__ = "jewellery"

    id          = Column(String, primary_key=True, default=gen_uuid)
    owner_id    = Column(String, ForeignKey("users_v2.id"), nullable=False, index=True)
    type        = Column(String, nullable=False)              # e.g. "necklace", "bangle"
    gross_weight= Column(Float,  nullable=False)              # grams
    purity      = Column(Integer, nullable=False)             # fineness: 999/916/750/585
    hallmark    = Column(String, nullable=True)               # BIS hallmark code
    created_at  = Column(DateTime(timezone=True), server_default=func.now())

    owner         = relationship("UserV2",        back_populates="jewellery_items", foreign_keys=[owner_id])
    verifications = relationship("VerificationV2", back_populates="jewellery",      foreign_keys="VerificationV2.jewellery_id")
    transactions  = relationship("TransactionV2",  back_populates="jewellery",      foreign_keys="TransactionV2.jewellery_id")


# ── 3. verifications ──────────────────────────────────────────────────────────

class VerificationV2(Base):
    """
    XRF/assay verification record for a jewellery item.
    xrf_result holds the actual measured fineness (float).
    huid = Hallmark Unique ID (6-character BIS code).
    """
    __tablename__ = "verifications"

    id            = Column(String,  primary_key=True, default=gen_uuid)
    jewellery_id  = Column(String,  ForeignKey("jewellery.id"), nullable=False, index=True)
    huid          = Column(String(6), nullable=True)           # BIS HUID
    xrf_result    = Column(Float,   nullable=True)             # measured fineness
    net_weight    = Column(Float,   nullable=True)             # grams after stone deduction
    stone_weight  = Column(Float,   nullable=True)             # grams of stones
    verified_by_id= Column(String,  ForeignKey("users_v2.id"), nullable=True, index=True)
    status        = Column(SAEnum(VerificationStatus), default=VerificationStatus.pending)
    created_at    = Column(DateTime(timezone=True), server_default=func.now())

    jewellery   = relationship("JewelleryItem", back_populates="verifications", foreign_keys=[jewellery_id])
    verified_by = relationship("UserV2",        back_populates="verifications_done", foreign_keys=[verified_by_id])


# ── 4. gold_rates ─────────────────────────────────────────────────────────────

class GoldRate(Base):
    """
    Daily IBJA gold rate record.
    One row per (date, fineness, session) combination.
    """
    __tablename__ = "gold_rates"

    id            = Column(String,  primary_key=True, default=gen_uuid)
    date          = Column(Date,    nullable=False, index=True)
    purity_label  = Column(String,  nullable=False)            # "24K" / "22K" / "18K" / "14K"
    fineness      = Column(Integer, nullable=False)            # 999 / 916 / 750 / 585
    rate_per_gram = Column(Float,   nullable=False)            # INR per gram
    source        = Column(String,  nullable=False, default="IBJA")
    session       = Column(SAEnum(RateSession), nullable=False)
    timestamp     = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_gold_rates_date_fineness_session", "date", "fineness", "session", unique=True),
    )


# ── 5. transactions ───────────────────────────────────────────────────────────

class TransactionV2(Base):
    """
    Gold exchange transaction with an immutable snapshot JSON column.
    The snapshot stores ALL inputs + rate + deductions + formula version
    frozen at confirmation time — used for dispute replay.
    """
    __tablename__ = "transactions"

    id           = Column(String,  primary_key=True, default=gen_uuid)
    customer_id  = Column(String,  ForeignKey("users_v2.id"), nullable=False, index=True)
    jeweller_id  = Column(String,  ForeignKey("users_v2.id"), nullable=False, index=True)
    jewellery_id = Column(String,  ForeignKey("jewellery.id"), nullable=True,  index=True)

    # Immutable snapshot — all inputs frozen at confirmation
    snapshot     = Column(JSON,    nullable=True)

    status       = Column(SAEnum(TransactionStatus), default=TransactionStatus.draft)
    created_at   = Column(DateTime(timezone=True), server_default=func.now())

    customer  = relationship("UserV2",       back_populates="customer_transactions", foreign_keys=[customer_id])
    jeweller  = relationship("UserV2",       back_populates="jeweller_transactions", foreign_keys=[jeweller_id])
    jewellery = relationship("JewelleryItem", back_populates="transactions",          foreign_keys=[jewellery_id])
    evidence  = relationship("EvidenceFile",  back_populates="transaction",           cascade="all, delete-orphan")
    flags     = relationship("AnomalyFlag",   back_populates="transaction",           cascade="all, delete-orphan")


# ── 6. evidence ───────────────────────────────────────────────────────────────

class EvidenceFile(Base):
    """
    Uploaded evidence (photos, XRF certs, bills, scale receipts) for a transaction.
    """
    __tablename__ = "evidence"

    id             = Column(String,  primary_key=True, default=gen_uuid)
    transaction_id = Column(String,  ForeignKey("transactions.id"), nullable=False, index=True)
    file_url       = Column(Text,    nullable=False)
    evidence_type  = Column(SAEnum(EvidenceType), nullable=False)
    uploaded_by_id = Column(String,  ForeignKey("users_v2.id"), nullable=False, index=True)
    timestamp      = Column(DateTime(timezone=True), server_default=func.now())

    transaction = relationship("TransactionV2", back_populates="evidence",        foreign_keys=[transaction_id])
    uploaded_by = relationship("UserV2",        back_populates="uploaded_evidence", foreign_keys=[uploaded_by_id])


# ── 7. anomaly_flags ──────────────────────────────────────────────────────────

class AnomalyFlag(Base):
    """
    Flags raised by the system when anomalies are detected in a transaction.
    """
    __tablename__ = "anomaly_flags"

    id             = Column(String,   primary_key=True, default=gen_uuid)
    transaction_id = Column(String,   ForeignKey("transactions.id"), nullable=False, index=True)
    flag_type      = Column(SAEnum(FlagType),     nullable=False)
    severity       = Column(SAEnum(FlagSeverity), nullable=False)
    explanation    = Column(Text,     nullable=True)
    created_at     = Column(DateTime(timezone=True), server_default=func.now())

    transaction = relationship("TransactionV2", back_populates="flags", foreign_keys=[transaction_id])
