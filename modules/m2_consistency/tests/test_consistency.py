import json
from pathlib import Path
import pytest

from modules.m2_consistency.consistency import (
    compare_numeric_field,
    compare_prepayment_clauses,
    run_consistency_check,
)


def load_test_cases():
    test_cases_path = (
        Path(__file__).resolve().parents[3]
        / "data"
        / "test_cases"
        / "consistency_test_cases.json"
    )
    with open(test_cases_path, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.mark.parametrize("scenario", load_test_cases(), ids=lambda s: s["scenario_id"])
def test_consistency_scenarios(scenario):
    """
    Validates consistency matching engine against 100% of canonical injected mismatch scenarios.
    """
    manual = scenario.get("manual_terms")
    tnc = scenario.get("tnc_extracted")
    kfs = scenario.get("kfs_extracted")
    expected = scenario["expected_results"]

    checks, overall_status, explanation, requires_human_review = run_consistency_check(
        manual_terms=manual,
        tnc_extracted=tnc,
        kfs_extracted=kfs,
    )

    # 1. Overall status
    assert (
        overall_status == expected["overall_status"]
    ), f"Scenario {scenario['scenario_id']}: expected overall_status {expected['overall_status']}, got {overall_status}"

    # 2. Field-level statuses
    field_status_map = {c.field_name: c.match_status for c in checks}
    for field_name, exp_status in expected["field_statuses"].items():
        assert (
            field_status_map.get(field_name) == exp_status
        ), f"Scenario {scenario['scenario_id']}, field {field_name}: expected {exp_status}, got {field_status_map.get(field_name)}"

    # 3. Mismatched fields count and names
    actual_mismatches = [c.field_name for c in checks if c.match_status == "mismatch"]
    expected_mismatches = expected.get("mismatched_fields", [])
    assert (
        sorted(actual_mismatches) == sorted(expected_mismatches)
    ), f"Scenario {scenario['scenario_id']}: expected mismatches {expected_mismatches}, got {actual_mismatches}"

    # 4. Human review requirement
    assert (
        requires_human_review == expected["requires_human_review"]
    ), f"Scenario {scenario['scenario_id']}: expected requires_human_review {expected['requires_human_review']}, got {requires_human_review}"


def test_numeric_tolerances():
    # Principal within relative tolerance: 100,000 vs 100,050 (0.05% diff < 0.1% allowed)
    c1 = compare_numeric_field("principal", 100000.0, 100050.0, 100020.0)
    assert c1.match_status == "match"

    # Principal beyond tolerance: 100,000 vs 100,500 (0.5% diff > 0.1% allowed)
    c2 = compare_numeric_field("principal", 100000.0, 100500.0, 100000.0)
    assert c2.match_status == "mismatch"

    # Rate within tolerance: 12.00% vs 12.04% (0.04% diff < 0.05% allowed)
    c3 = compare_numeric_field("disclosed_rate", 12.00, 12.04, 12.01)
    assert c3.match_status == "match"

    # Rate beyond tolerance: 12.00% vs 12.10% (0.10% diff > 0.05% allowed)
    c4 = compare_numeric_field("disclosed_rate", 12.00, 12.10, 12.00)
    assert c4.match_status == "mismatch"

    # Tenure strict integer match
    c5 = compare_numeric_field("tenure_months", 24, 24, 24)
    assert c5.match_status == "match"
    c6 = compare_numeric_field("tenure_months", 24, 25, 24)
    assert c6.match_status == "mismatch"


def test_prepayment_prose_matching():
    # Both declare Nil charges
    c1 = compare_prepayment_clauses(
        "Nil prepayment charges apply.", "Foreclosure fee is zero."
    )
    assert c1.match_status == "match"
    assert not c1.requires_human_review

    # Direct contradiction: 2% penalty vs Nil charges
    c2 = compare_prepayment_clauses(
        "A prepayment penalty of 2.0% applies on outstanding balance.",
        "Foreclosure charges are nil as per RBI circular.",
    )
    assert c2.match_status == "mismatch"
    assert c2.requires_human_review

    # Missing clause in one document
    c3 = compare_prepayment_clauses(None, "Foreclosure charges are nil.")
    assert c3.match_status == "missing"
    assert not c3.requires_human_review
