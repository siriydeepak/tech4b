"""
AURUM — Synthetic Prototype Dataset Generator (100 Benchmark Records)
Member 2: Verification, Evidence Pipeline & Data Management

Generates 100 realistic gold transaction records across 4 test scenarios:
  1. 50 Normal / Verified transactions
  2. 20 Incomplete / Missing evidence transactions
  3. 20 Inconsistent measurement transactions
  4. 10 Hallmark & Purity mismatch transactions
"""

import json
import random
from datetime import datetime, timedelta

random.seed(42)

JEWELLERY_TYPES = ["CHAIN", "BANGLE", "NECKLACE", "RING", "EARRINGS", "GOLD_COIN"]
AHC_CENTRES = [
    "Bangalore Assaying & Hallmarking Centre (AHC-KA-004)",
    "South India Hallmarking Federation (AHC-KA-012)",
    "Deccan Assay Labs Bangalore (AHC-KA-009)",
    "Karnataka Bullion Assaying Laboratory (AHC-KA-002)",
    "National Refineries & Hallmark Centre Delhi (AHC-DL-001)"
]
JEWELLER_STORES = [
    "Tanishq Jewellers Indiranagar",
    "Malabar Gold & Diamonds MG Road",
    "CaratLane Jayanagar",
    "Kalyan Jewellers Commercial Street",
    "Bhima Jewellers Koramangala",
    "GRT Jewellers Marathahalli"
]

BENCHMARK_RATE_999 = 7650.00  # ₹ / gram for 999 24K gold

def generate_huid():
    letters = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "".join(random.choices(letters, k=6))

def compute_valuation(net_weight, fineness, rate_999, deduction_pct=2.0):
    metal_value = round(net_weight * rate_999 * (fineness / 999.0), 2)
    deduction_amount = round(metal_value * (deduction_pct / 100.0), 2)
    final_offer = round(metal_value - deduction_amount, 2)
    return metal_value, deduction_amount, final_offer

def build_dataset():
    records = []
    base_time = datetime(2026, 11, 15, 10, 0, 0)

    # ----------------------------------------------------
    # SCENARIO 1: 50 Normal / Verified Records (AUR-001 to AUR-050)
    # ----------------------------------------------------
    for i in range(1, 51):
        tx_id = f"AUR-{i:03d}"
        j_type = random.choice(JEWELLERY_TYPES)
        huid = generate_huid()
        
        # 85% 22K, 10% 24K, 5% 18K
        karat = random.choices(["22K", "24K", "18K"], weights=[85, 10, 5])[0]
        fineness_target = 916 if karat == "22K" else (999 if karat == "24K" else 750)
        
        gross_w = round(random.uniform(5.0, 45.0), 2)
        stone_w = round(random.uniform(0.0, 2.5), 2) if j_type in ["RING", "NECKLACE"] else 0.0
        net_w = round(gross_w - stone_w, 2)
        
        xrf_fineness = round(fineness_target + random.uniform(-0.8, 1.2), 1)
        xrf_purity_pct = round(xrf_fineness / 10.0, 2)
        
        metal_val, ded_amt, final_offer = compute_valuation(net_w, xrf_fineness, BENCHMARK_RATE_999, deduction_pct=1.8)
        
        tx_time = (base_time + timedelta(hours=i*2)).isoformat() + "Z"
        
        record = {
            "transaction_id": tx_id,
            "scenario": "NORMAL_VERIFIED",
            "timestamp": tx_time,
            "customer_id": f"CUST-{random.randint(100, 999)}",
            "jeweller_store": random.choice(JEWELLER_STORES),
            "jewellery": {
                "type": j_type,
                "declared_karat": karat,
                "declared_fineness": fineness_target,
                "declared_gross_weight_g": gross_w,
                "declared_stone_weight_g": stone_w,
                "declared_net_weight_g": net_w,
                "declared_huid": huid
            },
            "bis_huid_verification": {
                "status": "VALID_VERIFIED",
                "huid": huid,
                "registered_article_type": j_type,
                "registered_purity": karat,
                "registered_fineness": fineness_target,
                "ahc_centre": random.choice(AHC_CENTRES),
                "is_match": True
            },
            "physical_measurements": {
                "scale_gross_weight_g": gross_w,
                "scale_stone_weight_g": stone_w,
                "scale_net_weight_g": net_w,
                "xrf_measured_fineness": xrf_fineness,
                "xrf_purity_percent": xrf_purity_pct,
                "elemental_composition": {
                    "Au": xrf_purity_pct,
                    "Ag": round(random.uniform(3.0, 5.0), 2),
                    "Cu": round(random.uniform(2.5, 4.0), 2),
                    "Zn": round(random.uniform(0.1, 0.5), 2),
                    "Cd": 0.01  # Safe / compliant
                }
            },
            "valuation": {
                "benchmark_rate_999_inr": BENCHMARK_RATE_999,
                "gross_metal_value_inr": metal_val,
                "itemized_deductions": [
                    {"name": "Standard Refining/Melting Charge", "percentage": 1.8, "amount_inr": ded_amt}
                ],
                "total_deductions_inr": ded_amt,
                "final_offer_inr": final_offer
            },
            "evidence_items": [
                {"category": "JEWELLERY_PHOTO", "provenance": "CUSTOMER_PROVIDED", "file": f"https://storage.aurum.app/evidence/{tx_id}/photo.jpg"},
                {"category": "HALLMARK_HUID_PHOTO", "provenance": "INSTRUMENT_RECORDED", "file": f"https://storage.aurum.app/evidence/{tx_id}/huid_loupe.jpg"},
                {"category": "WEIGHING_SCALE_READOUT", "provenance": "INSTRUMENT_RECORDED", "file": f"https://storage.aurum.app/evidence/{tx_id}/scale.jpg"},
                {"category": "XRF_SPECTROMETER_READOUT", "provenance": "INSTRUMENT_RECORDED", "file": f"https://storage.aurum.app/evidence/{tx_id}/xrf_spectrum.pdf"},
                {"category": "BIS_CARE_SCREENSHOT", "provenance": "OFFICIALLY_VERIFIED", "file": f"https://storage.aurum.app/evidence/{tx_id}/bis_verify.png"}
            ],
            "anomaly_flags": [],
            "overall_trust_score": random.randint(92, 99)
        }
        records.append(record)

    # ----------------------------------------------------
    # SCENARIO 2: 20 Missing Information Records (AUR-051 to AUR-070)
    # ----------------------------------------------------
    for i in range(51, 71):
        tx_id = f"AUR-{i:03d}"
        j_type = random.choice(JEWELLERY_TYPES)
        huid = generate_huid()
        gross_w = round(random.uniform(8.0, 30.0), 2)
        net_w = gross_w
        
        # Simulate missing evidence type
        missing_type = random.choice(["MISSING_XRF", "MISSING_HUID_PHOTO", "MISSING_PURCHASE_RECEIPT", "HUID_NOT_ENTERED"])
        tx_time = (base_time + timedelta(hours=i*2)).isoformat() + "Z"
        
        evidence = [
            {"category": "JEWELLERY_PHOTO", "provenance": "CUSTOMER_PROVIDED", "file": f"https://storage.aurum.app/evidence/{tx_id}/photo.jpg"},
            {"category": "WEIGHING_SCALE_READOUT", "provenance": "INSTRUMENT_RECORDED", "file": f"https://storage.aurum.app/evidence/{tx_id}/scale.jpg"}
        ]
        
        flags = []
        trust_score = 65
        
        if missing_type == "MISSING_XRF":
            xrf_fineness = 916.0
            flags.append({
                "code": "MISSING_MANDATORY_EVIDENCE",
                "severity": "HIGH",
                "explanation": "XRF Spectrometer laboratory report was not uploaded. Valuation relies on manual jeweller scratch test."
            })
            trust_score = 55
        elif missing_type == "HUID_NOT_ENTERED":
            huid = ""
            flags.append({
                "code": "HUID_NOT_FOUND",
                "severity": "MEDIUM",
                "explanation": "No 6-digit BIS HUID was provided. Item must be treated as unhallmarked vintage gold."
            })
            trust_score = 48
        else:
            xrf_fineness = 916.0
            flags.append({
                "code": "MISSING_MANDATORY_EVIDENCE",
                "severity": "LOW",
                "explanation": "Original customer purchase invoice missing. Secondary KYC verification recommended."
            })
            trust_score = 72

        metal_val, ded_amt, final_offer = compute_valuation(net_w, xrf_fineness, BENCHMARK_RATE_999, deduction_pct=2.5)

        records.append({
            "transaction_id": tx_id,
            "scenario": "MISSING_INFO",
            "timestamp": tx_time,
            "customer_id": f"CUST-{random.randint(100, 999)}",
            "jeweller_store": random.choice(JEWELLER_STORES),
            "jewellery": {
                "type": j_type,
                "declared_karat": "22K",
                "declared_fineness": 916,
                "declared_gross_weight_g": gross_w,
                "declared_stone_weight_g": 0.0,
                "declared_net_weight_g": net_w,
                "declared_huid": huid
            },
            "bis_huid_verification": {
                "status": "VALID_VERIFIED" if huid else "NOT_FOUND",
                "huid": huid,
                "registered_article_type": j_type,
                "is_match": bool(huid)
            },
            "physical_measurements": {
                "scale_gross_weight_g": gross_w,
                "scale_stone_weight_g": 0.0,
                "scale_net_weight_g": net_w,
                "xrf_measured_fineness": xrf_fineness,
                "xrf_purity_percent": round(xrf_fineness / 10.0, 2)
            },
            "valuation": {
                "benchmark_rate_999_inr": BENCHMARK_RATE_999,
                "gross_metal_value_inr": metal_val,
                "itemized_deductions": [{"name": "Refining & Unhallmarked Testing Margin", "percentage": 2.5, "amount_inr": ded_amt}],
                "total_deductions_inr": ded_amt,
                "final_offer_inr": final_offer
            },
            "evidence_items": evidence,
            "anomaly_flags": flags,
            "overall_trust_score": trust_score
        })

    # ----------------------------------------------------
    # SCENARIO 3: 20 Inconsistent Measurement Records (AUR-071 to AUR-090)
    # ----------------------------------------------------
    for i in range(71, 91):
        tx_id = f"AUR-{i:03d}"
        j_type = random.choice(JEWELLERY_TYPES)
        huid = generate_huid()
        declared_gross = 20.00
        
        # Sub-variations: Weight discrepancy, Net math error, Toxic Cadmium solder
        anomaly_choice = (i % 3)
        tx_time = (base_time + timedelta(hours=i*2)).isoformat() + "Z"
        flags = []
        cd_level = 0.01

        if anomaly_choice == 0:
            # Scale reads 17.5g vs declared 20g
            measured_gross = 17.50
            stone_w = 0.0
            net_w = 17.50
            flags.append({
                "code": "WEIGHT_MISMATCH",
                "severity": "HIGH",
                "explanation": f"Customer declared 20.00g, but certified counter scale registered {measured_gross}g (12.5% discrepancy)."
            })
            trust_score = 50
        elif anomaly_choice == 1:
            # Toxic Cadmium solder detected
            measured_gross = 20.00
            stone_w = 1.00
            net_w = 19.00
            cd_level = 0.85
            flags.append({
                "code": "TOXIC_SOLDER_DETECTED",
                "severity": "CRITICAL",
                "explanation": "XRF spectrometer detected 0.85% Cadmium (Cd) solder. Banned under BIS IS 1417 due to health and refining hazards."
            })
            trust_score = 35
        else:
            # Unexplained excessive deduction
            measured_gross = 20.00
            stone_w = 0.50
            net_w = 19.50
            flags.append({
                "code": "DEDUCTION_ANOMALY",
                "severity": "HIGH",
                "explanation": "Jeweller applied an 8.5% unexplained deduction exceeding standard 1.5-2.5% market refining margins."
            })
            trust_score = 45

        xrf_fineness = 916.0
        metal_val, ded_amt, final_offer = compute_valuation(net_w, xrf_fineness, BENCHMARK_RATE_999, deduction_pct=8.5 if anomaly_choice == 2 else 2.0)

        records.append({
            "transaction_id": tx_id,
            "scenario": "INCONSISTENT_MEASUREMENTS",
            "timestamp": tx_time,
            "customer_id": f"CUST-{random.randint(100, 999)}",
            "jeweller_store": random.choice(JEWELLER_STORES),
            "jewellery": {
                "type": j_type,
                "declared_karat": "22K",
                "declared_fineness": 916,
                "declared_gross_weight_g": declared_gross,
                "declared_stone_weight_g": 0.0,
                "declared_net_weight_g": declared_gross,
                "declared_huid": huid
            },
            "bis_huid_verification": {
                "status": "VALID_VERIFIED",
                "huid": huid,
                "registered_article_type": j_type,
                "is_match": True
            },
            "physical_measurements": {
                "scale_gross_weight_g": measured_gross,
                "scale_stone_weight_g": stone_w,
                "scale_net_weight_g": net_w,
                "xrf_measured_fineness": xrf_fineness,
                "xrf_purity_percent": 91.6,
                "elemental_composition": {"Au": 91.6, "Ag": 4.5, "Cu": 3.0, "Cd": cd_level}
            },
            "valuation": {
                "benchmark_rate_999_inr": BENCHMARK_RATE_999,
                "gross_metal_value_inr": metal_val,
                "itemized_deductions": [{"name": "Refining / Cadmium Penalty", "percentage": 8.5 if anomaly_choice == 2 else 2.0, "amount_inr": ded_amt}],
                "total_deductions_inr": ded_amt,
                "final_offer_inr": final_offer
            },
            "evidence_items": [
                {"category": "JEWELLERY_PHOTO", "provenance": "CUSTOMER_PROVIDED", "file": f"https://storage.aurum.app/evidence/{tx_id}/photo.jpg"},
                {"category": "WEIGHING_SCALE_READOUT", "provenance": "INSTRUMENT_RECORDED", "file": f"https://storage.aurum.app/evidence/{tx_id}/scale.jpg"},
                {"category": "XRF_SPECTROMETER_READOUT", "provenance": "INSTRUMENT_RECORDED", "file": f"https://storage.aurum.app/evidence/{tx_id}/xrf.pdf"}
            ],
            "anomaly_flags": flags,
            "overall_trust_score": trust_score
        })

    # ----------------------------------------------------
    # SCENARIO 4: 10 Hallmark & Purity Mismatch Records (AUR-091 to AUR-100)
    # ----------------------------------------------------
    for i in range(91, 101):
        tx_id = f"AUR-{i:03d}"
        huid = f"MIS{i:03d}"
        tx_time = (base_time + timedelta(hours=i*2)).isoformat() + "Z"

        if i % 2 == 0:
            # Declared 22K (916), XRF measures 18K (750)
            j_type = "CHAIN"
            declared_karat = "22K"
            declared_fineness = 916
            xrf_fineness = 751.4
            flags = [{
                "code": "PURITY_DOWNGRADE",
                "severity": "CRITICAL",
                "explanation": "Severe purity mismatch: Customer declared 22K (916 fineness), but certified XRF scan measured 751.4 fineness (18K gold). Potential fake hallmark stamp."
            }]
            bis_record = {
                "status": "MISMATCH",
                "huid": huid,
                "registered_article_type": "CHAIN",
                "registered_purity": "18K",
                "registered_fineness": 750,
                "is_match": False
            }
        else:
            # Article type mismatch: Customer presents Chain, HUID registers Bangle
            j_type = "CHAIN"
            declared_karat = "22K"
            declared_fineness = 916
            xrf_fineness = 915.8
            flags = [{
                "code": "ARTICLE_TYPE_MISMATCH",
                "severity": "CRITICAL",
                "explanation": f"Hallmark HUID {huid} is officially registered in BIS CARE database as a 'BANGLE', but the physical article presented is a 'CHAIN'. Indicates hallmark transplant / stamp cloning."
            }]
            bis_record = {
                "status": "MISMATCH",
                "huid": huid,
                "registered_article_type": "BANGLE",
                "registered_purity": "22K",
                "registered_fineness": 916,
                "is_match": False
            }

        gross_w = 15.00
        net_w = 15.00
        metal_val, ded_amt, final_offer = compute_valuation(net_w, xrf_fineness, BENCHMARK_RATE_999, deduction_pct=3.0)

        records.append({
            "transaction_id": tx_id,
            "scenario": "HALLMARK_PURITY_MISMATCH",
            "timestamp": tx_time,
            "customer_id": f"CUST-{random.randint(100, 999)}",
            "jeweller_store": random.choice(JEWELLER_STORES),
            "jewellery": {
                "type": j_type,
                "declared_karat": declared_karat,
                "declared_fineness": declared_fineness,
                "declared_gross_weight_g": gross_w,
                "declared_stone_weight_g": 0.0,
                "declared_net_weight_g": net_w,
                "declared_huid": huid
            },
            "bis_huid_verification": bis_record,
            "physical_measurements": {
                "scale_gross_weight_g": gross_w,
                "scale_stone_weight_g": 0.0,
                "scale_net_weight_g": net_w,
                "xrf_measured_fineness": xrf_fineness,
                "xrf_purity_percent": round(xrf_fineness / 10.0, 2)
            },
            "valuation": {
                "benchmark_rate_999_inr": BENCHMARK_RATE_999,
                "gross_metal_value_inr": metal_val,
                "itemized_deductions": [{"name": "Risk & Discrepancy Margin", "percentage": 3.0, "amount_inr": ded_amt}],
                "total_deductions_inr": ded_amt,
                "final_offer_inr": final_offer
            },
            "evidence_items": [
                {"category": "JEWELLERY_PHOTO", "provenance": "CUSTOMER_PROVIDED", "file": f"https://storage.aurum.app/evidence/{tx_id}/photo.jpg"},
                {"category": "HALLMARK_HUID_PHOTO", "provenance": "INSTRUMENT_RECORDED", "file": f"https://storage.aurum.app/evidence/{tx_id}/huid.jpg"},
                {"category": "XRF_SPECTROMETER_READOUT", "provenance": "INSTRUMENT_RECORDED", "file": f"https://storage.aurum.app/evidence/{tx_id}/xrf.pdf"},
                {"category": "BIS_CARE_SCREENSHOT", "provenance": "OFFICIALLY_VERIFIED", "file": f"https://storage.aurum.app/evidence/{tx_id}/bis.png"}
            ],
            "anomaly_flags": flags,
            "overall_trust_score": 25  # Severe penalty
        })

    return records

if __name__ == "__main__":
    dataset = build_dataset()
    output_path = "data/synthetic_transactions.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(dataset, f, indent=2)
    print(f"Successfully generated {len(dataset)} synthetic transaction records -> {output_path}")
