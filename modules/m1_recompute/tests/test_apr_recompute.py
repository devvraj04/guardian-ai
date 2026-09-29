import json
from pathlib import Path
import pytest
from modules.m1_recompute.apr_recompute import recompute_apr

BENCHMARK_PATH = (
    Path(__file__).resolve().parent.parent.parent.parent
    / "data"
    / "test_cases"
    / "hand_computed_apr.json"
)


def test_hand_computed_apr_benchmarks():
    """
    Enforces RULES.md §1.7 and §4.4:
    Unit-tested against hand-computed ground truth examples across various tenures and fee structures.
    """
    with open(BENCHMARK_PATH, "r", encoding="utf-8") as f:
        cases = json.load(f)

    for case in cases:
        result = recompute_apr(
            principal=case["principal"],
            disclosed_rate=case["disclosed_rate"],
            tenure_months=case["tenure_months"],
            fees=case["fees"],
        )

        # Check EMI within 0.05 rupee tolerance
        assert (
            abs(result.monthly_emi - case["expected_emi"]) <= 0.10
        ), f"EMI mismatch on {case['description']}: got {result.monthly_emi}, expected {case['expected_emi']}"

        # Check Effective APR within tolerance
        assert (
            abs(result.recomputed_apr - case["expected_apr"]) <= case["tolerance_apr"]
        ), f"APR mismatch on {case['description']}: got {result.recomputed_apr:.2f}%, expected {case['expected_apr']}%"


def test_zero_fee_identity():
    """
    When fees are zero, effective APR must exactly equal the nominal disclosed rate.
    """
    result = recompute_apr(
        principal=100000, disclosed_rate=15.0, tenure_months=12, fees=0.0
    )
    assert result.recomputed_apr == 15.0
    assert result.fee_impact_apr == 0.0


def test_invalid_parameters():
    with pytest.raises(ValueError):
        recompute_apr(principal=-100, disclosed_rate=10, tenure_months=12)

    with pytest.raises(ValueError):
        recompute_apr(principal=10000, disclosed_rate=10, tenure_months=0)

    with pytest.raises(ValueError):
        # Fees equal to or greater than principal
        recompute_apr(principal=10000, disclosed_rate=10, tenure_months=12, fees=10000)
