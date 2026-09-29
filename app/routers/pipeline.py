from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from supabase import Client, create_client

from app.core.config import settings
from app.deps.auth import AuthenticatedUser, get_current_user
from app.orchestration.pipeline import run_full_loan_pipeline
from app.schemas.pipeline import LoanAnalysisPipelineResponse, RunPipelineRequest

router = APIRouter(prefix="/loans/{loan_id}/pipeline", tags=["Pipeline Orchestration"])


def get_db_client() -> Client:
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)


@router.post(
    "/analyze",
    response_model=LoanAnalysisPipelineResponse,
    status_code=status.HTTP_200_OK,
)
async def analyze_loan_pipeline_endpoint(
    loan_id: str,
    payload: Optional[RunPipelineRequest] = None,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> LoanAnalysisPipelineResponse:
    """
    Triggers the complete GUARDIAN pipeline end-to-end (Phase 10):
    ingest → extract → consistency-check → recompute/serviceability →
    generate claim → retrieve → verify → (vernacular, if requested) → respond

    Guarantees:
    - Server-side JWT ownership verification (S-3).
    - Sub-5 second round trip on reference loan.
    - All claims routed through Sacred Verification Gate (RULES.md §1.1).
    """
    supabase = get_db_client()

    # Verify loan ownership server-side (Rule S-3)
    loan_res = supabase.table("loans").select("user_id").eq("id", loan_id).execute()
    if not loan_res.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Loan not found"
        )

    if loan_res.data[0]["user_id"] != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: you do not own this loan",
        )

    return run_full_loan_pipeline(
        loan_id=loan_id,
        user_id=current_user.user_id,
        request=payload,
        supabase_client=supabase,
    )
