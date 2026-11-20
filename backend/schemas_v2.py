"""
schemas_v2.py
-------------
Pydantic v2 request/response schemas for all AURUM v2 endpoints:
  - Gold Rates   : GoldRateOut, GoldRatesLatestResponse, GoldRatesHistoryResponse
  - Calculator   : DeductionItem, CalculatorRequest, CalculatorResponse
  - Transactions : TransactionCreateRequest, TransactionOut, SnapshotOut
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


# ── Gold Rates ─────────────────────────────────────────────────────────────────

class GoldRateOut(BaseModel):
    id:            str
    date:          date
    purity_label:  str
    fineness:      int
    rate_per_gram: float
    source:        str
    session:       Literal["AM", "PM"]
    timestamp:     datetime

    model_config = {"from_attributes": True}


class GoldRatesLatestResponse(BaseModel):
    date:    date
    session: Optional[str] = None
    rates:   List[GoldRateOut]


class GoldRatesHistoryResponse(BaseModel):
    days:  int
    rates: List[GoldRateOut]


# ── Calculator ─────────────────────────────────────────────────────────────────

class DeductionItem(BaseModel):
    label:  str   = Field(..., min_length=1, description="Human-readable deduction label")
    amount: float = Field(..., ge=0,         description="Deduction amount in INR")


class CalculatorRequest(BaseModel):
    net_weight:  float = Field(..., gt=0,  description="Net gold weight in grams")
    fineness:    Optional[int]  = Field(None, description="Fineness integer: 999/916/750/585")
    purity_label:Optional[str] = Field(None, description="Purity label: 24K/22K/18K/14K (alternative to fineness)")
    rate_999:    Optional[float]= Field(None, gt=0, description="24K rate per gram in INR; uses latest DB rate if omitted")
    deductions:  List[DeductionItem] = Field(default_factory=list)
    session:     Literal["AM", "PM"] = Field("AM", description="Rate session to use when fetching from DB")

    @model_validator(mode="after")
    def check_fineness_or_label(self) -> "CalculatorRequest":
        from valuation_engine import LABEL_TO_FINENESS, FINENESS_TO_LABEL
        if self.fineness is None and self.purity_label is None:
            raise ValueError("Provide either 'fineness' (integer) or 'purity_label' (e.g. '22K')")
        if self.purity_label and self.fineness is None:
            if self.purity_label not in LABEL_TO_FINENESS:
                raise ValueError(f"Unknown purity_label '{self.purity_label}'. Allowed: {list(LABEL_TO_FINENESS)}")
            self.fineness = LABEL_TO_FINENESS[self.purity_label]
        if self.fineness and self.purity_label is None:
            if self.fineness not in FINENESS_TO_LABEL:
                raise ValueError(f"Unknown fineness {self.fineness}. Allowed: {list(FINENESS_TO_LABEL)}")
            self.purity_label = FINENESS_TO_LABEL[self.fineness]
        return self


class CalculatorResponse(BaseModel):
    # Inputs echoed back
    net_weight:   float
    fineness:     int
    purity_label: str
    rate_999:     float
    rate_id:      Optional[str]   = None
    rate_date:    Optional[str]   = None
    rate_session: Optional[str]   = None

    # Computed results
    pure_gold_grams:  float
    gross_valuation:  float
    deductions:       List[DeductionItem]
    total_deductions: float
    final_offer:      float
    calc_version:     str


# ── Transactions ───────────────────────────────────────────────────────────────

class TransactionCreateRequest(BaseModel):
    customer_id:  str
    jewellery_id: Optional[str] = None

    # Valuation inputs
    net_weight:   float = Field(..., gt=0)
    fineness:     Optional[int]  = None
    purity_label: Optional[str] = None
    rate_999:     Optional[float]= Field(None, gt=0)
    deductions:   List[DeductionItem] = Field(default_factory=list)
    session:      Literal["AM", "PM"] = "AM"

    @model_validator(mode="after")
    def check_fineness_or_label(self) -> "TransactionCreateRequest":
        from valuation_engine import LABEL_TO_FINENESS, FINENESS_TO_LABEL
        if self.fineness is None and self.purity_label is None:
            raise ValueError("Provide either 'fineness' or 'purity_label'")
        if self.purity_label and self.fineness is None:
            if self.purity_label not in LABEL_TO_FINENESS:
                raise ValueError(f"Unknown purity_label '{self.purity_label}'")
            self.fineness = LABEL_TO_FINENESS[self.purity_label]
        if self.fineness and self.purity_label is None:
            if self.fineness not in FINENESS_TO_LABEL:
                raise ValueError(f"Unknown fineness {self.fineness}")
            self.purity_label = FINENESS_TO_LABEL[self.fineness]
        return self


class TransactionOut(BaseModel):
    id:           str
    customer_id:  str
    jeweller_id:  str
    jewellery_id: Optional[str]
    status:       str
    snapshot:     Optional[dict[str, Any]] = None
    created_at:   datetime

    model_config = {"from_attributes": True}


class SnapshotOut(BaseModel):
    transaction_id: str
    snapshot:       dict[str, Any]
