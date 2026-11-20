# Member 2: Verification, Evidence Pipeline & Data Management
**Status**: Core Foundation Completed  
**Assigned Role**: Member 2  
**Tech Stack**: Next.js 15 (TypeScript) + Supabase  

---

## 1. Summary of Delivered Components

Member 2 owns the physical verification, hallmark/HUID validation, evidence provenance tagging, and benchmark test datasets. All core services, types, Next.js API routes, and the 100-record synthetic test dataset have been implemented.

```
Tech4Bharat/
├── types/
│   ├── evidence.ts                   # 4-tier provenance tags & evidence categories
│   ├── jewellery.ts                  # Jewellery asset types & karat-to-fineness mappings
│   └── verification.ts               # HUID, BIS record, XRF & discrepancy types
├── lib/
│   ├── index.ts                      # Clean module exports
│   ├── bis-huid-service.ts           # 6-char HUID validation & BIS CARE lookup engine
│   ├── physical-verification-service.ts # Weighing & XRF processing, toxic solder checks, trust score
│   └── storage-service.ts            # Supabase Storage path generator & file validator
├── app/api/
│   ├── verification/
│   │   ├── huid/route.ts             # POST: HUID validation & BIS comparison
│   │   └── measurements/route.ts     # POST: Counter scale & XRF logging
│   └── evidence/
│       └── upload/route.ts           # POST: Evidence upload & provenance assignment
├── data/
│   └── synthetic_transactions.json   # 100 benchmark transaction test records
└── scripts/
    └── generate_synthetic_dataset.py # Automated test data generator script
```

---

## 2. Implemented Services & Modules

### A. Strict Evidence Provenance System (`types/evidence.ts`)
To prevent unverified customer claims or manual inputs from masquerading as verified evidence, all media is categorized into one of 4 strict tiers:
1. `OFFICIALLY_VERIFIED` (Weight: 1.0) — Data from BIS CARE portal or official assay registries.
2. `INSTRUMENT_RECORDED` (Weight: 0.9) — Direct readouts from certified XRF spectrometers or precision scales.
3. `JEWELLER_ENTERED` (Weight: 0.7) — Counter inspection values manually logged by the assayer.
4. `CUSTOMER_PROVIDED` (Weight: 0.4) — Initial declarations, old bills, or unverified photos.

### B. BIS CARE HUID Verification (`lib/bis-huid-service.ts`)
- **Format Validation**: Ensures strict 6-character uppercase alphanumeric structure (`^[A-Z0-9]{6}$`).
- **Registry Lookup**: Queries official registry (with simulated cache for offline/hackathon use, e.g., `A1B2C3`, `H7K9M2`, `X8Y9Z1`, `MIS001`).
- **Discrepancy Checker**: Flags mismatches between declared jewellery attributes and BIS recorded data (article type mismatch, purity downgrade, weight variance).

### C. Physical Measurement & Instrument Logger (`lib/physical-verification-service.ts`)
- **Scale Weighing Verification**:
  - Validates $W_{\text{net}} = W_{\text{gross}} - W_{\text{stone}}$ with floating-point tolerance checks.
  - Flags negative stone weight, gross weight $\le 0$, and stone weight exceeding gross weight.
- **XRF Spectrometer Analysis**:
  - Converts purity percentage to fineness (e.g. $91.65\% \to 916.5$).
  - Assesses purity against BIS legal tolerances (flags purity downgrades beyond 0.2%).
  - **Cadmium Alert Engine**: Detects toxic Cadmium (Cd) soldering ($>0.05\%$) banned under BIS IS 1417.
- **Composite Trust Score Engine**: Computes a dynamic 0–100 confidence score based on HUID status, evidence provenance tiers, and detected discrepancies.

### D. Supabase Storage Pipeline (`lib/storage-service.ts`)
- Validates file constraints (max 10MB; JPEG, PNG, WEBP, PDF).
- Derives standardized storage paths:  
  `jewellery/<jewelleryId>/<category>/<timestamp>_<filename>`
- Prepares verified evidence records for Supabase database insertion.

### E. 100-Record Synthetic Benchmark Dataset (`data/synthetic_transactions.json`)
Generated via `scripts/generate_synthetic_dataset.py` to support all team members:
- **50 Normal Records (`AUR-001` to `AUR-050`)**: Clean transactions with verified HUIDs, compliant XRF readings, and trust scores $\ge 92$.
- **20 Missing Info Records (`AUR-051` to `AUR-070`)**: Missing XRF reports, missing purchase receipts, or unentered HUIDs.
- **20 Inconsistent Records (`AUR-071` to `AUR-090`)**: Scale weight discrepancies, Cadmium solder contamination, and excessive deduction margins.
- **10 Hallmark Mismatch Records (`AUR-091` to `AUR-100`)**: Customer declared 22K vs measured 18K (fake hallmark), and HUID article mismatches (declared Chain vs registered Bangle).

---

## 3. API Contract Hand-offs for Other Team Members

### For Member 4 (Frontend UI Lead):
- **HUID Verification**:
  ```http
  POST /api/verification/huid
  Content-Type: application/json
  {
    "huid": "A1B2C3",
    "declaredType": "CHAIN",
    "declaredKarat": "22K",
    "declaredGrossWeightGrams": 12.50
  }
  ```
- **Physical Counter Measurements**:
  ```http
  POST /api/verification/measurements
  Content-Type: application/json
  {
    "jewelleryId": "jewel_123",
    "jewellerId": "jwl_456",
    "grossWeightGrams": 12.50,
    "stoneWeightGrams": 0.50,
    "reportedNetWeightGrams": 12.00,
    "xrfPurityPercent": 91.65,
    "declaredKarat": "22K"
  }
  ```
- **Evidence Upload**:
  ```http
  POST /api/evidence/upload
  Content-Type: application/json
  {
    "jewelleryId": "jewel_123",
    "fileName": "xrf_scan.pdf",
    "fileSizeBytes": 1048576,
    "mimeType": "application/pdf",
    "category": "XRF_SPECTROMETER_READOUT",
    "provenance": "INSTRUMENT_RECORDED"
  }
  ```

### For Member 1 (Database & Pricing):
- Import types from `@/types/verification`, `@/types/jewellery`, and `@/types/evidence`.
- Seed the `transactions` and `evidence` tables in Supabase directly using `data/synthetic_transactions.json`.

### For Member 3 (AI Intelligence & PDF):
- Use `data/synthetic_transactions.json` records in scenarios 2, 3, and 4 to test Gemini OCR prompts, anomaly detection rules, and ReportLab PDF layout generation.
