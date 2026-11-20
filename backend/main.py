from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import engine, Base
from config import settings
import models
import models_v2
from routes import (
    auth_routes,
    user_routes,
    article_routes,
    measurement_routes,
    verification_routes,
    exchange_routes,
    gold_rates_routes,
    calculator_routes,
    transaction_routes,
)
import seed as seed_module
import seed_v2 as seed_v2_module

# Create all tables (legacy and v2 7 tables)
Base.metadata.create_all(bind=engine)

# Seed demo data on startup
try:
    seed_module.seed()
    seed_v2_module.seed_v2()
except Exception as e:
    print(f"Warning: seeding encountered: {e}")

app = FastAPI(
    title="AURUM API",
    description="AI-powered gold verification, benchmark pricing, and fair exchange platform",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Core & Legacy Routes
app.include_router(auth_routes.router)
app.include_router(user_routes.router)
app.include_router(article_routes.router)
app.include_router(measurement_routes.router)
app.include_router(verification_routes.router)
app.include_router(exchange_routes.router)

# Person 1: Financial Core, Benchmark Rates & Immutable Snapshots
app.include_router(gold_rates_routes.router)
app.include_router(calculator_routes.router)
app.include_router(transaction_routes.router)


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "app": "AURUM",
        "version": "2.0.0",
        "modules": {
            "financial_engine": "active",
            "pricing_engine": "active",
            "snapshot_engine": "active",
        },
    }
