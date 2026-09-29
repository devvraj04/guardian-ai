"""
Module 3: Numeric Truth Verifier.
Governing Rules: RULES.md §1.7, §4.4; SPEC §3.4; IMPLEMENTATION_PLAN Phase 6.

Extracts financial figures from claim_text and compares against ground-truth arithmetic
computed by importing Module 1 (apr_recompute) and Module 1b (serviceability).
NEVER duplicates calculation math.
"""

from dataclasses import dataclass, field
import re
from typing import Any, Dict, List, Literal, Optional

from modules.m1_recompute.apr_recompute import recompute_apr
from modules.m1b_serviceability.serviceability import assess_serviceability


@dataclass(frozen=True)
class NumericCheckDetail:
    field_name: str
    stated_value: float
    computed_truth: float
    tolerance: float
    diff: float
    match: bool


@dataclass(frozen=True)
class NumericVerificationOutput:
    verdict: Literal["grounded", "flagged", "not_applicable"]
    error_type: Optional[str] = None  # None | "numeric_mismatch"
    details: Dict[str, Any] = field(default_factory=dict)
    discrepancies: List[str] = field(default_factory=list)


def extract_percentage(text: str, context_keyword: str) -> Optional[float]:
    """Extracts a percentage figure following or preceding a context keyword."""
    # Pattern: 15.89% or 15.89 percent
    pattern = rf"(?:{context_keyword}[^\d\n\.\%]{{0,30}})(\d+(?:\.\d+)?)\s*\%"
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        return float(match.group(1))

    reverse_pattern = rf"(\d+(?:\.\d+)?)\s*\%[^\d\n\.\%]{{0,30}}(?:{context_keyword})"
    rev_match = re.search(reverse_pattern, text, re.IGNORECASE)
    if rev_match:
        return float(rev_match.group(1))
    return None


def extract_currency(text: str, context_keyword: str) -> Optional[float]:
    """Extracts a rupee amount following or preceding a context keyword."""
    # Pattern: ₹8,884.88 or Rs. 8,884.88 or INR 8884
    pattern = rf"(?:{context_keyword}[^\d\n₹RsINR]{{0,30}})(?:₹|Rs\.?|INR)?\s*([0-9,]+(?:\.[0-9]+)?)"
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        clean_num = match.group(1).replace(",", "")
        try:
            return float(clean_num)
        except ValueError:
            pass

    reverse_pattern = (
        rf"(?:₹|Rs\.?|INR)\s*([0-9,]+(?:\.[0-9]+)?)[^\d\n]{{0,30}}(?:{context_keyword})"
    )
    rev_match = re.search(reverse_pattern, text, re.IGNORECASE)
    if rev_match:
        clean_num = rev_match.group(1).replace(",", "")
        try:
            return float(clean_num)
        except ValueError:
            pass
    return None


def verify_numeric_figures(
    claim_text: str,
    supporting_figures: Optional[Dict[str, Any]] = None,
) -> NumericVerificationOutput:
    """
    Deterministically verifies numeric assertions inside claim_text.
    Cross-checks extracted numbers against true arithmetic recomputed by Module 1 & 1b.
    """
    if not claim_text or not claim_text.strip():
        return NumericVerificationOutput(verdict="not_applicable")

    figures = supporting_figures or {}
    checks: List[NumericCheckDetail] = []
    discrepancies: List[str] = []

    # 1. APR & EMI Verification Path (Module 1 Recompute)
    # Check if this claim concerns APR, EMI, principal, rate, tenure
    principal = figures.get("principal")
    rate = figures.get("disclosed_rate")
    tenure = figures.get("tenure_months")
    fees = figures.get("fees", 0.0)

    # If principal/rate/tenure are present in figures or can be extracted
    if principal is not None and rate is not None and tenure is not None:
        try:
            truth_apr_result = recompute_apr(
                principal=float(principal),
                disclosed_rate=float(rate),
                tenure_months=int(tenure),
                fees=float(fees or 0.0),
            )

            # Check Stated APR in claim text
            stated_apr = extract_percentage(claim_text, "APR")
            if stated_apr is not None:
                diff_apr = abs(stated_apr - truth_apr_result.recomputed_apr)
                # Tolerance: 0.05 percentage points (RULES.md §4.4)
                apr_match = diff_apr <= 0.05
                checks.append(
                    NumericCheckDetail(
                        field_name="effective_apr",
                        stated_value=stated_apr,
                        computed_truth=truth_apr_result.recomputed_apr,
                        tolerance=0.05,
                        diff=round(diff_apr, 4),
                        match=apr_match,
                    )
                )
                if not apr_match:
                    discrepancies.append(
                        f"Claim states effective APR of {stated_apr:.2f}%, but true computed APR is {truth_apr_result.recomputed_apr:.2f}% (difference: {diff_apr:.2f}pp > 0.05pp tolerance)."
                    )

            # Check Stated EMI in claim text
            stated_emi = extract_currency(claim_text, "EMI")
            if stated_emi is not None:
                diff_emi = abs(stated_emi - truth_apr_result.monthly_emi)
                # Tolerance: ₹1.00
                emi_match = diff_emi <= 1.00
                checks.append(
                    NumericCheckDetail(
                        field_name="monthly_emi",
                        stated_value=stated_emi,
                        computed_truth=truth_apr_result.monthly_emi,
                        tolerance=1.00,
                        diff=round(diff_emi, 2),
                        match=emi_match,
                    )
                )
                if not emi_match:
                    discrepancies.append(
                        f"Claim states monthly EMI of ₹{stated_emi:,.2f}, but true computed EMI is ₹{truth_apr_result.monthly_emi:,.2f} (difference: ₹{diff_emi:.2f} > ₹1.00 tolerance)."
                    )

        except Exception as e:
            discrepancies.append(f"Failed to recompute APR/EMI truth: {str(e)}")

    # 2. Serviceability & DTI Verification Path (Module 1b)
    monthly_income = figures.get("monthly_income")
    existing_emis = figures.get("existing_emis")
    monthly_expenses = figures.get("monthly_expenses")
    new_emi = figures.get("new_emi") or (
        truth_apr_result.monthly_emi if "truth_apr_result" in locals() else None
    )

    if (
        monthly_income is not None
        and existing_emis is not None
        and monthly_expenses is not None
        and new_emi is not None
    ):
        try:
            truth_serv_result = assess_serviceability(
                monthly_income=float(monthly_income),
                existing_emis=float(existing_emis),
                monthly_expenses=float(monthly_expenses),
                new_emi=float(new_emi),
            )

            # Check Stated DTI in claim text
            stated_dti = extract_percentage(claim_text, r"(?:DTI|debt[- ]to[- ]income)")
            if stated_dti is not None:
                stated_dti_ratio = stated_dti / 100.0
                diff_dti = abs(stated_dti_ratio - truth_serv_result.dti_ratio)
                # Tolerance: 0.005 (0.5%)
                dti_match = diff_dti <= 0.005
                checks.append(
                    NumericCheckDetail(
                        field_name="dti_ratio",
                        stated_value=stated_dti_ratio,
                        computed_truth=truth_serv_result.dti_ratio,
                        tolerance=0.005,
                        diff=round(diff_dti, 4),
                        match=dti_match,
                    )
                )
                if not dti_match:
                    discrepancies.append(
                        f"Claim states DTI of {stated_dti:.1f}%, but true computed DTI is {truth_serv_result.dti_ratio*100:.1f}%."
                    )

        except Exception as e:
            discrepancies.append(f"Failed to recompute Serviceability truth: {str(e)}")

    # If no verifiable numeric assertions were found in the claim
    if not checks and not discrepancies:
        return NumericVerificationOutput(
            verdict="not_applicable",
            error_type=None,
            details={"message": "No verifiable arithmetic figures asserted in claim."},
        )

    # Any discrepancy results in a flagged numeric verdict
    if discrepancies or any(not c.match for c in checks):
        return NumericVerificationOutput(
            verdict="flagged",
            error_type="numeric_mismatch",
            details={
                "checks": [
                    {
                        "field": c.field_name,
                        "stated": c.stated_value,
                        "computed": c.computed_truth,
                        "diff": c.diff,
                        "tolerance": c.tolerance,
                        "match": c.match,
                    }
                    for c in checks
                ]
            },
            discrepancies=discrepancies,
        )

    # All checks passed within tolerance
    return NumericVerificationOutput(
        verdict="grounded",
        error_type=None,
        details={
            "checks": [
                {
                    "field": c.field_name,
                    "stated": c.stated_value,
                    "computed": c.computed_truth,
                    "diff": c.diff,
                    "tolerance": c.tolerance,
                    "match": c.match,
                }
                for c in checks
            ]
        },
    )
