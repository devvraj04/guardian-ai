from modules.m3_verifier.semantic_verifier import verify_semantic_entailment


def test_semantic_entailment_grounded():
    premise = (
        "Clause 5.2: Prepayment penalties are prohibited on floating-rate term loans "
        "granted to individual borrowers for purposes other than business."
    )
    claim = "Individual borrowers with floating-rate loans cannot be charged prepayment penalties."
    result = verify_semantic_entailment(claim_text=claim, premises=[premise])

    assert result.verdict == "grounded"
    assert result.error_type is None
    assert result.score >= 0.55


def test_semantic_contradiction_flagged():
    premise = (
        "Clause 5.2: Prepayment penalties are prohibited on floating-rate term loans "
        "granted to individual borrowers for purposes other than business."
    )
    contradictory_claim = "Lenders are allowed to charge 4% prepayment penalties on floating-rate personal loans."
    result = verify_semantic_entailment(
        claim_text=contradictory_claim, premises=[premise]
    )

    assert result.verdict == "flagged"
    assert result.error_type == "semantic_mismatch"
    assert result.contradiction_score >= 0.50


def test_semantic_insufficient_evidence_neutral():
    premise = "Clause 4.1: All loan disbursements must be executed directly between the bank account of the borrower and the Regulated Entity."
    unrelated_claim = (
        "Borrowers will receive a festive reward voucher on their birthday."
    )
    result = verify_semantic_entailment(claim_text=unrelated_claim, premises=[premise])

    assert result.verdict == "flagged"
    assert result.error_type == "insufficient_evidence"


def test_semantic_empty_premises():
    claim = "Any assertion without source evidence."
    result = verify_semantic_entailment(claim_text=claim, premises=[])

    assert result.verdict == "flagged"
    assert result.error_type == "insufficient_evidence"
    assert result.score == 0.0
