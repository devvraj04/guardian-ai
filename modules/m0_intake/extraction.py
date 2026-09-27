import io
import json
import re
from typing import Dict, Optional, Tuple
import fitz  # PyMuPDF
import pdfplumber
from groq import Groq
from app.core.config import settings
from app.core.logging import logger
from app.schemas.extraction import ExtractedTerms, FieldConfidence
from modules.m0_intake.ocr_fallback import extract_text_via_ocr

CONFIDENCE_CONFIRMATION_THRESHOLD = 0.85


def extract_raw_text_from_pdf(pdf_bytes: bytes) -> Tuple[str, str]:
    """
    Dual-path text extractor:
    1. Primary: pdfplumber for digital text and tables
    2. Fallback: PyMuPDF for complex text layouts
    3. Final Fallback: PaddleOCR if character density < 50 chars/page (scanned image)
    Returns: (extracted_text, extraction_method)
    """
    extracted_text = ""
    method = "pdfplumber"

    # Step 1: Attempt digital extraction via pdfplumber
    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            pages_text = []
            for page in pdf.pages:
                text = page.extract_text() or ""
                pages_text.append(text)
            extracted_text = "\n".join(pages_text).strip()
    except Exception as e:
        logger.warning(f"pdfplumber extraction failed: {e}. Falling back to PyMuPDF.")
        extracted_text = ""

    # Step 2: Attempt PyMuPDF if pdfplumber produced sparse text
    if len(extracted_text) < 100:
        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            pymupdf_text = []
            for page in doc:
                pymupdf_text.append(page.get_text() or "")
            doc.close()
            alt_text = "\n".join(pymupdf_text).strip()
            if len(alt_text) > len(extracted_text):
                extracted_text = alt_text
                method = "pymupdf"
        except Exception as e:
            logger.warning(f"PyMuPDF fallback failed: {e}")

    # Step 3: Trigger PaddleOCR if document appears to be a scanned image
    # Condition: Less than 50 characters extracted or empty
    if len(extracted_text.strip()) < 50:
        logger.info("PDF character density is below threshold (< 50 chars). Triggering PaddleOCR fallback.")
        extracted_text = extract_text_via_ocr(pdf_bytes)
        method = "paddleocr"

    return extracted_text.strip(), method


def extract_structured_fields_via_llm(raw_text: str, doc_type: str) -> ExtractedTerms:
    """
    Extracts structured fields from raw contract text using Groq LLM.
    Strictly validates output using ExtractedTerms schema with extra="forbid" (S-6, S-9).
    """
    system_prompt = (
        "You are GUARDIAN's financial contract extraction engine.\n"
        "Your task is to extract exact financial terms from the provided loan document text.\n"
        "You must respond with ONLY valid JSON adhering precisely to this structure:\n"
        "{\n"
        '  "principal": float or null,\n'
        '  "disclosed_rate": float or null,\n'
        '  "tenure_months": int or null,\n'
        '  "processing_fee": float or null,\n'
        '  "prepayment_clause": string or null,\n'
        '  "field_confidences": {\n'
        '    "principal": float between 0.0 and 1.0,\n'
        '    "disclosed_rate": float between 0.0 and 1.0,\n'
        '    "tenure_months": float between 0.0 and 1.0,\n'
        '    "processing_fee": float between 0.0 and 1.0,\n'
        '    "prepayment_clause": float between 0.0 and 1.0\n'
        "  }\n"
        "}\n"
        "Assign lower confidence (< 0.85) if a field is ambiguous, mentioned vaguely, or hard to verify.\n"
        "Do not include any Markdown tags, backticks, or explanatory text. Return ONLY raw JSON."
    )

    user_prompt = f"DOCUMENT TYPE: {doc_type.upper()}\n\nDOCUMENT TEXT:\n{raw_text[:8000]}"

    try:
        client = Groq(api_key=settings.GROQ_API_KEY)
        response = client.chat.completions.create(
            model=settings.GROQ_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.0,
        )

        response_content = response.choices[0].message.content or "{}"
        parsed = json.loads(response_content)
        return ExtractedTerms.model_validate(parsed)

    except Exception as e:
        logger.warning(f"Groq structured extraction failed: {type(e).__name__} - {e}. Using deterministic regex fallback.")
        return fallback_regex_extraction(raw_text)


def fallback_regex_extraction(text: str) -> ExtractedTerms:
    """
    Deterministic regex fallback when LLM API is unavailable or rate-limited.
    Provides conservative confidence scores.
    """
    conf = FieldConfidence(
        principal=0.7,
        disclosed_rate=0.7,
        tenure_months=0.7,
        processing_fee=0.7,
        prepayment_clause=0.7,
    )

    principal: Optional[float] = None
    rate: Optional[float] = None
    tenure: Optional[int] = None
    fee: Optional[float] = None
    prepay: Optional[str] = None

    # Principal matching (e.g. Loan Amount: Rs. 50,000 or INR 50000)
    p_match = re.search(r"(?:loan\s+amount|principal|sanctioned\s+amount)[:\s]*(?:rs\.?|inr|₹)?\s*([\d,]+(?:\.\d+)?)", text, re.I)
    if p_match:
        try:
            principal = float(p_match.group(1).replace(",", ""))
            conf.principal = 0.88
        except ValueError:
            pass

    # Rate matching (e.g. Interest Rate: 14.5% or 14% p.a.)
    r_match = re.search(r"(?:interest\s+rate|rate\s+of\s+interest|roi)[:\s]*([\d\.]+)\s*%", text, re.I)
    if r_match:
        try:
            rate = float(r_match.group(1))
            conf.disclosed_rate = 0.90
        except ValueError:
            pass

    # Tenure matching (e.g. Tenure: 24 Months)
    t_match = re.search(r"(?:tenure|duration|term)[:\s]*(\d+)\s*(?:months|m)", text, re.I)
    if t_match:
        try:
            tenure = int(t_match.group(1))
            conf.tenure_months = 0.90
        except ValueError:
            pass

    # Fee matching (e.g. Processing Fee: Rs. 1,000)
    f_match = re.search(r"(?:processing\s+fee|upfront\s+charges)[:\s]*(?:rs\.?|inr|₹)?\s*([\d,]+(?:\.\d+)?)", text, re.I)
    if f_match:
        try:
            fee = float(f_match.group(1).replace(",", ""))
            conf.processing_fee = 0.85
        except ValueError:
            pass

    # Prepayment clause search
    pre_match = re.search(r"(?:prepayment|foreclosure)[^\.\n]+(?:\.|\n)", text, re.I)
    if pre_match:
        prepay = pre_match.group(0).strip()
        conf.prepayment_clause = 0.80

    return ExtractedTerms(
        principal=principal,
        disclosed_rate=rate,
        tenure_months=tenure,
        processing_fee=fee,
        prepayment_clause=prepay,
        field_confidences=conf,
    )
