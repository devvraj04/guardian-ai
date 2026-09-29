import json
from pathlib import Path
from uuid import uuid4
import pytest

from app.schemas.claim import Claim
from modules.m3_verifier.verifier import verify_claim


@pytest.fixture(scope="module")
def adversarial_dataset():
    dataset_path = (
        Path(__file__).resolve().parents[3]
        / "data"
        / "test_cases"
        / "adversarial_verification_cases.json"
    )
    with open(dataset_path, "r", encoding="utf-8") as f:
        return json.load(f)


def test_adversarial_stress_benchmark(adversarial_dataset):
    """
    Phase 6 Acceptance Gate (STATUS.md line 81, IMPLEMENTATION_PLAN line 152):
    Adversarial test: 10–15 manually constructed subtly-wrong KFS/T&C inputs,
    verifier MUST catch >= 90%.
    """
    adversarial_cases = [
        c for c in adversarial_dataset if c["expected_verdict"] == "flagged"
    ]
    grounded_cases = [
        c for c in adversarial_dataset if c["expected_verdict"] == "grounded"
    ]

    assert (
        len(adversarial_cases) >= 10
    ), f"Expected at least 10 adversarial cases, found {len(adversarial_cases)}"

    caught_adversarial = 0
    missed_cases = []

    test_user_id = f"test_adv_user_{uuid4().hex[:6]}"
    test_loan_id = f"test_adv_loan_{uuid4().hex[:6]}"

    # Regulatory premises from RBI Digital Lending Directions 2025
    rbi_benchmark_premises = [
        "Clause 5.2: Prepayment penalties are prohibited on floating-rate term loans granted to individual borrowers for purposes other than business.",
        "Clause 4.1: All loan disbursements and repayments must be executed directly between the bank account of the borrower and the Regulated Entity, without pass-through or pool accounts of any Lending Service Provider (LSP) or third party.",
        "Clause 4.2: Automatic increase in credit limit without explicit recorded consent of the borrower is strictly prohibited.",
        "Clause 3.2: The KFS shall clearly disclose cooling-off / look-up period during which the borrower can exit the loan without penalty.",
        "Clause 3.3: Any fee, charge, penalty, or cost not explicitly disclosed in the KFS cannot be charged to the borrower at any stage of the loan lifecycle.",
        "Clause 5.1: Penal charges for delayed payments shall be reasonable, transparent, and non-capitalized (i.e., interest shall not be charged on penal charges).",
        "Clause 6.1: REs and LSPs shall provide an effective and accessible grievance redressal mechanism with a turnaround time (TAT) not exceeding 30 days.",
        "Clause 1.2: These directions apply to digital lending operations undertaken by Regulated Entities (REs) including Commercial Banks, Primary (Urban) Co-operative Banks, and Non-Banking Financial Companies (NBFCs).",
    ]

    for item in adversarial_cases:
        claim = Claim(
            claim_id=str(uuid4()),
            source_module=item["source_module"],
            user_id=test_user_id,
            loan_id=test_loan_id,
            claim_text=item["claim_text"],
            supporting_figures=item.get("supporting_figures", {}),
            source_record_id=test_loan_id,
        )

        res = verify_claim(
            claim=claim,
            user_id=test_user_id,
            loan_id=test_loan_id,
            custom_premises=rbi_benchmark_premises,
        )

        if res.final_verdict == "flagged":
            caught_adversarial += 1
        else:
            missed_cases.append(
                {
                    "case_id": item["case_id"],
                    "text": item["claim_text"],
                    "verdict": res.final_verdict,
                }
            )

    catch_rate = caught_adversarial / len(adversarial_cases)
    print(
        f"\nAdversarial Stress Test Catch Rate: {catch_rate*100:.1f}% ({caught_adversarial}/{len(adversarial_cases)} caught)"
    )

    assert catch_rate >= 0.90, (
        f"Phase 6 Gate Failure: Verifier caught {catch_rate*100:.1f}% < 90% target. "
        f"Missed cases: {missed_cases}"
    )

    # Verify grounded cases pass with high precision (Low False Alarm Rate)
    grounded_passed = 0
    for item in grounded_cases:
        claim = Claim(
            claim_id=str(uuid4()),
            source_module=item["source_module"],
            user_id=test_user_id,
            loan_id=test_loan_id,
            claim_text=item["claim_text"],
            supporting_figures=item.get("supporting_figures", {}),
            source_record_id=test_loan_id,
        )

        res = verify_claim(
            claim=claim,
            user_id=test_user_id,
            loan_id=test_loan_id,
            custom_premises=rbi_benchmark_premises,
        )

        if res.final_verdict == "grounded":
            grounded_passed += 1

    precision = grounded_passed / len(grounded_cases)
    print(
        f"Grounded Cases True Positive Rate: {precision*100:.1f}% ({grounded_passed}/{len(grounded_cases)})"
    )
    assert (
        precision >= 0.75
    ), f"False positive rejection rate too high on legitimate claims: {precision}"
