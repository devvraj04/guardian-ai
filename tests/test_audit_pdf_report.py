import pymupdf
from fastapi.testclient import TestClient
from app.main import app
from app.deps.auth import get_current_user, AuthenticatedUser
from app.services.pdf_generator import generate_audit_verification_report_pdf


def test_generate_audit_verification_report_pdf_direct():
    """Test direct PDF generation using PyMuPDF."""
    pdf_bytes = generate_audit_verification_report_pdf(
        loan_id="test-loan-pdf-1",
        loan_name="Gold Home Loan",
        lender_name="State Bank of India",
        kfs={
            "principal": 2500000,
            "disclosed_rate": 8.5,
            "tenure_months": 240,
            "monthly_emi": 21695,
            "processing_fee": 15000,
            "net_disbursed_amount": 2485000,
            "apr": 8.62,
            "bank_name": "State Bank of India",
            "interest_type": "Floating Rate",
            "prepayment_clause": "Zero foreclosure charges per RBI norms.",
            "penal_charges": "2% per month on overdue EMI.",
            "bounce_charges": 500,
            "cooling_off_period": "3 business days",
            "grievance_email": "nodal.officer@sbi.co.in",
            "grievance_phone": "1800-11-2211",
        },
        apr={
            "principal": 2500000,
            "disclosed_rate": 8.5,
            "tenure_months": 240,
            "monthly_emi": 21695,
            "fees": 15000,
            "recomputed_apr": 8.62,
            "fee_impact_apr": 0.12,
            "disbursed_amount": 2485000,
            "total_interest": 2706800,
            "total_payment": 5206800,
        },
        pipeline_result={
            "is_fully_compliant": True,
            "summary": "Facility complies fully with RBI Master Direction on KFS.",
            "total_duration_ms": 1150,
            "warnings": [],
            "consistency_result": {
                "checks": [
                    {
                        "field_name": "principal",
                        "manual_value": 2500000,
                        "tnc_value": 2500000,
                        "kfs_value": 2500000,
                        "match_status": "match",
                    },
                    {
                        "field_name": "disclosed_rate",
                        "manual_value": 8.5,
                        "tnc_value": 8.5,
                        "kfs_value": 8.5,
                        "match_status": "match",
                    },
                ]
            },
            "verified_claims": [
                {
                    "source_module": "m1_recompute",
                    "verification_status": "grounded",
                    "claim_text": "True APR recomputed at 8.62% p.a.",
                    "verification_result": {"semantic_score": 0.99},
                },
            ],
        },
    )

    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 1000
    assert pdf_bytes.startswith(b"%PDF-")

    # Verify PyMuPDF can parse it and verify pages
    doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    assert len(doc) >= 2
    full_text = "".join(page.get_text() for page in doc)
    assert "GUARDIAN AI" in full_text
    assert "AUDIT REPORT" in full_text
    assert "KEY FACT STATEMENT" in full_text
    assert "RBI/2024-25/18" in full_text
    assert "Gold Home Loan" in full_text
    assert "State Bank of India" in full_text


def test_loan_report_pdf_endpoint():
    """Test the /api/v1/loans/{loan_id}/report/pdf endpoint."""
    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        user_id="test-user-pdf", email="borrower@example.com"
    )

    client = TestClient(app)
    try:
        res = client.post(
            "/api/v1/loans/kfs/report/pdf",
            json={
                "loan_id": "kfs",
                "loan_name": "Personal Express Loan",
                "lender_name": "ICICI Bank",
                "kfs": {
                    "principal": 300000,
                    "disclosed_rate": 11.2,
                    "tenure_months": 36,
                    "monthly_emi": 9850,
                    "processing_fee": 6000,
                },
                "apr": {
                    "principal": 300000,
                    "disclosed_rate": 11.2,
                    "tenure_months": 36,
                    "recomputed_apr": 12.65,
                },
                "pipeline_result": {
                    "is_fully_compliant": True,
                    "summary": "Compliant KFS report.",
                },
            },
        )
        assert res.status_code == 200
        assert res.headers.get("content-type") == "application/pdf"
        assert "Content-Disposition" in res.headers
        assert res.content.startswith(b"%PDF-")
    finally:
        app.dependency_overrides.clear()
