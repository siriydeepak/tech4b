"""
valuation_engine.py
-------------------
Pure financial math for gold exchange valuation.
NO I/O, NO database access, NO side effects — only deterministic calculations.

Formula reference:
  Pure Gold (g)   = Wn × (P / 999)
  Valuation V     = Wn × R999 × (P / 999)
  Final Offer     = V − D
where:
  Wn   = net gold weight (grams)
  P    = measured fineness (integer: 999 / 916 / 750 / 585)
  R999 = 24K benchmark rate per gram (INR)
  D    = sum of itemised deductions
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

CALC_VERSION = "1.0.0"

# Supported fineness values and their purity labels
FINENESS_TO_LABEL: dict[int, str] = {
    999: "24K",
    916: "22K",
    750: "18K",
    585: "14K",
}

LABEL_TO_FINENESS: dict[str, int] = {v: k for k, v in FINENESS_TO_LABEL.items()}


# ── Core formulas ──────────────────────────────────────────────────────────────

def compute_pure_gold(net_weight: float, fineness: int) -> float:
    """
    Returns the pure-gold equivalent weight in grams.
    Pure Gold (g) = Wn × (P / 999)

    Args:
        net_weight: Net gold weight in grams (after deducting stones/solder).
        fineness:   Integer fineness (999, 916, 750, 585).

    Returns:
        Pure gold grams (rounded to 4 decimal places).
    """
    if net_weight <= 0:
        raise ValueError(f"net_weight must be > 0, got {net_weight}")
    if fineness not in FINENESS_TO_LABEL:
        raise ValueError(
            f"Unsupported fineness {fineness}. "
            f"Allowed values: {list(FINENESS_TO_LABEL)}"
        )
    return round(net_weight * (fineness / 999), 4)


def compute_valuation(net_weight: float, fineness: int, rate_999: float) -> float:
    """
    Returns the gross valuation in INR.
    V = Wn × R999 × (P / 999)

    Args:
        net_weight: Net gold weight in grams.
        fineness:   Integer fineness (999, 916, 750, 585).
        rate_999:   24K benchmark rate per gram in INR.

    Returns:
        Gross valuation in INR (rounded to 2 decimal places).
    """
    if rate_999 <= 0:
        raise ValueError(f"rate_999 must be > 0, got {rate_999}")
    pure_gold = compute_pure_gold(net_weight, fineness)
    return round(pure_gold * rate_999, 2)


def compute_deductions(deduction_items: list[dict]) -> dict:
    """
    Accepts a list of deduction dicts with keys 'label' and 'amount'.
    Returns an itemised breakdown dict plus a 'total' key.

    Args:
        deduction_items: e.g. [{"label": "Making charges", "amount": 500.0}, ...]

    Returns:
        {
            "items": [{"label": str, "amount": float}, ...],
            "total": float
        }
    """
    items: list[dict] = []
    total = 0.0
    for item in deduction_items:
        label = str(item.get("label", "")).strip()
        amount = float(item.get("amount", 0))
        if amount < 0:
            raise ValueError(f"Deduction amount cannot be negative (label='{label}')")
        items.append({"label": label, "amount": round(amount, 2)})
        total += amount
    return {"items": items, "total": round(total, 2)}


def compute_final_offer(valuation: float, total_deductions: float) -> float:
    """
    Final Offer = V − D

    Args:
        valuation:        Gross valuation in INR.
        total_deductions: Sum of all deductions in INR.

    Returns:
        Final offer in INR (rounded to 2 decimal places).
        Can be 0 at minimum (never negative in a fair offer).
    """
    return round(max(0.0, valuation - total_deductions), 2)


# ── Snapshot builder ───────────────────────────────────────────────────────────

def build_calculation_snapshot(
    inputs: dict[str, Any],
    result: dict[str, Any],
    rate_id: str,
    calc_version: str = CALC_VERSION,
) -> dict[str, Any]:
    """
    Builds the immutable snapshot dict frozen at confirmation time.
    This dict is stored verbatim in the transactions.snapshot JSON column
    and must never be mutated after creation.

    Required keys in `inputs`:
        net_weight, fineness, purity_label, rate_999, rate_date, rate_session

    Required keys in `result`:
        pure_gold_grams, gross_valuation, deductions (list), total_deductions, final_offer

    Returns:
        Snapshot dict with all keys defined in the architecture spec.
    """
    now_utc = datetime.now(timezone.utc).isoformat()

    snapshot: dict[str, Any] = {
        # ── Inputs (frozen) ──────────────────────────────────────────
        "net_weight":        inputs["net_weight"],
        "fineness":          inputs["fineness"],          # integer
        "purity_label":      inputs["purity_label"],      # e.g. "22K"
        "rate_999":          inputs["rate_999"],           # INR per gram
        "rate_id":           rate_id,
        "rate_date":         inputs.get("rate_date", ""),
        "rate_session":      inputs.get("rate_session", ""),
        # ── Results (computed at confirmation time) ──────────────────
        "pure_gold_grams":   result["pure_gold_grams"],
        "gross_valuation":   result["gross_valuation"],
        "deductions":        result["deductions"],         # list of {label, amount}
        "total_deductions":  result["total_deductions"],
        "final_offer":       result["final_offer"],
        # ── Audit / versioning ───────────────────────────────────────
        "calc_version":      calc_version,
        "confirmed_at":      now_utc,
    }
    return snapshot
