import io
import json
import re
from typing import Optional, Tuple
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
        logger.info(
            "PDF character density is below threshold (< 50 chars). Triggering PaddleOCR fallback."
        )
        extracted_text = extract_text_via_ocr(pdf_bytes)
        method = "paddleocr"

    return extracted_text.strip(), method


def extract_structured_fields_via_llm(raw_text: str, doc_type: str) -> ExtractedTerms:
    """
    Extracts structured fields from raw contract text using Groq LLM.
    Strictly parses all standardized RBI Key Fact Statement (KFS) fields across any bank or NBFC.
    """
    system_prompt = (
        "You are GUARDIAN's financial contract extraction engine for RBI-mandated Key Fact Statements (KFS).\n"
        "Your task is to extract exact financial terms and qualitative disclosures from any Indian Bank or NBFC KFS document.\n"
        "You must respond with ONLY valid JSON adhering precisely to this structure:\n"
        "{\n"
        '  "bank_name": string or null,\n'
        '  "loan_type": string or null,\n'
        '  "principal": float or null,\n'
        '  "disclosed_rate": float or null,\n'
        '  "interest_type": string or null,\n'
        '  "tenure_months": int or null,\n'
        '  "monthly_emi": float or null,\n'
        '  "processing_fee": float or null,\n'
        '  "net_disbursed_amount": float or null,\n'
        '  "total_interest_amount": float or null,\n'
        '  "total_repayment_amount": float or null,\n'
        '  "apr": float or null,\n'
        '  "prepayment_clause": string or null,\n'
        '  "penal_charges": string or null,\n'
        '  "bounce_charges": float or null,\n'
        '  "cooling_off_period": string or null,\n'
        '  "grievance_email": string or null,\n'
        '  "grievance_phone": string or null,\n'
        '  "field_confidences": {\n'
        '    "principal": float between 0.0 and 1.0,\n'
        '    "disclosed_rate": float between 0.0 and 1.0,\n'
        '    "tenure_months": float between 0.0 and 1.0,\n'
        '    "processing_fee": float between 0.0 and 1.0,\n'
        '    "prepayment_clause": float between 0.0 and 1.0\n'
        "  }\n"
        "}\n"
        "Universal RBI KFS Field Definitions:\n"
        "- bank_name: Name of Regulated Entity (e.g. State Bank of India, HDFC Bank, Bandhan Bank, ICICI Bank, Axis Bank, Bajaj Finance, etc.)\n"
        "- loan_type: Type of loan (Housing Finance, Personal Loan, Vehicle Loan, MSME, Digital Loan)\n"
        "- principal: Sanctioned loan amount in INR (Part 1 Item 2 or Annexure B Item 1)\n"
        "- disclosed_rate: Annualized rate of interest percentage (Part 1 Item 6 or Item 7 or Annexure B Item 4)\n"
        "- interest_type: 'Fixed', 'Floating', or 'Hybrid' (Part 1 Item 6)\n"
        "- tenure_months: Loan tenor in months (Part 1 Item 4 or Annexure B Item 2)\n"
        "- monthly_emi: Equated Periodic Instalment (EPI) amount in INR (Part 1 Item 5 or Annexure B Item 2b.ii)\n"
        "- processing_fee: Total upfront fees and charges payable (Part 1 Item 8 or Annexure B Item 6)\n"
        "- net_disbursed_amount: Net amount disbursed to borrower = Principal minus upfront charges (Annexure B Item 7)\n"
        "- total_interest_amount: Total interest to be charged over entire tenor (Annexure B Item 5)\n"
        "- total_repayment_amount: Total amount to be repaid by borrower = Principal + Total Interest (Annexure B Item 8)\n"
        "- apr: Annual Percentage Rate % computed via IRR reducing balance approach (Part 1 Item 9 or Annexure B Item 9)\n"
        "- prepayment_clause: Exact prepayment/foreclosure terms. Specifically note if floating rate for individuals is NIL charges.\n"
        "- penal_charges: Penal charges for late payment (Part 1 Item 10(I))\n"
        "- bounce_charges: Cheque/ECS/NACH bounce charges in INR (Part 1 Item 10(II))\n"
        "- cooling_off_period: Look-up / cooling-off period for loan exit without penalty (Part 2 Item 6)\n"
        "- grievance_email: Nodal Grievance Redressal Officer email (Part 2 Item 3)\n"
        "- grievance_phone: Grievance Redressal helpline or phone number (Part 2 Item 2/3)\n"
        "Assign lower confidence (< 0.85) if a field is not stated, blank, or ambiguous in the text.\n"
        "Return ONLY raw JSON with no Markdown commentary."
    )

    user_prompt = (
        f"DOCUMENT TYPE: {doc_type.upper()}\n\nDOCUMENT TEXT:\n{raw_text[:25000]}"
    )

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
        logger.warning(
            f"Groq structured extraction failed: {type(e).__name__} - {e}. Using deterministic regex fallback."
        )
        return fallback_regex_extraction(raw_text)


def fallback_regex_extraction(text: str) -> ExtractedTerms:
    """
    Deterministic regex fallback when LLM API is unavailable or rate-limited.
    Equipped with universal patterns for all standard RBI Key Fact Statement formats.
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
    emi: Optional[float] = None
    apr_val: Optional[float] = None
    penal: Optional[str] = None
    bounce: Optional[float] = None
    bank_name: Optional[str] = None
    loan_type: Optional[str] = None
    interest_type: Optional[str] = None
    net_disbursed: Optional[float] = None
    total_interest: Optional[float] = None
    total_repayment: Optional[float] = None
    cooling_off: Optional[str] = None
    grievance_email: Optional[str] = None
    grievance_phone: Optional[str] = None

    # Detect Lender / Bank Name
    bank_match = re.search(
        r"(?:name\s+of\s+the\s+originating\s+re|regulated\s+entity|lender|bank)[\s\:\-]+([A-Za-z\s]+(?:bank|finance|nbfc|capital|ltd|limited))",
        text,
        re.I,
    )
    if bank_match:
        bank_name = bank_match.group(1).strip()
    elif re.search(r"bandhan\s+bank", text, re.I):
        bank_name = "Bandhan Bank"
    elif re.search(r"state\s+bank\s+of\s+india|sbi", text, re.I):
        bank_name = "State Bank of India"
    elif re.search(r"hdfc\s+bank", text, re.I):
        bank_name = "HDFC Bank"
    elif re.search(r"icici\s+bank", text, re.I):
        bank_name = "ICICI Bank"
    elif re.search(r"axis\s+bank", text, re.I):
        bank_name = "Axis Bank"
    elif re.search(r"kotak\s+(?:mahindra\s+)?bank", text, re.I):
        bank_name = "Kotak Mahindra Bank"
    elif re.search(r"bajaj\s+finance", text, re.I):
        bank_name = "Bajaj Finance"

    # Detect Loan Type
    lt_match = re.search(r"type\s+of\s+loan[\s\:\-]+([A-Za-z\s]+)(?:\n|$|\r)", text, re.I)
    if lt_match and len(lt_match.group(1).strip()) > 2:
        loan_type = lt_match.group(1).strip()
    elif re.search(r"housing\s+finance|home\s+loan", text, re.I):
        loan_type = "Housing Finance"
    elif re.search(r"personal\s+loan", text, re.I):
        loan_type = "Personal Loan"
    elif re.search(r"vehicle\s+loan|auto\s+loan", text, re.I):
        loan_type = "Vehicle Loan"
    elif re.search(r"digital\s+lending|digital\s+loan", text, re.I):
        loan_type = "Digital Loan"

    # Interest Type
    if re.search(r"interest\s+type[\s\:\-]+floating", text, re.I) or re.search(r"\bfloating\s+rate\b", text, re.I):
        interest_type = "Floating"
    elif re.search(r"interest\s+type[\s\:\-]+fixed", text, re.I) or re.search(r"\bfixed\s+rate\b", text, re.I):
        interest_type = "Fixed"

    # Principal matching (Part 1 Item 2 or Annexure B Item 1)
    p_patterns = [
        r"(?:sanctioned\s+loan\s+amount\s*(?:\(in\s*₹\))?|loan\s+amount|principal|sanctioned\s+amount)[\s\:\-]+(?:rs\.?|inr|₹)?\s*([\d,]+(?:\.\d+)?)",
        r"1\s+Sanctioned\s+loan\s+amount[^\d]+([\d,]+(?:\.\d+)?)",
    ]
    for pat in p_patterns:
        p_match = re.search(pat, text, re.I)
        if p_match:
            try:
                principal = float(p_match.group(1).replace(",", ""))
                conf.principal = 0.90
                break
            except ValueError:
                pass

    # Rate matching (Part 1 Item 6, Item 7, or Annexure B Item 4)
    r_patterns = [
        r"(?:final\s+rate\s*\(%\)\s*r\s*=\s*\(b\)\s*\+\s*\(s\)|rate\s+of\s+interest\s*\*\*?\s*\(%\)|rate\s+of\s+interest|roi)[\s\:\-]+([\d\.]+)\s*%?",
        r"4\s+Rate\s+of\s+interest[\s\:\-]+([\d\.]+)",
    ]
    for pat in r_patterns:
        r_match = re.search(pat, text, re.I)
        if r_match:
            try:
                rate = float(r_match.group(1))
                conf.disclosed_rate = 0.90
                break
            except ValueError:
                pass

    # Tenure matching (Part 1 Item 4 or Annexure B Item 2)
    t_patterns = [
        r"(?:loan\s+tenor\s*\(in\s*months\)|loan\s+tenor|tenure|duration|term)[\s\:\-]+(\d+)",
        r"2\s+Loan\s+tenor[^\d]+(\d+)",
    ]
    for pat in t_patterns:
        t_match = re.search(pat, text, re.I)
        if t_match:
            try:
                tenure = int(t_match.group(1))
                conf.tenure_months = 0.90
                break
            except ValueError:
                pass

    # Monthly EMI / EPI matching (Part 1 Item 5 or Annexure B Item 2b.ii)
    emi_match = re.search(
        r"(?:amount\s+of\s+each\s+epi\s*\(in\s*₹\)|epi\s*\*?\s*\(in\s*₹\)|monthly\s+emi|emi)[\s\:\-]+(?:rs\.?|inr|₹)?\s*([\d,]+(?:\.\d+)?)",
        text,
        re.I,
    )
    if emi_match:
        try:
            emi = float(emi_match.group(1).replace(",", ""))
        except ValueError:
            pass

    # Upfront Fees / Charges (Part 1 Item 8 or Annexure B Item 6)
    f_match = re.search(
        r"(?:total\s+fees|fee\/charges\s+payable|processing\s+fee|upfront\s+charges)[\s\:\-]+(?:rs\.?|inr|₹)?\s*([\d,]+(?:\.\d+)?)",
        text,
        re.I,
    )
    if f_match:
        try:
            fee = float(f_match.group(1).replace(",", ""))
            conf.processing_fee = 0.88
        except ValueError:
            fee = None

    # Net Disbursed Amount (Annexure B Item 7)
    nd_match = re.search(
        r"net\s+disbursed\s+amount[^\d₹]*₹?\s*([\d,]+(?:\.\d+)?)", text, re.I
    )
    if nd_match:
        try:
            net_disbursed = float(nd_match.group(1).replace(",", ""))
        except ValueError:
            pass

    # Total Interest Amount (Annexure B Item 5)
    ti_match = re.search(
        r"total\s+interest\s+amount[^\d₹]*₹?\s*([\d,]+(?:\.\d+)?)", text, re.I
    )
    if ti_match:
        try:
            total_interest = float(ti_match.group(1).replace(",", ""))
        except ValueError:
            pass

    # Total Amount to be Paid (Annexure B Item 8)
    tr_match = re.search(
        r"total\s+amount\s+to\s+be\s+paid[^\d₹]*₹?\s*([\d,]+(?:\.\d+)?)", text, re.I
    )
    if tr_match:
        try:
            total_repayment = float(tr_match.group(1).replace(",", ""))
        except ValueError:
            pass

    # APR matching (Part 1 Item 9 or Annexure B Item 9)
    apr_match = re.search(
        r"(?:annual\s+percentage\s+rate\s*(?:\(apr\))?\s*(?:\(%\))?|effective\s+annualised\s+interest\s+rate)[\s\:\-]+([\d\.]+)\s*%?",
        text,
        re.I,
    )
    if apr_match:
        try:
            apr_val = float(apr_match.group(1))
        except ValueError:
            pass

    # Prepayment Clause (Part 1 Item 10)
    if re.search(r"prepayment\s+charges\s+on\s+floating\s+roi", text, re.I):
        if re.search(r"individual[^\n]*nil\s+charges", text, re.I):
            prepay = "Floating rate loan to individual borrower: NIL prepayment charges (RBI compliant)."
            conf.prepayment_clause = 0.95
        else:
            prepay = "Floating rate prepayment subject to KFS terms."
            conf.prepayment_clause = 0.85
    else:
        pre_match = re.search(r"(?:prepayment|foreclosure)[^\.\n]+(?:\.|\n)", text, re.I)
        if pre_match:
            prepay = pre_match.group(0).strip()
            conf.prepayment_clause = 0.80

    # Penal Charges (Part 1 Item 10(I))
    penal_match = re.search(
        r"penal\s+charges[^\d%]*([\d\.]+\s*%\s*(?:of\s+overdue\s+amount)?(?:\s*\+\s*applicable\s*gst)?)",
        text,
        re.I,
    )
    if penal_match:
        penal = penal_match.group(1).strip()
    elif re.search(r"2\.00%\s+of\s+overdue\s+amount", text, re.I):
        penal = "2.00% of overdue amount + applicable GST"

    # Bounce Charges (Part 1 Item 10(II))
    bounce_match = re.search(
        r"(?:bounce\s+charges|cheque\/si\/nach\s+bounce\s+charges)[^\d₹]*₹?\s*([\d,]+)",
        text,
        re.I,
    )
    if bounce_match:
        try:
            bounce = float(bounce_match.group(1).replace(",", ""))
        except ValueError:
            pass

    # Cooling-off Period (Part 2 Item 6)
    cool_match = re.search(
        r"cooling\s*off[^\.\n]+(?:\.|\n)", text, re.I
    )
    if cool_match:
        cooling_off = cool_match.group(0).strip()

    # Grievance details (Part 2 Item 2 & 3)
    email_match = re.search(r"[\w\.-]+@[\w\.-]+\.(?:com|in|org|net)", text)
    if email_match:
        grievance_email = email_match.group(0)

    phone_match = re.search(r"(?:1800[-\s]?\d{3}[-\s]?\d{3,4}|0\d{2,4}[-\s]?\d{6,8})", text)
    if phone_match:
        grievance_phone = phone_match.group(0)

    return ExtractedTerms(
        principal=principal,
        disclosed_rate=rate,
        tenure_months=tenure,
        processing_fee=fee or 0.0,
        prepayment_clause=prepay,
        monthly_emi=emi,
        apr=apr_val,
        penal_charges=penal,
        bounce_charges=bounce,
        bank_name=bank_name,
        loan_type=loan_type,
        interest_type=interest_type,
        net_disbursed_amount=net_disbursed,
        total_interest_amount=total_interest,
        total_repayment_amount=total_repayment,
        cooling_off_period=cooling_off,
        grievance_email=grievance_email,
        grievance_phone=grievance_phone,
        field_confidences=conf,
    )
