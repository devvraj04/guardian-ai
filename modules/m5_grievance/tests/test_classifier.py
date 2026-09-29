"""
Unit tests for Grievance Classifier (Module 5).
SPEC §3.7 Target: F1 >= 0.80.
"""

from modules.m5_grievance.classifier import grievance_classifier
from modules.m5_grievance.dataset import CATEGORY_METADATA


def test_classifier_benchmark_f1_target():
    """Validates that the classifier achieves F1 >= 0.80 on the benchmark test set."""
    metrics = grievance_classifier.evaluate_benchmark()
    assert (
        metrics["macro_f1"] >= 0.80
    ), f"Grievance classifier F1 of {metrics['macro_f1']} fell below the 0.80 target (SPEC §3.7)"
    assert metrics["accuracy"] >= 0.80


def test_classifier_individual_categories():
    test_cases = [
        (
            "The loan app deducted 12% hidden processing fee and undisclosed insurance charges.",
            "excessive_charges_and_hidden_fees",
        ),
        (
            "Recovery agents called my manager and sent threatening messages to my contacts.",
            "recovery_harassment_and_privacy",
        ),
        (
            "They disbursed the loan into a third-party pool account and hiked my credit limit automatically.",
            "unauthorized_disbursal_or_credit_limit",
        ),
        (
            "I never received a Key Fact Statement (KFS) and was denied my cooling-off period exit.",
            "transparency_and_kfs_violation",
        ),
        (
            "I closed my loan three months ago but they have not updated CIBIL or issued my NOC.",
            "repayment_and_noc_delay",
        ),
        (
            "No response from customer support or Grievance Officer after 40 days of filing complaint.",
            "general_service_deficiency",
        ),
    ]

    for text, expected_category in test_cases:
        res = grievance_classifier.classify(text)
        assert (
            res.category == expected_category
        ), f"Expected '{expected_category}', got '{res.category}' for text: {text}"
        assert res.confidence >= 0.20
        assert res.redressal_tat_days == 30
        assert (
            res.rbi_clause_reference
            == CATEGORY_METADATA[expected_category]["rbi_clause"]
        )
