from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException, status
from supabase import Client, create_client
from app.core.config import settings
from app.deps.auth import AuthenticatedUser, get_current_user, verify_user_ownership
from app.schemas.claim import Claim
from app.schemas.serviceability import RecomputeRequest, RecomputeResponse
from modules.m1_recompute.apr_recompute import recompute_apr

router = APIRouter(prefix="/loans/{loan_id}/recompute", tags=["Recompute"])


def get_db_client() -> Client:
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)


def execute_apr_recompute(
    supabase: Client,
    loan_id: str,
    user_id: str,
    payload: Optional[RecomputeRequest] = None,
) -> RecomputeResponse:
    """
    Core function to deterministically compute APR/EMI, emit a Claim, and log audit event.
    Callable from both the HTTP endpoint and document ingestion workflows.
    """
    if payload:
        principal = payload.principal
        rate = payload.disclosed_rate
        tenure = payload.tenure_months
        fees = payload.fees
        source_rec = loan_id
    else:
        # Fallback to stored manual terms or extracted fields from KFS
        terms_res = (
            supabase.table("loan_manual_terms")
            .select("*")
            .eq("loan_id", loan_id)
            .order("entered_at", desc=True)
            .limit(1)
            .execute()
        )
        if terms_res.data:
            t = terms_res.data[0]
            principal = float(t["principal"])
            rate = float(t["disclosed_rate"])
            tenure = int(t["tenure_months"])
            fees = float(t.get("fees", 0.0))
            source_rec = t["id"]
        else:
            # Fallback to latest KFS extracted fields if manual terms absent
            kfs_doc = (
                supabase.table("loan_documents")
                .select("doc_id")
                .eq("loan_id", loan_id)
                .eq("doc_type", "kfs")
                .order("version", desc=True)
                .limit(1)
                .execute()
            )
            if not kfs_doc.data:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No terms provided in payload and no manual/KFS terms found for this loan.",
                )
            kfs_id = kfs_doc.data[0]["doc_id"]
            fields = (
                supabase.table("extracted_fields")
                .select("*")
                .eq("doc_id", kfs_id)
                .execute()
            )
            f_map = {
                row["field_name"]: row["extracted_value"].get("value")
                if isinstance(row["extracted_value"], dict)
                else row["extracted_value"]
                for row in fields.data
            }
            try:
                principal = float(f_map["principal"])
                rate = float(f_map["disclosed_rate"])
                tenure = int(f_map["tenure_months"])
                fees = float(f_map.get("processing_fee") or f_map.get("fees") or 0.0)
                source_rec = kfs_id
            except (KeyError, TypeError, ValueError):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Incomplete terms extracted from KFS document.",
                )

    calc_res = recompute_apr(
        principal=principal,
        disclosed_rate=rate,
        tenure_months=tenure,
        fees=fees,
    )

    claim_id = str(uuid4())
    claim_text = (
        f"For a principal of ₹{principal:,.0f} at disclosed rate {rate:.2f}% over {tenure} months with fees of ₹{fees:,.0f}, "
        f"the true effective APR is {calc_res.recomputed_apr:.2f}% with a monthly EMI of ₹{calc_res.monthly_emi:,.2f}."
    )

    claim = Claim(
        claim_id=claim_id,
        source_module="recompute",
        user_id=user_id,
        loan_id=loan_id,
        claim_text=claim_text,
        supporting_figures={
            "principal": principal,
            "disclosed_rate": rate,
            "tenure_months": tenure,
            "fees": fees,
            "recomputed_apr": calc_res.recomputed_apr,
            "monthly_emi": calc_res.monthly_emi,
        },
        source_record_id=str(source_rec),
        generated_at=datetime.now(timezone.utc),
        verification_status="pending",
    )

    supabase.table("claims").insert(
        {
            "claim_id": claim.claim_id,
            "source_module": claim.source_module,
            "user_id": claim.user_id,
            "loan_id": claim.loan_id,
            "claim_text": claim.claim_text,
            "supporting_figures": claim.supporting_figures,
            "source_record_id": claim.source_record_id,
            "generated_at": claim.generated_at.isoformat(),
            "verification_status": claim.verification_status,
        }
    ).execute()

    supabase.table("audit_log").insert(
        {
            "user_id": user_id,
            "action": "APR_RECOMPUTED",
            "entity_type": "claims",
            "entity_id": claim_id,
            "metadata": {"loan_id": loan_id, "recomputed_apr": calc_res.recomputed_apr},
        }
    ).execute()

    res_dict = calc_res.to_dict()
    res_dict["claim_id"] = claim_id
    return RecomputeResponse(**res_dict)


@router.post("", response_model=RecomputeResponse, status_code=status.HTTP_200_OK)
async def recompute_loan_apr(
    loan_id: str,
    payload: Optional[RecomputeRequest] = None,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> RecomputeResponse:
    """
    Deterministically computes reducing-balance EMI and true effective APR (Module 1).
    Can recompute from explicit payload or automatically fallback to stored manual terms.
    Emits an unverified Claim (source_module="recompute").
    """
    supabase = get_db_client()

    loan_res = supabase.table("loans").select("user_id").eq("id", loan_id).execute()
    if not loan_res.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Loan not found"
        )

    verify_user_ownership(loan_res.data[0]["user_id"], current_user)

    return execute_apr_recompute(
        supabase=supabase,
        loan_id=loan_id,
        user_id=current_user.user_id,
        payload=payload,
    )
