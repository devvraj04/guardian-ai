from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from supabase import Client, create_client

from app.core.config import settings
from app.deps.auth import AuthenticatedUser, get_current_user, verify_user_ownership
from app.schemas.dispute import (
    CreateDisputeRequest,
    DisputeListResponse,
    DisputeResponse,
)
from modules.m5_grievance.dataset import CATEGORY_METADATA
from modules.m5_grievance.dispute_service import create_user_dispute, list_user_disputes

router = APIRouter(prefix="/loans/{loan_id}/disputes", tags=["Disputes & Grievances"])


def get_db_client() -> Client:
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)


@router.post("", response_model=DisputeResponse, status_code=status.HTTP_201_CREATED)
async def submit_dispute_endpoint(
    loan_id: str,
    payload: CreateDisputeRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> DisputeResponse:
    """
    Submits a user-initiated loan grievance or dispute (RULES.md §1.3, SPEC §3.4).
    Automatically classifies into an RBI-aligned category and stores for trackable resolution.
    """
    supabase = get_db_client()

    # Step 1: Verify loan ownership (Rule S-3)
    loan_res = supabase.table("loans").select("user_id").eq("id", loan_id).execute()
    if not loan_res.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Loan not found"
        )
    verify_user_ownership(loan_res.data[0]["user_id"], current_user)

    # Step 2: Create Dispute via Module 5
    response = create_user_dispute(
        loan_id=loan_id,
        user_id=current_user.user_id,
        free_text=payload.free_text,
        category_override=payload.category_override,
        supabase_client=supabase,
    )
    return response


@router.get("", response_model=DisputeListResponse, status_code=status.HTTP_200_OK)
async def list_disputes_endpoint(
    loan_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> DisputeListResponse:
    """
    Lists all trackable disputes filed for the given loan.
    """
    supabase = get_db_client()

    loan_res = supabase.table("loans").select("user_id").eq("id", loan_id).execute()
    if not loan_res.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Loan not found"
        )
    verify_user_ownership(loan_res.data[0]["user_id"], current_user)

    disputes = list_user_disputes(
        loan_id=loan_id,
        user_id=current_user.user_id,
        supabase_client=supabase,
    )
    return DisputeListResponse(disputes=disputes, total=len(disputes))


@router.get(
    "/{dispute_id}", response_model=DisputeResponse, status_code=status.HTTP_200_OK
)
async def get_dispute_endpoint(
    loan_id: str,
    dispute_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> DisputeResponse:
    """
    Retrieves the details and trackable status of a specific dispute.
    """
    supabase = get_db_client()

    loan_res = supabase.table("loans").select("user_id").eq("id", loan_id).execute()
    if not loan_res.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Loan not found"
        )
    verify_user_ownership(loan_res.data[0]["user_id"], current_user)

    res = (
        supabase.table("disputes")
        .select("*")
        .eq("id", dispute_id)
        .eq("loan_id", loan_id)
        .eq("user_id", current_user.user_id)
        .execute()
    )
    if not res.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dispute {dispute_id} not found",
        )

    row = res.data[0]
    cat = row["category"]
    meta = CATEGORY_METADATA.get(
        cat,
        {
            "label": "Loan Dispute",
            "rbi_clause": "RBI Digital Lending Guidelines",
        },
    )

    return DisputeResponse(
        id=row["id"],
        loan_id=row["loan_id"],
        user_id=row["user_id"],
        category=cat,
        category_label=meta["label"],
        confidence=1.0,
        free_text=row["free_text"],
        status=row["status"],
        rbi_clause_reference=meta["rbi_clause"],
        redressal_tat_days=30,
        claim_id=None,
        created_at=datetime.fromisoformat(row["created_at"]),
    )
