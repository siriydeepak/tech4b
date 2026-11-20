"""
seed_v2.py
-----------
Seeds initial data for AURUM Person 1 features:
  - Users: Customer, Jeweller, Admin
  - Gold rates: Last 7 days (AM + PM) across 24K, 22K, 18K, 14K
  - Jewellery: Sample items for testing
  - Transactions: Confirmed transactions with immutable calculation snapshots
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone

import auth as auth_utils
import models
from database import Base, SessionLocal, engine
from models_v2 import (
    GoldRate,
    JewelleryItem,
    RateSession,
    TransactionStatus,
    TransactionV2,
    UserRole,
    UserV2,
    VerificationStatus,
    VerificationV2,
)
from pricing_engine import FINENESS_STANDARDS, get_cached_rate, seed_today_rates
from valuation_engine import (
    CALC_VERSION,
    build_calculation_snapshot,
    compute_deductions,
    compute_final_offer,
    compute_pure_gold,
    compute_valuation,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("seed_v2")


def seed_v2():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        logger.info("--- Seeding Users ---")
        users_meta = [
            {
                "email": "customer@aurum.demo",
                "name": "Priya Sharma",
                "password": "demo1234",
                "role": UserRole.customer,
                "phone": "+91-9876543210",
            },
            {
                "email": "jeweller@aurum.demo",
                "name": "Rajan Mehta",
                "password": "demo1234",
                "role": UserRole.jeweller,
                "phone": "+91-9123456789",
                "business_name": "Mehta Gold Works",
            },
            {
                "email": "admin@aurum.demo",
                "name": "AURUM System Admin",
                "password": "admin1234",
                "role": UserRole.admin,
                "phone": "+91-9000000000",
            },
        ]

        users_v2_map = {}
        users_v1_map = {}

        for u in users_meta:
            # Seed in users_v2
            existing_v2 = db.query(UserV2).filter(UserV2.email == u["email"]).first()
            if not existing_v2:
                u_v2 = UserV2(
                    email=u["email"],
                    name=u["name"],
                    role=u["role"],
                    phone=u.get("phone"),
                    hashed_password=auth_utils.hash_password(u["password"]),
                )
                db.add(u_v2)
                db.flush()
                users_v2_map[u["role"]] = u_v2
            else:
                users_v2_map[u["role"]] = existing_v2

            # Seed in legacy users table for backward auth compatibility
            existing_v1 = db.query(models.User).filter(models.User.email == u["email"]).first()
            if not existing_v1:
                u_v1 = models.User(
                    id=users_v2_map[u["role"]].id,
                    email=u["email"],
                    full_name=u["name"],
                    hashed_password=auth_utils.hash_password(u["password"]),
                    role=u["role"],
                    phone=u.get("phone"),
                    business_name=u.get("business_name"),
                )
                db.add(u_v1)
                db.flush()
                users_v1_map[u["role"]] = u_v1
            else:
                users_v1_map[u["role"]] = existing_v1

        db.commit()

        customer = users_v2_map[UserRole.customer]
        jeweller = users_v2_map[UserRole.jeweller]

        logger.info("--- Seeding 7 Days of Gold Rates (AM & PM) ---")
        today = date.today()
        seeded_rates_count = 0

        # Base prices
        base_prices = {
            999: 7420.0,
            916: 6800.0,
            750: 5565.0,
            585: 4340.0,
        }

        for day_offset in range(7):
            cur_date = today - timedelta(days=day_offset)
            # Add slight day-to-day variance
            drift = 1.0 + (day_offset * 0.002) - 0.006

            for fineness, label in FINENESS_STANDARDS.items():
                for session_name in ("AM", "PM"):
                    pm_factor = 1.0008 if session_name == "PM" else 1.0
                    rate_val = round(base_prices[fineness] * drift * pm_factor, 2)

                    exists = (
                        db.query(GoldRate)
                        .filter(
                            GoldRate.date == cur_date,
                            GoldRate.fineness == fineness,
                            GoldRate.session == RateSession(session_name),
                        )
                        .first()
                    )
                    if not exists:
                        db.add(
                            GoldRate(
                                date=cur_date,
                                purity_label=label,
                                fineness=fineness,
                                rate_per_gram=rate_val,
                                source="IBJA",
                                session=RateSession(session_name),
                            )
                        )
                        seeded_rates_count += 1

        db.commit()
        logger.info("Seeded %d gold rate records.", seeded_rates_count)

        logger.info("--- Seeding Jewellery Items & Verifications ---")
        jewellery_item = db.query(JewelleryItem).filter(JewelleryItem.owner_id == customer.id).first()
        if not jewellery_item:
            jewellery_item = JewelleryItem(
                owner_id=customer.id,
                type="Traditional 22K Gold Necklace",
                gross_weight=24.5000,
                purity=916,
                hallmark="HUID-916-KA",
            )
            db.add(jewellery_item)
            db.flush()

            verification = VerificationV2(
                jewellery_id=jewellery_item.id,
                huid="AB1234",
                xrf_result=91.65,
                net_weight=23.8000,
                stone_weight=0.7000,
                verified_by_id=jeweller.id,
                status=VerificationStatus.verified,
            )
            db.add(verification)
            db.commit()

        logger.info("--- Seeding Sample Exchange Transaction with Immutable Snapshot ---")
        existing_txn = db.query(TransactionV2).filter(TransactionV2.customer_id == customer.id).first()
        if not existing_txn:
            net_wt = 23.8000
            fineness = 916
            purity_label = "22K"
            rate_999 = 7420.0
            rate_date = today.isoformat()
            rate_session = "AM"

            pure_gold = compute_pure_gold(net_wt, fineness)
            gross_val = compute_valuation(net_wt, fineness, rate_999)

            deduction_items = [
                {"label": "Refining & Melting Charges (1.5%)", "amount": 950.0},
                {"label": "Standard Stone / Enamel Deduction", "amount": 420.0},
            ]
            deductions_res = compute_deductions(deduction_items)
            final_offer = compute_final_offer(gross_val, deductions_res["total"])

            inputs = {
                "net_weight": net_wt,
                "fineness": fineness,
                "purity_label": purity_label,
                "rate_999": rate_999,
                "rate_date": rate_date,
                "rate_session": rate_session,
            }
            result = {
                "pure_gold_grams": pure_gold,
                "gross_valuation": gross_val,
                "deductions": deductions_res["items"],
                "total_deductions": deductions_res["total"],
                "final_offer": final_offer,
            }

            snapshot = build_calculation_snapshot(
                inputs=inputs,
                result=result,
                rate_id="ibja-demo-rate-today",
                calc_version=CALC_VERSION,
            )

            txn = TransactionV2(
                customer_id=customer.id,
                jeweller_id=jeweller.id,
                jewellery_id=jewellery_item.id if jewellery_item else None,
                snapshot=snapshot,
                status=TransactionStatus.confirmed,
            )
            db.add(txn)
            db.commit()
            logger.info("Seeded sample transaction with snapshot ID: %s", txn.id)

        logger.info("✓ Seeding completed successfully.")

    finally:
        db.close()


if __name__ == "__main__":
    seed_v2()

