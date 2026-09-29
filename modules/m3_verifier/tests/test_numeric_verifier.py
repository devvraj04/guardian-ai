from modules.m3_verifier.numeric_verifier import (
    extract_currency,
    extract_percentage,
    verify_numeric_figures,
)


def test_extract_figures():
    text = "For a principal of ₹100,000 at disclosed rate 12.00% over 12 months with fees of ₹2,000, the true effective APR is 15.89% with a monthly EMI of ₹8,884.88."
    apr = extract_percentage(text, "APR")
    emi = extract_currency(text, "EMI")

    assert apr == 15.89
    assert emi == 8884.88


def test_numeric_verifier_grounded_apr():
    claim_text = (
        "For a principal of ₹100,000 at disclosed rate 12.00% over 12 months with fees of ₹2,000, "
        "the true effective APR is 15.89% with a monthly EMI of ₹8,884.88."
    )
    figures = {
        "principal": 100000.0,
        "disclosed_rate": 12.0,
        "tenure_months": 12,
        "fees": 2000.0,
    }
    result = verify_numeric_figures(claim_text=claim_text, supporting_figures=figures)
    assert result.verdict == "grounded"
    assert result.error_type is None
    assert len(result.discrepancies) == 0


def test_numeric_verifier_flagged_understated_apr():
    # Adversarial claim: states 12.00% APR despite fees
    claim_text = (
        "For a principal of ₹100,000 at disclosed rate 12.00% over 12 months with fees of ₹2,000, "
        "the true effective APR is 12.00% with a monthly EMI of ₹8,884.88."
    )
    figures = {
        "principal": 100000.0,
        "disclosed_rate": 12.0,
        "tenure_months": 12,
        "fees": 2000.0,
    }
    result = verify_numeric_figures(claim_text=claim_text, supporting_figures=figures)
    assert result.verdict == "flagged"
    assert result.error_type == "numeric_mismatch"
    assert any("APR" in d for d in result.discrepancies)


def test_numeric_verifier_flagged_wrong_emi():
    # Adversarial claim: states wrong EMI
    claim_text = (
        "For a principal of ₹100,000 at disclosed rate 12.00% over 12 months with fees of ₹2,000, "
        "the true effective APR is 15.89% with a monthly EMI of ₹7,500.00."
    )
    figures = {
        "principal": 100000.0,
        "disclosed_rate": 12.0,
        "tenure_months": 12,
        "fees": 2000.0,
    }
    result = verify_numeric_figures(claim_text=claim_text, supporting_figures=figures)
    assert result.verdict == "flagged"
    assert result.error_type == "numeric_mismatch"
    assert any("EMI" in d for d in result.discrepancies)


def test_numeric_verifier_grounded_serviceability():
    claim_text = "With monthly income of ₹80,000 and total obligations of ₹18,885, your debt-to-income DTI is 23.6%."
    figures = {
        "monthly_income": 80000.0,
        "existing_emis": 10000.0,
        "monthly_expenses": 30000.0,
        "new_emi": 8884.88,
    }
    result = verify_numeric_figures(claim_text=claim_text, supporting_figures=figures)
    assert result.verdict == "grounded"
    assert result.error_type is None


def test_numeric_verifier_flagged_wrong_dti():
    # Claim states 15.0% DTI when true is ~23.6%
    claim_text = "With monthly income of ₹80,000 and total obligations of ₹18,885, your debt-to-income DTI is 15.0%."
    figures = {
        "monthly_income": 80000.0,
        "existing_emis": 10000.0,
        "monthly_expenses": 30000.0,
        "new_emi": 8884.88,
    }
    result = verify_numeric_figures(claim_text=claim_text, supporting_figures=figures)
    assert result.verdict == "flagged"
    assert result.error_type == "numeric_mismatch"


def test_numeric_verifier_not_applicable():
    claim_text = "The lender shall provide a Key Fact Statement prior to signing."
    result = verify_numeric_figures(claim_text=claim_text, supporting_figures={})
    assert result.verdict == "not_applicable"
    assert result.error_type is None
