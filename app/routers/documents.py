from datetime import datetime, timezone
import os
from typing import List, Literal
from uuid import uuid4
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from supabase import Client, create_client
from app.core.config import settings
from app.core.logging import logger
from app.deps.auth import AuthenticatedUser, get_current_user, verify_user_ownership
from app.schemas.extraction import DocumentUploadResponse, ExtractedFieldItem, ExtractedTerms
from modules.m0_intake.extraction import (
    CONFIDENCE_CONFIRMATION_THRESHOLD,
    extract_raw_text_from_pdf,
    extract_structured_fields_via_llm,
)
from rag.ingest_user_docs import ingest_document_into_chroma

router = APIRouter(prefix="/loans/{loan_id}/documents", tags=["Documents"])

MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB limit (S-8)
ALLOWED_DOC_TYPES = ["tnc", "kfs"]
STORAGE_BUCKET = "loan-documents"


def get_db_client() -> Client:
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)


def ensure_storage_bucket(supabase: Client):
    try:
        supabase.storage.get_bucket(STORAGE_BUCKET)
    except Exception:
        try:
            supabase.storage.create_bucket(STORAGE_BUCKET, options={"public": False})
        except Exception as e:
            logger.info(f"Storage bucket verification note: {e}")


@router.post("/upload", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_loan_document(
    loan_id: str,
    doc_type: str = Form(..., description="Document type: 'tnc' or 'kfs'"),
    file: UploadFile = File(..., description="PDF document file"),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> DocumentUploadResponse:
    """
    Uploads a T&C or KFS PDF document, extracts text with PaddleOCR fallback,
    indexes clauses into ChromaDB, and extracts structured contract terms (Module 0).
    """
    if doc_type.lower() not in ALLOWED_DOC_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid doc_type '{doc_type}'. Must be 'tnc' or 'kfs'",
        )
    doc_type = doc_type.lower()

    supabase = get_db_client()

    # Step 1: Verify loan ownership (S-3)
    loan_res = supabase.table("loans").select("user_id").eq("id", loan_id).execute()
    if not loan_res.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Loan not found")

    verify_user_ownership(loan_res.data[0]["user_id"], current_user)

    # Step 2: Validate file MIME type and magic header (S-8)
    if file.content_type not in ["application/pdf", "application/x-pdf"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file format. Only PDF documents (application/pdf) are permitted.",
        )

    file_bytes = await file.read()
    if len(file_bytes) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum allowed size of {MAX_FILE_SIZE_BYTES // (1024 * 1024)}MB",
        )

    if not file_bytes.startswith(b"%PDF"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File header does not match valid PDF specification.",
        )

    # Step 3: Determine document versioning
    existing_docs = (
        supabase.table("loan_documents")
        .select("version")
        .eq("loan_id", loan_id)
        .eq("doc_type", doc_type)
        .order("version", desc=True)
        .limit(1)
        .execute()
    )
    current_version = 1
    if existing_docs.data:
        current_version = existing_docs.data[0]["version"] + 1

    doc_id = str(uuid4())
    storage_path = f"{current_user.user_id}/{loan_id}/{doc_type}_v{current_version}.pdf"

    # Step 4: Upload to Supabase Storage
    try:
        ensure_storage_bucket(supabase)
        supabase.storage.from_(STORAGE_BUCKET).upload(
            path=storage_path,
            file=file_bytes,
            file_options={"content-type": "application/pdf", "upsert": "true"},
        )
    except Exception as e:
        logger.warning(f"Supabase storage upload note: {e}. Storing path reference.")

    # Step 5: Insert loan_documents row
    doc_record = {
        "doc_id": doc_id,
        "loan_id": loan_id,
        "doc_type": doc_type,
        "storage_path": storage_path,
        "version": current_version,
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
    }
    supabase.table("loan_documents").insert(doc_record).execute()

    # Log document upload in audit_log (S-21)
    supabase.table("audit_log").insert({
        "user_id": current_user.user_id,
        "action": "DOCUMENT_UPLOADED",
        "entity_type": "loan_documents",
        "entity_id": doc_id,
        "metadata": {"doc_type": doc_type, "version": current_version, "loan_id": loan_id},
    }).execute()

    # Step 6: Extract raw text with PaddleOCR fallback
    raw_text, extraction_method = extract_raw_text_from_pdf(file_bytes)

    # Step 7: Chunk and ingest into ChromaDB (RULES.md §2)
    ingest_document_into_chroma(
        user_id=current_user.user_id,
        loan_id=loan_id,
        doc_type=doc_type,
        doc_id=doc_id,
        raw_text=raw_text,
    )

    # Step 8: Structured field extraction via Groq LLM (S-6, S-9)
    extracted_terms: ExtractedTerms = extract_structured_fields_via_llm(raw_text, doc_type)

    # Step 9: Persist extracted fields to database
    fields_to_persist = [
        ("principal", extracted_terms.principal, extracted_terms.field_confidences.principal),
        ("disclosed_rate", extracted_terms.disclosed_rate, extracted_terms.field_confidences.disclosed_rate),
        ("tenure_months", extracted_terms.tenure_months, extracted_terms.field_confidences.tenure_months),
        ("processing_fee", extracted_terms.processing_fee, extracted_terms.field_confidences.processing_fee),
        ("prepayment_clause", extracted_terms.prepayment_clause, extracted_terms.field_confidences.prepayment_clause),
    ]

    saved_field_items: List[ExtractedFieldItem] = []
    for field_name, value, conf in fields_to_persist:
        field_id = str(uuid4())
        needs_confirm = conf < CONFIDENCE_CONFIRMATION_THRESHOLD
        field_record = {
            "id": field_id,
            "doc_id": doc_id,
            "field_name": field_name,
            "extracted_value": {"value": value},
            "confidence": float(conf),
            "extraction_method": extraction_method,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        supabase.table("extracted_fields").insert(field_record).execute()

        saved_field_items.append(
            ExtractedFieldItem(
                id=field_id,
                doc_id=doc_id,
                field_name=field_name,
                extracted_value=value,
                confidence=conf,
                extraction_method=extraction_method,
                needs_manual_confirmation=needs_confirm,
                created_at=datetime.now(timezone.utc),
            )
        )

    # Log extraction completion in audit_log (S-21)
    supabase.table("audit_log").insert({
        "user_id": current_user.user_id,
        "action": "FIELDS_EXTRACTED",
        "entity_type": "extracted_fields",
        "entity_id": doc_id,
        "metadata": {
            "doc_type": doc_type,
            "extraction_method": extraction_method,
            "fields_count": len(saved_field_items),
        },
    }).execute()

    return DocumentUploadResponse(
        doc_id=doc_id,
        loan_id=loan_id,
        doc_type=doc_type,
        storage_path=storage_path,
        version=current_version,
        uploaded_at=datetime.now(timezone.utc),
        extraction_status="completed",
        extracted_fields=saved_field_items,
    )


@router.get("", response_model=List[dict])
async def list_loan_documents(
    loan_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> List[dict]:
    supabase = get_db_client()
    loan_res = supabase.table("loans").select("user_id").eq("id", loan_id).execute()
    if not loan_res.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Loan not found")

    verify_user_ownership(loan_res.data[0]["user_id"], current_user)

    res = (
        supabase.table("loan_documents")
        .select("*")
        .eq("loan_id", loan_id)
        .order("uploaded_at", desc=True)
        .execute()
    )
    return res.data


@router.get("/{doc_id}/fields", response_model=List[ExtractedFieldItem])
async def get_document_fields(
    loan_id: str,
    doc_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> List[ExtractedFieldItem]:
    supabase = get_db_client()
    loan_res = supabase.table("loans").select("user_id").eq("id", loan_id).execute()
    if not loan_res.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Loan not found")

    verify_user_ownership(loan_res.data[0]["user_id"], current_user)

    res = supabase.table("extracted_fields").select("*").eq("doc_id", doc_id).execute()
    items = []
    for row in res.data:
        val = row["extracted_value"].get("value") if isinstance(row["extracted_value"], dict) else row["extracted_value"]
        items.append(
            ExtractedFieldItem(
                id=row["id"],
                doc_id=row["doc_id"],
                field_name=row["field_name"],
                extracted_value=val,
                confidence=float(row["confidence"]),
                extraction_method=row["extraction_method"],
                needs_manual_confirmation=float(row["confidence"]) < CONFIDENCE_CONFIRMATION_THRESHOLD,
                created_at=datetime.fromisoformat(row["created_at"].replace("Z", "+00:00")),
            )
        )
    return items
