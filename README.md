# AURUM — AI-Powered Gold Verification & Fair Exchange Platform

> **Module Completed**: Person 1 — Financial Engine, Pricing & Database Architect  
> **Project Directory**: `D:\tech4b`  
> **Backend Framework**: Python FastAPI + SQLAlchemy + PostgreSQL / SQLite  

---

## 🏛️ Person 1 Architecture & Delivered Components

Person 1 owns the deterministic financial calculations, benchmark price ingestion, database schema with RLS, and immutable transaction snapshotting for dispute replay.

### 1. Database & Schema (Supabase PostgreSQL / SQLite)
- **SQL Migration**: `backend/migrations/001_initial_schema.sql`
  - Defines the **7 core tables**: `users`, `jewellery`, `verifications`, `gold_rates`, `transactions`, `evidence`, `anomaly_flags`.
  - Configures **Row-Level Security (RLS)**:
    - Customers can view and access only their own transactions and jewellery.
    - Jewellers access transactions assigned to their store.
    - Admins have system-wide access.
- **ORM Models**: `backend/models_v2.py`
  - SQLAlchemy 2.0 models compatible with PostgreSQL/Supabase and SQLite.
- **Client Configuration**: `backend/supabase_client.py`
  - Configures connection to Supabase with automatic local SQLite fallback.

### 2. Gold Pricing Engine (IBJA Sync & Cache)
- **Module**: `backend/pricing_engine.py`
  - Supports 4 official purity standards: **999 (24K), 916 (22K), 750 (18K), 585 (14K)**.
  - Morning (**AM**) and Evening (**PM**) rate sessions.
  - Database caching with fallback lookup handling for weekends and market holidays.
  - Automated daily seeder (`seed_today_rates`).

### 3. Core Exchange Valuation Engine
- **Module**: `backend/valuation_engine.py`
  - Pure deterministic math (no side effects):
    $$\text{Pure Gold (g)} = W_n \times \frac{P}{999}$$
    $$\text{Valuation } V = W_n \times R_{999} \times \frac{P}{999}$$
    $$\text{Final Net Offer } V_{\text{offer}} = V - D$$
  - Itemized deductions breakdown engine.

### 4. Transaction Snapshotting (Dispute Replay)
- **Module**: `backend/valuation_engine.py` (`build_calculation_snapshot`) & `backend/routes/transaction_routes.py`
  - Freezes all calculation inputs, benchmark rates, date, session, pure gold equivalent, gross metal valuation, deduction breakdown, and `calc_version` into the `transactions.snapshot` JSON column.
  - Past transactions are immutable and protected against subsequent daily gold price shifts.

---

## 🚀 Person 1 API Endpoints Delivered

| Method | Endpoint | Description | Auth Required |
|:---|:---|:---|:---|
| `GET` | `/api/gold-rates/latest` | Returns latest benchmark rates for 24K, 22K, 18K, 14K (AM/PM) | Public / Any |
| `GET` | `/api/gold-rates/history?days=7` | Historical rates for trend charts (up to 90 days) | Public / Any |
| `POST` | `/api/calculator/evaluate` | Stateless real-time financial valuation & deduction breakdown | Public / Any |
| `POST` | `/api/transactions/create` | Jeweller confirms exchange; freezes immutable snapshot in DB | Jeweller / Admin |
| `GET` | `/api/transactions/:id/snapshot` | Retrieves frozen snapshot for Dispute Replay | Customer / Jeweller |
| `GET` | `/api/transactions/` | Role-filtered list of transactions | Authenticated |

---

## 🔑 Demo Credentials (Pre-seeded)

| Role | Email | Password |
|:---|:---|:---|
| **Jeweller** | `jeweller@aurum.demo` | `demo1234` |
| **Customer** | `customer@aurum.demo` | `demo1234` |
| **Admin** | `admin@aurum.demo` | `admin1234` |

---

## 💻 Running the Backend Locally

```powershell
# Navigate to the backend directory
cd D:\tech4b\backend

# Run the FastAPI server
python -m uvicorn main:app --reload --port 8000
```

- **Interactive API Documentation (Swagger)**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/api/health
