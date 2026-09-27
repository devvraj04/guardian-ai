# Module 0: Loan Intake & Document Ingestion

## 1. Overview
Module 0 is responsible for consumer loan intake and contract document ingestion. It handles manual term entry, PDF upload for Terms & Conditions (T&C) and Key Fact Statements (KFS), dual-path text extraction with PaddleOCR fallback for scanned PDFs, clause-level chunking into ChromaDB, and structured field extraction with confidence scores.

## 2. Architecture & Pipeline
1. **Manual Terms Entry**:
   - `POST /api/v1/loans/{id}/terms` writes user-declared parameters (`principal`, `disclosed_rate`, `tenure_months`, `fees`) to `loan_manual_terms`.
2. **Document Ingestion**:
   - File upload via `POST /api/v1/loans/{id}/documents/upload`.
   - Security validation (Rule S-8): `application/pdf` MIME check, magic `%PDF` byte header check, 10MB file size limit.
   - Versioned storage in Supabase Storage (`loan-documents` bucket).
3. **Dual-Path Text Extraction**:
   - Primary: `pdfplumber` (tables, structured layouts).
   - Fallback: `PyMuPDF` (dense digital layouts).
   - Scanned OCR Fallback: If average character density is `< 50` chars/page, `PaddleOCR` is automatically triggered.
4. **ChromaDB Scoping (RULES.md §2)**:
   - Extracted text is split into semantic clauses via `chunker.py`.
   - Indexed via `rag/chroma_client.py` into the `user_documents` collection strictly stamped with `{user_id, loan_id, doc_type}` metadata.
5. **Structured Field Extraction**:
   - Groq LLM extracts `{principal, disclosed_rate, tenure_months, processing_fee, prepayment_clause}` with confidence scores (`0.0`–`1.0`).
   - Validated against Pydantic schema `ExtractedTerms` with `extra="forbid"` (Rule S-6, S-9).
   - Fields with confidence `< 0.85` are flagged with `needs_manual_confirmation: true`.
6. **Append-Only Audit Logging (Rule S-21/S-22)**:
   - `DOCUMENT_UPLOADED` and `FIELDS_EXTRACTED` actions are inserted into `audit_log`.

## 3. Directory Layout
```
modules/m0_intake/
├── __init__.py
├── chunker.py             # Clause-level chunking
├── extraction.py          # Dual-path extraction + Groq LLM extraction
├── ocr_fallback.py        # PaddleOCR pipeline for image-based PDFs
├── metrics.json           # Accuracy and latency evaluation
├── README.md              # This documentation
└── tests/
    ├── __init__.py
    ├── test_chunker.py
    └── test_extraction.py
```

## 4. Running Tests
To run unit tests for this module:
```powershell
pytest modules/m0_intake/tests -v
```
