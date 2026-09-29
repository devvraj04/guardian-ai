"""
Integration benchmark tests for Module 4 Vernacular Verifier.
"""

import json
from pathlib import Path
from uuid import uuid4
import pytest

from app.schemas.claim import Claim
from modules.m4_vernacular.vernacular_verifier import verify_vernacular_claim


@pytest.fixture(scope="module")
def vernacular_dataset():
    dataset_path = (
        Path(__file__).resolve().parents[3]
        / "data"
        / "test_cases"
        / "vernacular_test_cases.json"
    )
    with open(dataset_path, "r", encoding="utf-8") as f:
        return json.load(f)


def test_vernacular_verification_benchmark(vernacular_dataset):
    """
    Phase 7 Acceptance Gate (STATUS.md lines 86-89):
    - Translation implemented and cached
    - Back-translation verified via Module 3's own functions
    - Cross-Lingual Numeric Preservation Rate reported
    - Clause-Drop Rate reported
    """
    test_user_id = f"test_vern_user_{uuid4().hex[:6]}"
    test_loan_id = f"test_vern_loan_{uuid4().hex[:6]}"

    rbi_premises = [
        "Clause 5.2: Prepayment penalties are prohibited on floating-rate term loans granted to individual borrowers for purposes other than business.",
        "Clause 4.1: All loan disbursements and repayments must be executed directly between the bank account of the borrower and the Regulated Entity, without pass-through or pool accounts of any Lending Service Provider (LSP) or third party.",
        "Clause 3.2: The KFS shall clearly disclose cooling-off / look-up period during which the borrower can exit the loan without penalty.",
    ]

    for item in vernacular_dataset:
        claim = Claim(
            claim_id=str(uuid4()),
            source_module=item["source_module"],
            user_id=test_user_id,
            loan_id=test_loan_id,
            claim_text=item["original_claim"],
            supporting_figures=item.get("supporting_figures", {}),
            source_record_id=test_loan_id,
        )

        response = verify_vernacular_claim(
            claim=claim,
            user_id=test_user_id,
            loan_id=test_loan_id,
            target_language=item["language"],
            custom_premises=rbi_premises,
        )

        # Invariants:
        assert (
            response.verification_verdict == item["expected_verdict"]
        ), f"Case {item['case_id']} expected {item['expected_verdict']}, got {response.verification_verdict}"
        assert (
            response.metrics.numeric_preservation_rate
            >= item["expected_min_numeric_preservation"]
        )
        assert response.metrics.clause_drop_rate <= item["expected_max_clause_drop"]
        assert response.metrics.semantic_drift_score >= 0.70
        assert response.is_cached is True
