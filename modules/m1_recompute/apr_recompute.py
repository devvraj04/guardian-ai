"""
Module 1: APR Recompute Engine (THE numeric truth function for APR/EMI).
Governing Rules: RULES.md §1.7, §4.4.
Deterministic pure Python financial calculations. No ML.
Single source of truth: This function is imported everywhere its number is needed.
"""

from dataclasses import dataclass
from typing import Dict, Any


@dataclass(frozen=True)
class APRRecomputeResult:
    principal: float
    disclosed_rate: float
    tenure_months: int
    fees: float
    disbursed_amount: float
    monthly_emi: float
    total_payment: float
    total_interest: float
    recomputed_apr: float
    fee_impact_apr: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "principal": round(self.principal, 2),
            "disclosed_rate": round(self.disclosed_rate, 4),
            "tenure_months": self.tenure_months,
            "fees": round(self.fees, 2),
            "disbursed_amount": round(self.disbursed_amount, 2),
            "monthly_emi": round(self.monthly_emi, 2),
            "total_payment": round(self.total_payment, 2),
            "total_interest": round(self.total_interest, 2),
            "recomputed_apr": round(self.recomputed_apr, 4),
            "fee_impact_apr": round(self.fee_impact_apr, 4),
        }


def calculate_reducing_balance_emi(
    principal: float, annual_rate: float, tenure_months: int
) -> float:
    """
    Standard reducing-balance EMI formula:
    EMI = P * r * (1 + r)^N / ((1 + r)^N - 1)
    where r = annual_rate / (12 * 100)
    """
    if principal <= 0 or tenure_months <= 0:
        raise ValueError("Principal and tenure must be strictly positive.")

    if annual_rate <= 0:
        return principal / tenure_months

    r = annual_rate / (12.0 * 100.0)
    factor = (1.0 + r) ** tenure_months
    emi = principal * r * factor / (factor - 1.0)
    return emi


def solve_monthly_irr(
    net_disbursed: float, monthly_emi: float, tenure_months: int, max_iter: int = 100
) -> float:
    """
    Numerical solver for monthly Internal Rate of Return (IRR).
    Solves: net_disbursed = sum_{t=1..N} [ monthly_emi / (1 + r)^t ]
    Uses high-precision bisection method with guaranteed convergence.
    """
    if net_disbursed <= 0 or monthly_emi <= 0 or tenure_months <= 0:
        raise ValueError("Invalid parameters for IRR calculation.")

    # Total payment must exceed net disbursed amount for positive return
    if monthly_emi * tenure_months <= net_disbursed:
        return 0.0

    low = 0.0
    high = 2.0  # Up to 200% monthly rate (astronomical ceiling)

    for _ in range(max_iter):
        mid = (low + high) / 2.0
        # Calculate Present Value of annuities at rate mid
        # PV = emi * (1 - (1 + mid)^(-N)) / mid
        if mid == 0.0:
            pv = monthly_emi * tenure_months
        else:
            pv = monthly_emi * (1.0 - (1.0 + mid) ** (-tenure_months)) / mid

        if abs(pv - net_disbursed) < 1e-7:
            return mid

        if pv > net_disbursed:
            # Discount rate is too low; PV is too high
            low = mid
        else:
            # Discount rate is too high; PV is too low
            high = mid

    return (low + high) / 2.0


def recompute_apr(
    principal: float,
    disclosed_rate: float,
    tenure_months: int,
    fees: float = 0.0,
) -> APRRecomputeResult:
    """
    The canonical APR recompute function (RULES.md §1.7).
    Calculates the true effective APR on the reducing balance taking all upfront fees into account.
    """
    if principal <= 0 or tenure_months <= 0 or disclosed_rate < 0:
        raise ValueError(
            "Principal and tenure must be positive, and disclosed rate non-negative."
        )

    fees = max(0.0, float(fees))
    disbursed = principal - fees
    if disbursed <= 0:
        raise ValueError(
            "Upfront fees cannot be greater than or equal to loan principal."
        )

    monthly_emi = calculate_reducing_balance_emi(
        principal, disclosed_rate, tenure_months
    )
    total_payment = monthly_emi * tenure_months
    total_interest = total_payment - principal

    if fees == 0.0:
        effective_apr = disclosed_rate
    else:
        monthly_irr = solve_monthly_irr(disbursed, monthly_emi, tenure_months)
        effective_apr = monthly_irr * 12.0 * 100.0

    fee_impact = max(0.0, effective_apr - disclosed_rate)

    return APRRecomputeResult(
        principal=principal,
        disclosed_rate=disclosed_rate,
        tenure_months=tenure_months,
        fees=fees,
        disbursed_amount=disbursed,
        monthly_emi=monthly_emi,
        total_payment=total_payment,
        total_interest=total_interest,
        recomputed_apr=effective_apr,
        fee_impact_apr=fee_impact,
    )
