from sqlalchemy import (
    Column, String, Float, Integer, Boolean,
    DateTime, ForeignKey, Text, Enum as SAEnum
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
import uuid
from database import Base


def gen_uuid():
    return str(uuid.uuid4())


class UserRole(str, enum.Enum):
    customer = "customer"
    jeweller = "jeweller"
    admin = "admin"


class VerificationStatus(str, enum.Enum):
    pending = "pending"
    verified = "verified"
    disputed = "disputed"


class TransactionStatus(str, enum.Enum):
    draft = "draft"
    confirmed = "confirmed"
    completed = "completed"
    cancelled = "cancelled"


# ── Users ────────────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=gen_uuid)
    email = Column(String, unique=True, nullable=False, index=True)
    full_name = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(SAEnum(UserRole), default=UserRole.customer, nullable=False)
    phone = Column(String, nullable=True)
    business_name = Column(String, nullable=True)   # for jewellers
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    articles = relationship("GoldArticle", back_populates="owner", foreign_keys="GoldArticle.owner_id")
    jeweller_transactions = relationship("ExchangeTransaction", back_populates="jeweller", foreign_keys="ExchangeTransaction.jeweller_id")
    customer_transactions = relationship("ExchangeTransaction", back_populates="customer", foreign_keys="ExchangeTransaction.customer_id")


# ── Gold Articles ─────────────────────────────────────────────────────────────

class GoldArticle(Base):
    __tablename__ = "gold_articles"

    id = Column(String, primary_key=True, default=gen_uuid)
    owner_id = Column(String, ForeignKey("users.id"), nullable=False)
    registered_by_id = Column(String, ForeignKey("users.id"), nullable=True)
    article_name = Column(String, nullable=False)       # e.g. "Gold Necklace"
    description = Column(Text, nullable=True)
    hallmark = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    owner = relationship("User", back_populates="articles", foreign_keys=[owner_id])
    measurements = relationship("MeasurementRecord", back_populates="article")
    verifications = relationship("VerificationRecord", back_populates="article")


# ── Measurement Records ───────────────────────────────────────────────────────

class MeasurementRecord(Base):
    __tablename__ = "measurement_records"

    id = Column(String, primary_key=True, default=gen_uuid)
    article_id = Column(String, ForeignKey("gold_articles.id"), nullable=False)
    measured_by_id = Column(String, ForeignKey("users.id"), nullable=False)
    gross_weight = Column(Float, nullable=False)          # grams
    non_gold_weight = Column(Float, nullable=False)       # grams (stones, solder etc.)
    net_gold_weight = Column(Float, nullable=False)       # gross - non_gold
    purity_percentage = Column(Float, nullable=False)     # 0-100
    notes = Column(Text, nullable=True)
    measured_at = Column(DateTime(timezone=True), server_default=func.now())

    article = relationship("GoldArticle", back_populates="measurements")
    measured_by = relationship("User", foreign_keys=[measured_by_id])


# ── Verification Records ──────────────────────────────────────────────────────

class VerificationRecord(Base):
    __tablename__ = "verification_records"

    id = Column(String, primary_key=True, default=gen_uuid)
    article_id = Column(String, ForeignKey("gold_articles.id"), nullable=False)
    verified_by_id = Column(String, ForeignKey("users.id"), nullable=False)
    status = Column(SAEnum(VerificationStatus), default=VerificationStatus.pending)
    purity_confirmed = Column(Float, nullable=True)      # confirmed purity %
    remarks = Column(Text, nullable=True)
    verified_at = Column(DateTime(timezone=True), server_default=func.now())

    article = relationship("GoldArticle", back_populates="verifications")
    verified_by = relationship("User", foreign_keys=[verified_by_id])


# ── Exchange Transactions ─────────────────────────────────────────────────────

class ExchangeTransaction(Base):
    __tablename__ = "exchange_transactions"

    id = Column(String, primary_key=True, default=gen_uuid)
    jeweller_id = Column(String, ForeignKey("users.id"), nullable=False)
    customer_id = Column(String, ForeignKey("users.id"), nullable=False)
    article_id = Column(String, ForeignKey("gold_articles.id"), nullable=True)

    # Inputs
    gross_weight = Column(Float, nullable=False)
    non_gold_weight = Column(Float, nullable=False)
    net_gold_weight = Column(Float, nullable=False)
    purity_percentage = Column(Float, nullable=False)
    reference_rate = Column(Float, nullable=False)        # ₹ per gram (24K)

    # Computed (by backend)
    fine_gold_equivalent = Column(Float, nullable=False)  # net * purity/100
    metal_value = Column(Float, nullable=False)           # fine_gold * rate
    total_deductions = Column(Float, nullable=False)
    final_value = Column(Float, nullable=False)           # metal_value - deductions

    status = Column(SAEnum(TransactionStatus), default=TransactionStatus.draft)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    jeweller = relationship("User", back_populates="jeweller_transactions", foreign_keys=[jeweller_id])
    customer = relationship("User", back_populates="customer_transactions", foreign_keys=[customer_id])
    deductions = relationship("TransactionDeduction", back_populates="transaction", cascade="all, delete-orphan")


# ── Transaction Deductions ────────────────────────────────────────────────────

class TransactionDeduction(Base):
    __tablename__ = "transaction_deductions"

    id = Column(String, primary_key=True, default=gen_uuid)
    transaction_id = Column(String, ForeignKey("exchange_transactions.id"), nullable=False)
    label = Column(String, nullable=False)    # e.g. "Making charges", "Melting fee"
    amount = Column(Float, nullable=False)

    transaction = relationship("ExchangeTransaction", back_populates="deductions")

