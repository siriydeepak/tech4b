"""
pricing_engine.py
-----------------
Gold Pricing Engine for AURUM.

Responsibilities:
  1. IBJA fineness standards definition (999 / 916 / 750 / 585)
  2. fetch_ibja_rates()   — simulates IBJA daily rates (TODO: replace with real API)
  3. get_cached_rate()    — DB-first lookup with weekend/holiday fallback
  4. seed_today_rates()   — idempotent daily seeder

NOTE: IBJA (India Bullion and Jewellers Association) does not currently provide a
      free public REST API.  The function below uses a date-seeded simulation with
      ±0.3 % daily variation around ₹7,400 / gram (24K) as a realistic placeholder.

      TODO: Replace `fetch_ibja_rates()` with a real IBJA integration once an
            official data feed or licensed data-provider endpoint is available.
            Candidates: IBJA official website scraping (rate table),
            or commercial providers such as metals-api.com / commodities-api.com.
"""

from __future__ import annotations

import logging
import random
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────────

IBJA_BASE_RATE_24K_PER_GRAM: float = 7400.0  # INR, approximate 2024/2025 price

FINENESS_STANDARDS: dict[int, str] = {
    999: "24K",
    916: "22K",
    750: "18K",
    585: "14K",
}

LABEL_TO_FINENESS: dict[str, int] = {v: k for k, v in FINENESS_STANDARDS.items()}

# Simple public holiday list (India — extend as needed)
_PUBLIC_HOLIDAYS: set[date] = {
    # 2025 approximate dates
    date(2025, 1, 26),  # Republic Day
    date(2025, 8, 15),  # Independence Day
    date(2025, 10, 2),  # Gandhi Jayanti
    date(2025, 11, 1),  # Diwali (approximate)
    date(2026, 1, 26),
    date(2026, 8, 15),
}


# ── Helpers ────────────────────────────────────────────────────────────────────

def _is_market_closed(d: date) -> bool:
    """Returns True if the IBJA market is closed on the given date."""
    return d.weekday() >= 5 or d in _PUBLIC_HOLIDAYS  # Sat=5, Sun=6


def _last_market_day(d: date) -> date:
    """Returns the most recent market-open day on or before `d`."""
    while _is_market_closed(d):
        d -= timedelta(days=1)
    return d


def _daily_variation_factor(d: date, session: str, fineness: int) -> float:
    """
    Deterministic ±0.3 % daily variation seeded by (date, session, fineness).
    Using random.seed ensures the same value is returned for the same inputs.
    """
    rng = random.Random(f"{d.isoformat()}-{session}-{fineness}")
    return 1.0 + rng.uniform(-0.003, 0.003)


def _simulated_rate(fineness: int, d: date, session: str) -> float:
    """
    Simulates an IBJA daily rate for the given fineness / date / session.
    Rate is derived from the 24K base, proportionally scaled by fineness.
    A small intra-day PM premium (≈ 0.05 %) is added.
    """
    base_24k = IBJA_BASE_RATE_24K_PER_GRAM * _daily_variation_factor(d, "base", fineness)
    rate = base_24k * (fineness / 999)
    if session == "PM":
        rate *= 1.0005          # slight PM premium
    # Apply per-session micro-variation for realism
    rate *= _daily_variation_factor(d, session, fineness)
    return round(rate, 2)


# ── Public API ─────────────────────────────────────────────────────────────────

def fetch_ibja_rates(target_date: Optional[date] = None) -> list[dict]:
    """
    Returns a list of simulated IBJA rates for all purity × session combinations
    for `target_date` (defaults to today).

    Each dict contains:
        date, purity_label, fineness, rate_per_gram, source, session

    TODO: Replace this simulation with a real IBJA data-feed call.
          Example real endpoint (once available):
              GET https://api.ibja.co/rates?date=YYYY-MM-DD
          Requires authentication / licensing from IBJA.
    """
    target_date = target_date or date.today()
    # If market is closed, do NOT generate rates for that day
    # (caller should use last known rates instead)
    if _is_market_closed(target_date):
        logger.info(
            "Market closed on %s — no new rates generated (use last known).", target_date
        )
        return []

    records: list[dict] = []
    for fineness, label in FINENESS_STANDARDS.items():
        for session in ("AM", "PM"):
            records.append(
                {
                    "date":          target_date,
                    "purity_label":  label,
                    "fineness":      fineness,
                    "rate_per_gram": _simulated_rate(fineness, target_date, session),
                    "source":        "IBJA",
                    "session":       session,
                }
            )
    return records


def get_cached_rate(
    db: Session,
    fineness: int,
    session: str = "AM",
    target_date: Optional[date] = None,
) -> Optional[dict]:
    """
    Returns the gold rate dict for `fineness` + `session` on `target_date`.

    Lookup strategy:
      1. Check DB for today's rate.
      2. If not found (weekend / holiday / not-yet-seeded), walk back up to 10 days.
      3. If still nothing, fall back to simulated rate on the last market day.

    Returns a dict with keys: id, date, purity_label, fineness, rate_per_gram, source, session.
    Returns None only if `fineness` is unrecognised.
    """
    from models_v2 import GoldRate  # local import to avoid circular deps at module level

    if fineness not in FINENESS_STANDARDS:
        logger.error("Unknown fineness %s", fineness)
        return None

    target_date = target_date or date.today()

    # Walk back up to 10 days looking for a DB record
    search_date = target_date
    for _ in range(10):
        row = (
            db.query(GoldRate)
            .filter(
                GoldRate.fineness == fineness,
                GoldRate.session  == session,
                GoldRate.date     == search_date,
            )
            .first()
        )
        if row:
            return {
                "id":            row.id,
                "date":          row.date,
                "purity_label":  row.purity_label,
                "fineness":      row.fineness,
                "rate_per_gram": row.rate_per_gram,
                "source":        row.source,
                "session":       row.session,
            }
        search_date -= timedelta(days=1)

    # Fallback: generate a simulated rate for the last market day
    fallback_date = _last_market_day(target_date)
    logger.warning(
        "No DB rate found for fineness=%s session=%s — using simulated fallback for %s",
        fineness, session, fallback_date,
    )
    return {
        "id":            f"simulated-{fallback_date}-{fineness}-{session}",
        "date":          fallback_date,
        "purity_label":  FINENESS_STANDARDS[fineness],
        "fineness":      fineness,
        "rate_per_gram": _simulated_rate(fineness, fallback_date, session),
        "source":        "IBJA_SIMULATED",
        "session":       session,
    }


def seed_today_rates(db: Session) -> int:
    """
    Idempotent seeder: inserts today's AM + PM rates for all 4 purities into
    `gold_rates` if they don't already exist.

    Returns the number of rows inserted (0 if already seeded or market is closed).
    """
    from models_v2 import GoldRate  # local import

    today = date.today()

    # Skip weekends / holidays — IBJA doesn't publish rates on those days
    if _is_market_closed(today):
        logger.info("seed_today_rates: market closed on %s, skipping.", today)
        return 0

    records = fetch_ibja_rates(today)
    inserted = 0

    for rec in records:
        exists = (
            db.query(GoldRate)
            .filter(
                GoldRate.date     == rec["date"],
                GoldRate.fineness == rec["fineness"],
                GoldRate.session  == rec["session"],
            )
            .first()
        )
        if not exists:
            db.add(
                GoldRate(
                    date          = rec["date"],
                    purity_label  = rec["purity_label"],
                    fineness      = rec["fineness"],
                    rate_per_gram = rec["rate_per_gram"],
                    source        = rec["source"],
                    session       = rec["session"],
                )
            )
            inserted += 1

    if inserted:
        db.commit()
        logger.info("seed_today_rates: inserted %d rate rows for %s.", inserted, today)
    else:
        logger.debug("seed_today_rates: rates already present for %s.", today)

    return inserted



def get_all_cached_rates(
    db: Session,
    target_date: Optional[date] = None,
    session: Optional[str] = None,
) -> list[GoldRate]:
    """
    Returns latest rates for all fineness standards (999, 916, 750, 585).
    Walks back dates if target_date has no records.
    """
    from models_v2 import GoldRate

    target_date = target_date or date.today()
    search_date = target_date
    res: list[GoldRate] = []

    # Try to find records for search_date, stepping back up to 10 days if needed
    for _ in range(10):
        q = db.query(GoldRate).filter(GoldRate.date == search_date)
        if session:
            q = q.filter(GoldRate.session == session)
        records = q.order_by(GoldRate.fineness.desc()).all()
        if records:
            res = records
            break
        search_date -= timedelta(days=1)

    # If still empty (e.g. fresh DB before seeding or weekend with no seed), generate
    if not res:
        fallback_date = _last_market_day(target_date)
        use_session = session or "AM"
        res = []
        for fineness, label in FINENESS_STANDARDS.items():
            rate_val = _simulated_rate(fineness, fallback_date, use_session)
            gr = GoldRate(
                id=f"sim-{fallback_date}-{fineness}-{use_session}",
                date=fallback_date,
                purity_label=label,
                fineness=fineness,
                rate_per_gram=rate_val,
                source="IBJA_SIMULATED",
                session=use_session,
            )
            res.append(gr)

    return res


def get_history_rates(
    db: Session,
    days: int = 7,
) -> list[GoldRate]:
    """
    Returns rate history ordered by date descending, session, and fineness.
    If DB has fewer days, generates simulated history so charts always have full data.
    """
    from models_v2 import GoldRate

    cutoff_date = date.today() - timedelta(days=days)
    records = (
        db.query(GoldRate)
        .filter(GoldRate.date >= cutoff_date)
        .order_by(GoldRate.date.desc(), GoldRate.session.asc(), GoldRate.fineness.desc())
        .all()
    )

    if len(records) >= days * 4:
        return records

    # Seed historical simulated rates if sparse
    today = date.today()
    for d_offset in range(days):
        d = today - timedelta(days=d_offset)
        if not _is_market_closed(d):
            for fineness, label in FINENESS_STANDARDS.items():
                for s in ("AM", "PM"):
                    exists = db.query(GoldRate).filter(
                        GoldRate.date == d,
                        GoldRate.fineness == fineness,
                        GoldRate.session == s,
                    ).first()
                    if not exists:
                        db.add(GoldRate(
                            date=d,
                            purity_label=label,
                            fineness=fineness,
                            rate_per_gram=_simulated_rate(fineness, d, s),
                            source="IBJA",
                            session=s,
                        ))
    db.commit()

    return (
        db.query(GoldRate)
        .filter(GoldRate.date >= cutoff_date)
        .order_by(GoldRate.date.desc(), GoldRate.session.asc(), GoldRate.fineness.desc())
        .all()
    )
