"""Pure financial calculation logic — no I/O, fully tested."""
from typing import List
from schemas import DeductionIn


def compute_exchange(
    gross_weight: float,
    non_gold_weight: float,
    purity_percentage: float,
    reference_rate: float,
    deductions: List[DeductionIn],
) -> dict:
    net_gold_weight = round(gross_weight - non_gold_weight, 4)
    fine_gold_equivalent = round(net_gold_weight * purity_percentage / 100, 4)
    metal_value = round(fine_gold_equivalent * reference_rate, 2)
    total_deductions = round(sum(d.amount for d in deductions), 2)
    final_value = round(metal_value - total_deductions, 2)

    return {
        "gross_weight": gross_weight,
        "non_gold_weight": non_gold_weight,
        "net_gold_weight": net_gold_weight,
        "purity_percentage": purity_percentage,
        "reference_rate": reference_rate,
        "fine_gold_equivalent": fine_gold_equivalent,
        "metal_value": metal_value,
        "total_deductions": total_deductions,
        "final_value": final_value,
    }

