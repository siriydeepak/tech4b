"""Seed demo data into a fresh database."""
from database import SessionLocal, engine, Base
import models
import auth as auth_utils


DEMO_JEWELLER = {
    "email": "jeweller@aurum.demo",
    "full_name": "Rajan Mehta",
    "password": "demo1234",
    "role": models.UserRole.jeweller,
    "business_name": "Mehta Gold Works",
    "phone": "+91-9876543210",
}

DEMO_CUSTOMER = {
    "email": "customer@aurum.demo",
    "full_name": "Priya Sharma",
    "password": "demo1234",
    "role": models.UserRole.customer,
    "phone": "+91-9123456789",
}

DEMO_ADMIN = {
    "email": "admin@aurum.demo",
    "full_name": "AURUM Admin",
    "password": "admin1234",
    "role": models.UserRole.admin,
}


def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    users_created = {}

    for data in [DEMO_ADMIN, DEMO_JEWELLER, DEMO_CUSTOMER]:
        existing = db.query(models.User).filter(models.User.email == data["email"]).first()
        if existing:
            users_created[data["role"]] = existing
            continue
        user = models.User(
            email=data["email"],
            full_name=data["full_name"],
            hashed_password=auth_utils.hash_password(data["password"]),
            role=data["role"],
            phone=data.get("phone"),
            business_name=data.get("business_name"),
        )
        db.add(user)
        db.flush()
        users_created[data["role"]] = user

    db.commit()

    jeweller = users_created[models.UserRole.jeweller]
    customer = users_created[models.UserRole.customer]

    # Seed an article
    art_exists = db.query(models.GoldArticle).filter(
        models.GoldArticle.owner_id == customer.id
    ).first()
    if not art_exists:
        article = models.GoldArticle(
            owner_id=customer.id,
            registered_by_id=jeweller.id,
            article_name="Gold Necklace (Demo)",
            description="Traditional 22K gold necklace, family heirloom",
            hallmark="916",
        )
        db.add(article)
        db.flush()

        meas = models.MeasurementRecord(
            article_id=article.id,
            measured_by_id=jeweller.id,
            gross_weight=25.5,
            non_gold_weight=1.2,
            net_gold_weight=24.3,
            purity_percentage=91.6,
            notes="Measured with certified digital scale",
        )
        db.add(meas)

        verif = models.VerificationRecord(
            article_id=article.id,
            verified_by_id=jeweller.id,
            status=models.VerificationStatus.verified,
            purity_confirmed=91.6,
            remarks="Hallmark verified, acid test passed",
        )
        db.add(verif)
        db.flush()

        from calculations import compute_exchange
        from schemas import DeductionIn
        deductions = [
            DeductionIn(label="Making charges", amount=800.0),
            DeductionIn(label="Melting & refining fee", amount=350.0),
        ]
        result = compute_exchange(25.5, 1.2, 91.6, 6200.0, deductions)

        txn = models.ExchangeTransaction(
            jeweller_id=jeweller.id,
            customer_id=customer.id,
            article_id=article.id,
            gross_weight=result["gross_weight"],
            non_gold_weight=result["non_gold_weight"],
            net_gold_weight=result["net_gold_weight"],
            purity_percentage=result["purity_percentage"],
            reference_rate=result["reference_rate"],
            fine_gold_equivalent=result["fine_gold_equivalent"],
            metal_value=result["metal_value"],
            total_deductions=result["total_deductions"],
            final_value=result["final_value"],
            status=models.TransactionStatus.completed,
            notes="Demo transaction — sample data",
        )
        db.add(txn)
        db.flush()

        for d in deductions:
            db.add(models.TransactionDeduction(
                transaction_id=txn.id,
                label=d.label,
                amount=d.amount,
            ))

        db.commit()
        print("✓ Demo data seeded")
    else:
        print("✓ Demo data already present")

    db.close()


if __name__ == "__main__":
    seed()

