from fastapi import APIRouter, Depends, HTTPException, status
from supabase import Client, create_client

from app.core.config import settings
from app.deps.auth import AuthenticatedUser, get_current_user, verify_user_ownership
from app.orchestration.pipeline import verify_and_resolve_claim
from app.schemas.verification import VerifiedClaimResponse

router = APIRouter(prefix="/loans/{loan_id}/claims", tags=["Verification Gate"])


def get_db_client() -> Client:
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)


@router.post(
    "/{claim_id}/verify",
    response_model=VerifiedClaimResponse,
    status_code=status.HTTP_200_OK,
)
async def verify_claim_endpoint(
    loan_id: str,
    claim_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> VerifiedClaimResponse:
    """
    Executes Module 3 Dual Verification for a claim through the Sacred Verification Gate (RULES.md §1).
    Returns VerifiedClaimResponse indicating whether the claim is grounded or flagged.
    """
    supabase = get_db_client()

    # Step 1: Verify loan ownership (Rule S-3)
    loan_res = supabase.table("loans").select("user_id").eq("id", loan_id).execute()
    if not loan_res.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Loan not found"
        )
    verify_user_ownership(loan_res.data[0]["user_id"], current_user)

    # Step 2: Route through Sacred Verification Choke Point (RULES.md §1.1)
    response = verify_and_resolve_claim(
        claim_id=claim_id,
        user_id=current_user.user_id,
        loan_id=loan_id,
        supabase_client=supabase,
    )
    return response


@router.get(
    "/{claim_id}/verification",
    response_model=VerifiedClaimResponse,
    status_code=status.HTTP_200_OK,
)
async def get_claim_verification(
    loan_id: str,
    claim_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> VerifiedClaimResponse:
    """
    Retrieves the verification status of a claim through the Sacred Verification Gate.
    """
    supabase = get_db_client()

    loan_res = supabase.table("loans").select("user_id").eq("id", loan_id).execute()
    if not loan_res.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Loan not found"
        )
    verify_user_ownership(loan_res.data[0]["user_id"], current_user)

    return verify_and_resolve_claim(
        claim_id=claim_id,
        user_id=current_user.user_id,
        loan_id=loan_id,
        supabase_client=supabase,
    )
