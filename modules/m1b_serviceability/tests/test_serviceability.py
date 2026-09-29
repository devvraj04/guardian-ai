import json
from pathlib import Path
import pytest
from modules.m1b_serviceability.serviceability import (
    assess_serviceability,
    generate_serviceability_claim_text,
)

BENCHMARK_PATH = (
    Path(__file__).resolve().parent.parent.parent.parent
    / "data"
    / "test_cases"
    / "hand_computed_dti.json"
)


def test_hand_computed_dti_scenarios():
    """
    Enforces RULES.md §1.7, §4.4, §6.4:
    Unit-tested against hand-computed ground truth examples across multiple income/expense scenarios.
    """
    with open(BENCHMARK_PATH, "r", encoding="utf-8") as f:
        cases = json.load(f)

    for case in cases:
        result = assess_serviceability(
            monthly_income=case["monthly_income"],
            existing_emis=case["existing_emis"],
            monthly_expenses=case["monthly_expenses"],
            new_emi=case["new_emi"],
        )

        assert (
            abs(result.dti_ratio - case["expected_dti_ratio"]) <= 0.001
        ), f"DTI ratio mismatch in {case['scenario']}: got {result.dti_ratio}, expected {case['expected_dti_ratio']}"

        assert (
            abs(result.disposable_income - case["expected_disposable_income"]) <= 0.05
        ), f"Disposable income mismatch in {case['scenario']}: got {result.disposable_income}, expected {case['expected_disposable_income']}"

        assert (
            result.verdict == case["expected_verdict"]
        ), f"Verdict mismatch in {case['scenario']}: got {result.verdict}, expected {case['expected_verdict']}"

        # Verify claim text generation is non-empty and cites key figures
        claim_text = generate_serviceability_claim_text(result)
        assert len(claim_text) > 30
        assert f"{result.dti_ratio * 100:.1f}%" in claim_text


def test_invalid_income_raises_error():
    with pytest.raises(ValueError):
        assess_serviceability(
            monthly_income=0, existing_emis=1000, monthly_expenses=2000, new_emi=5000
        )

    with pytest.raises(ValueError):
        assess_serviceability(
            monthly_income=-5000, existing_emis=0, monthly_expenses=1000, new_emi=2000
        )
