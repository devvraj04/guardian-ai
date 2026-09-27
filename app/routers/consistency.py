from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException, status
from supabase import Client, create_client

from app.core.config import settings
from app.core.logging import logger
from app.deps.auth import AuthenticatedUser, get_current_user
from app.schemas.consistency import ConsistencyCheckResponse, FieldComparison
from modules.m2_consistency.consistency import run_consistency_check

router = APIRouter(prefix="/loans", tags=["Consistency Check"])


def get_db_client() -> Client:
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)


@router.post("/{loan_id}/consistency", response_model=ConsistencyCheckResponse)
async def check_loan_consistency(
    loan_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> ConsistencyCheckResponse:
    """
    Executes a three-way cross-source consistency check across:
    1. Manual Terms (`loan_manual_terms`)
    2. T&C Extracted Fields (`extracted_fields` for latest T&C document)
    3. KFS Extracted Fields (`extracted_fields` for latest KFS document)

    Populates `consistency_checks` table, generates an unverified `Claim` (source_module="consistency"),
    and logs an audit trail record (S-21).
    """
    supabase = get_db_client()

    # Step 1: Server-side loan ownership check (S-3)
    loan_res = supabase.table("loans").select("*").eq("id", loan_id).execute()
    if not loan_res.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Loan with ID {loan_id} not found.",
        )
    loan = loan_res.data[0]
    if loan["user_id"] != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: loan does not belong to authenticated user.",
        )

    # Step 2: Fetch Manual Terms
    manual_res = (
        supabase.table("loan_manual_terms")
        .select("*")
        .eq("loan_id", loan_id)
        .order("entered_at", desc=True)
        .limit(1)
        .execute()
    )
    manual_terms: Optional[Dict[str, Any]] = None
    if manual_res.data:
        manual_row = manual_res.data[0]
        manual_terms = {
            "principal": float(manual_row["principal"]) if manual_row.get("principal") is not None else None,
            "disclosed_rate": float(manual_row["disclosed_rate"]) if manual_row.get("disclosed_rate") is not None else None,
            "tenure_months": int(manual_row["tenure_months"]) if manual_row.get("tenure_months") is not None else None,
            "fees": float(manual_row["fees"]) if manual_row.get("fees") is not None else None,
        }

    # Step 3: Fetch latest T&C document and its extracted fields
    tnc_doc_res = (
        supabase.table("loan_documents")
        .select("*")
        .eq("loan_id", loan_id)
        .eq("doc_type", "tnc")
        .order("version", desc=True)
        .limit(1)
        .execute()
    )
    tnc_extracted: Optional[Dict[str, Any]] = None
    if tnc_doc_res.data:
        tnc_doc_id = tnc_doc_res.data[0]["doc_id"]
        fields_res = (
            supabase.table("extracted_fields")
            .select("field_name, extracted_value")
            .eq("doc_id", tnc_doc_id)
            .execute()
        )
        if fields_res.data:
            tnc_extracted = {}
            for item in fields_res.data:
                fname = item["field_name"]
                val = item["extracted_value"]
                # extracted_value is stored as {"value": ...} in extracted_fields
                if isinstance(val, dict) and "value" in val:
                    tnc_extracted[fname] = val["value"]
                else:
                    tnc_extracted[fname] = val

    # Step 4: Fetch latest KFS document and its extracted fields
    kfs_doc_res = (
        supabase.table("loan_documents")
        .select("*")
        .eq("loan_id", loan_id)
        .eq("doc_type", "kfs")
        .order("version", desc=True)
        .limit(1)
        .execute()
    )
    kfs_extracted: Optional[Dict[str, Any]] = None
    if kfs_doc_res.data:
        kfs_doc_id = kfs_doc_res.data[0]["doc_id"]
        fields_res = (
            supabase.table("extracted_fields")
            .select("field_name, extracted_value")
            .eq("doc_id", kfs_doc_id)
            .execute()
        )
        if fields_res.data:
            kfs_extracted = {}
            for item in fields_res.data:
                fname = item["field_name"]
                val = item["extracted_value"]
                if isinstance(val, dict) and "value" in val:
                    kfs_extracted[fname] = val["value"]
                else:
                    kfs_extracted[fname] = val

    # Step 5: Execute consistency matching
    checks, overall_status, summary_explanation, requires_human_review = run_consistency_check(
        manual_terms=manual_terms,
        tnc_extracted=tnc_extracted,
        kfs_extracted=kfs_extracted,
    )

    checked_at = datetime.now(timezone.utc).isoformat()

    # Step 6: Persist each comparison row into consistency_checks table
    for c in checks:
        check_record = {
            "loan_id": loan_id,
            "field_name": c.field_name,
            "manual_value": {"value": c.manual_value} if c.manual_value is not None else None,
            "tnc_value": {"value": c.tnc_value} if c.tnc_value is not None else None,
            "kfs_value": {"value": c.kfs_value} if c.kfs_value is not None else None,
            "match_status": c.match_status,
            "checked_at": checked_at,
        }
        supabase.table("consistency_checks").insert(check_record).execute()

    # Step 7: Emit unverified Claim into claims table (RULES.md §1.1, §1.8)
    claim_id = str(uuid4())
    mismatches = [c for c in checks if c.match_status == "mismatch"]
    missings = [c for c in checks if c.match_status == "missing"]
    matches = [c for c in checks if c.match_status == "match"]

    claim_record = {
        "claim_id": claim_id,
        "source_module": "consistency",
        "user_id": current_user.user_id,
        "loan_id": loan_id,
        "claim_text": summary_explanation,
        "supporting_figures": {
            "overall_status": overall_status,
            "mismatch_count": len(mismatches),
            "match_count": len(matches),
            "missing_count": len(missings),
            "mismatched_fields": [c.field_name for c in mismatches],
            "requires_human_review": requires_human_review,
        },
        "source_record_id": loan_id,
        "generated_at": checked_at,
        "verification_status": "pending",
    }
    supabase.table("claims").insert(claim_record).execute()

    # Step 8: Log in append-only audit_log (S-21)
    supabase.table("audit_log").insert({
        "user_id": current_user.user_id,
        "action": "CONSISTENCY_CHECK_PERFORMED",
        "entity_type": "loans",
        "entity_id": loan_id,
        "metadata": {
            "overall_status": overall_status,
            "mismatch_count": len(mismatches),
            "claim_id": claim_id,
            "requires_human_review": requires_human_review,
        },
    }).execute()

    return ConsistencyCheckResponse(
        loan_id=loan_id,
        overall_status=overall_status,
        mismatch_count=len(mismatches),
        missing_count=len(missings),
        match_count=len(matches),
        checks=checks,
        claim_id=claim_id,
        summary_explanation=summary_explanation,
        requires_human_review=requires_human_review,
    )
