"""
Unit tests for Vernacular Cross-Lingual Metrics.
"""

from modules.m4_vernacular.vernacular_verifier import compute_cross_lingual_metrics


def test_perfect_preservation_metrics():
    orig = "For a principal of ₹100,000 at 12.00% rate, the monthly EMI is ₹8,884.88."
    back = "For a principal of ₹100,000 at 12.00% rate, the monthly EMI is ₹8,884.88."

    metrics = compute_cross_lingual_metrics(orig, back)
    assert metrics.numeric_preservation_rate == 100.0
    assert metrics.preserved_figures_count == 3
    assert metrics.clause_drop_rate == 0.0
    assert metrics.semantic_drift_score >= 0.90


def test_corrupted_number_preservation_drop():
    orig = "For a principal of ₹100,000 at 12.00% rate, the monthly EMI is ₹8,884.88."
    # Corrupt two numbers
    corrupt_back = (
        "For a principal of ₹50,000 at 18.00% rate, the monthly EMI is ₹8,884.88."
    )

    metrics = compute_cross_lingual_metrics(orig, corrupt_back)
    # Only 1 out of 3 figures preserved (EMI)
    assert metrics.preserved_figures_count == 1
    assert metrics.numeric_preservation_rate < 50.0


def test_dropped_clause_detection():
    orig = (
        "Prepayment penalties are prohibited on floating-rate term loans. "
        "Borrowers can exit without penalty during the cooling-off period."
    )
    # Drop second sentence completely
    corrupt_back = "Prepayment penalties are prohibited on floating-rate term loans."

    metrics = compute_cross_lingual_metrics(orig, corrupt_back)
    assert metrics.clause_drop_rate > 0.0
    assert len(metrics.dropped_clauses) >= 1
