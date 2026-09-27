"""
Module 1b: Loan Serviceability / Affordability Engine.
Governing Rules: RULES.md §1.7, §1.8, §4.4, §6.4.

IMPORTANT REGULATORY NOTICE (RULES.md §6.4):
The Debt-to-Income (DTI) serviceability thresholds used below are commonly used
lending-industry heuristics, NOT an RBI-mandated regulatory rule. This distinction
must be clearly preserved in code comments, API outputs, and user-facing reports.
"""

from dataclasses import dataclass
from typing import Dict, Any, Literal

ServiceabilityVerdict = Literal["serviceable", "marginal", "not-serviceable"]


@dataclass(frozen=True)
class ServiceabilityResult:
    monthly_income: float
    existing_emis: float
    monthly_expenses: float
    new_emi: float
    total_emis: float
    dti_ratio: float
    disposable_income: float
    verdict: ServiceabilityVerdict
    is_heuristic: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "monthly_income": round(self.monthly_income, 2),
            "existing_emis": round(self.existing_emis, 2),
            "monthly_expenses": round(self.monthly_expenses, 2),
            "new_emi": round(self.new_emi, 2),
            "total_emis": round(self.total_emis, 2),
            "dti_ratio": round(self.dti_ratio, 4),
            "disposable_income": round(self.disposable_income, 2),
            "verdict": self.verdict,
            "is_heuristic": True,
            "disclaimer": "Thresholds are lending-industry heuristics, not RBI-mandated rules (RULES.md §6.4)",
        }


def assess_serviceability(
    monthly_income: float,
    existing_emis: float,
    monthly_expenses: float,
    new_emi: float,
) -> ServiceabilityResult:
    """
    The canonical serviceability assessment function (RULES.md §1.7).
    Computes DTI ratio and disposable income deterministically.
    
    Classification Bands (Industry Heuristic):
    - serviceable: DTI <= 0.40 AND disposable_income > 0
    - marginal: 0.40 < DTI <= 0.50 AND disposable_income >= 0
    - not-serviceable: DTI > 0.50 OR disposable_income < 0
    """
    if monthly_income <= 0:
        raise ValueError("Monthly income must be strictly positive.")

    existing_emis = max(0.0, float(existing_emis))
    monthly_expenses = max(0.0, float(monthly_expenses))
    new_emi = max(0.0, float(new_emi))

    total_emis = existing_emis + new_emi
    dti_ratio = total_emis / monthly_income
    disposable_income = monthly_income - monthly_expenses - total_emis

    # Heuristic band evaluation
    if dti_ratio <= 0.40 and disposable_income > 0:
        verdict: ServiceabilityVerdict = "serviceable"
    elif dti_ratio <= 0.50 and disposable_income >= 0:
        verdict = "marginal"
    else:
        verdict = "not-serviceable"

    return ServiceabilityResult(
        monthly_income=monthly_income,
        existing_emis=existing_emis,
        monthly_expenses=monthly_expenses,
        new_emi=new_emi,
        total_emis=total_emis,
        dti_ratio=dti_ratio,
        disposable_income=disposable_income,
        verdict=verdict,
    )


def generate_serviceability_claim_text(result: ServiceabilityResult) -> str:
    """
    Constructs the natural-language claim text summarizing the serviceability verdict.
    Per RULES.md §1.8, this text is a Claim that MUST be verified by Module 3 before presentation.
    """
    dti_pct = result.dti_ratio * 100.0
    if result.verdict == "serviceable":
        return (
            f"Based on a monthly income of ₹{result.monthly_income:,.0f} and monthly obligations of ₹{result.total_emis:,.0f}, "
            f"your debt-to-income ratio is {dti_pct:.1f}% with a positive disposable buffer of ₹{result.disposable_income:,.0f}, "
            f"making this loan serviceable under standard lending guidelines."
        )
    elif result.verdict == "marginal":
        return (
            f"Based on a monthly income of ₹{result.monthly_income:,.0f}, your total obligations would reach ₹{result.total_emis:,.0f} "
            f"({dti_pct:.1f}% DTI ratio) with limited disposable income of ₹{result.disposable_income:,.0f}. "
            f"This loan offer is categorized as marginal."
        )
    else:
        reason = "DTI ratio exceeds 50%" if result.dti_ratio > 0.50 else "insufficient disposable income buffer"
        return (
            f"With total obligations of ₹{result.total_emis:,.0f} against monthly income of ₹{result.monthly_income:,.0f}, "
            f"your debt-to-income ratio is {dti_pct:.1f}%. Due to {reason}, "
            f"this loan is categorized as not-serviceable."
        )
