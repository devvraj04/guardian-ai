from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from supabase import Client, create_client

from app.core.config import settings
from app.deps.auth import AuthenticatedUser, get_current_user, verify_user_ownership
from app.schemas.claim import Claim
from app.schemas.vernacular import (
    VernacularTranslationRequest,
    VernacularVerificationResponse,
)
from modules.m4_vernacular.vernacular_verifier import verify_vernacular_claim

router = APIRouter(prefix="/loans/{loan_id}/claims", tags=["Vernacular Verification"])


def get_db_client() -> Client:
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)


@router.post(
    "/{claim_id}/translate",
    response_model=VernacularVerificationResponse,
    status_code=status.HTTP_200_OK,
)
async def translate_and_verify_claim_endpoint(
    loan_id: str,
    claim_id: str,
    payload: VernacularTranslationRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> VernacularVerificationResponse:
    """
    Translates a claim into Hindi or Marathi, back-translates, computes cross-lingual metrics,
    and runs Module 3 verification on the back-translation (RULES.md §1.6).
    """
    supabase = get_db_client()

    # Step 1: Verify loan ownership (Rule S-3)
    loan_res = supabase.table("loans").select("user_id").eq("id", loan_id).execute()
    if not loan_res.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Loan not found"
        )
    verify_user_ownership(loan_res.data[0]["user_id"], current_user)

    # Step 2: Fetch Claim record
    claim_res = supabase.table("claims").select("*").eq("claim_id", claim_id).execute()
    if not claim_res.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Claim {claim_id} not found",
        )

    row = claim_res.data[0]
    gen_at = (
        datetime.fromisoformat(row["generated_at"])
        if row.get("generated_at")
        else datetime.now(timezone.utc)
    )
    claim_obj = Claim(
        claim_id=row["claim_id"],
        source_module=row["source_module"],
        user_id=row["user_id"],
        loan_id=row["loan_id"],
        claim_text=row["claim_text"],
        supporting_figures=row.get("supporting_figures", {}),
        source_record_id=row["source_record_id"],
        generated_at=gen_at,
        verification_status=row.get("verification_status", "pending"),
    )

    # Step 3: Execute Module 4 Vernacular Verification Pipeline
    try:
        response = verify_vernacular_claim(
            claim=claim_obj,
            user_id=current_user.user_id,
            loan_id=loan_id,
            target_language=payload.target_language,
            use_cache_only=payload.use_cache_only,
        )
        return response
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Vernacular verification failed: {str(e)}",
        )
