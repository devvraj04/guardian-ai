import pytest
import io
import fitz
from pydantic import ValidationError
from app.schemas.extraction import ExtractedTerms, FieldConfidence
from modules.m0_intake.extraction import extract_raw_text_from_pdf, fallback_regex_extraction


def create_dummy_pdf(text: str) -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 72), text, fontsize=12)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def test_extract_raw_text_digital_pdf():
    contract_text = "SANCTION LETTER\nLoan Amount: Rs. 2,00,000\nInterest Rate: 11.5% p.a.\nTenure: 36 Months\nProcessing Fee: Rs. 2,500"
    pdf_bytes = create_dummy_pdf(contract_text)

    text, method = extract_raw_text_from_pdf(pdf_bytes)
    assert "2,00,000" in text
    assert "11.5%" in text
    assert method in ["pdfplumber", "pymupdf"]


def test_fallback_regex_extraction():
    sample_text = """
    KEY FACT STATEMENT (KFS)
    Sanctioned Amount: Rs. 1,50,000
    Rate of Interest: 14.25% p.a.
    Duration: 24 Months
    Processing Fee: Rs. 1,200
    Prepayment: Foreclosure charges of 2% applicable if closed before 6 months.
    """
    terms = fallback_regex_extraction(sample_text)
    assert terms.principal == 150000.0
    assert terms.disclosed_rate == 14.25
    assert terms.tenure_months == 24
    assert terms.processing_fee == 1200.0
    assert terms.prepayment_clause is not None
    assert "Foreclosure" in terms.prepayment_clause or "prepayment" in terms.prepayment_clause.lower()


def test_extracted_terms_schema_extra_forbidden():
    with pytest.raises(ValidationError):
        ExtractedTerms(
            principal=50000.0,
            disclosed_rate=12.0,
            tenure_months=12,
            unauthorized_field="malicious_injection",  # type: ignore
        )
