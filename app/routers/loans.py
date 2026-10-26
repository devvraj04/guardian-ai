from datetime import datetime, timezone
from typing import List, Optional
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException, Response, status
from supabase import Client, create_client
from app.core.config import settings
from app.deps.auth import AuthenticatedUser, get_current_user, verify_user_ownership
from app.schemas.loan import (
    AuditReportPdfRequest,
    LoanCreate,
    LoanManualTermsCreate,
    LoanManualTermsResponse,
    LoanResponse,
)
from app.services.pdf_generator import generate_audit_verification_report_pdf

router = APIRouter(prefix="/loans", tags=["Loans"])


def get_db_client() -> Client:
    # Use service role key on server-side to enforce application-layer ownership checks
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)


@router.post("", response_model=LoanResponse, status_code=status.HTTP_201_CREATED)
async def create_loan(
    payload: LoanCreate,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> LoanResponse:
    """
    Creates a new loan record for the authenticated user.
    """
    supabase = get_db_client()
    loan_id = str(uuid4())

    loan_data = {
        "id": loan_id,
        "user_id": current_user.user_id,
        "loan_name": payload.loan_name,
        "lender_name": payload.lender_name,
        "status": "active",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    res = supabase.table("loans").insert(loan_data).execute()
    if not res.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to register loan offer in database",
        )

    # Append to audit_log (S-21)
    supabase.table("audit_log").insert(
        {
            "user_id": current_user.user_id,
            "action": "LOAN_CREATED",
            "entity_type": "loans",
            "entity_id": loan_id,
            "metadata": {
                "loan_name": payload.loan_name,
                "lender_name": payload.lender_name,
            },
        }
    ).execute()

    return LoanResponse(**res.data[0])


@router.get("", response_model=List[LoanResponse])
async def list_loans(
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> List[LoanResponse]:
    """
    Lists all loans belonging to the authenticated user.
    """
    supabase = get_db_client()
    res = (
        supabase.table("loans")
        .select("*")
        .eq("user_id", current_user.user_id)
        .order("created_at", desc=True)
        .execute()
    )
    return [LoanResponse(**item) for item in res.data]


@router.get("/{loan_id}", response_model=LoanResponse)
async def get_loan(
    loan_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> LoanResponse:
    supabase = get_db_client()
    res = supabase.table("loans").select("*").eq("id", loan_id).execute()
    if not res.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Loan not found"
        )

    loan = res.data[0]
    verify_user_ownership(loan["user_id"], current_user)
    return LoanResponse(**loan)


@router.post(
    "/{loan_id}/terms",
    response_model=LoanManualTermsResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_manual_terms(
    loan_id: str,
    payload: LoanManualTermsCreate,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> LoanManualTermsResponse:
    """
    Submits manual loan terms entered by the user (Module 0 / Phase 1).
    """
    supabase = get_db_client()

    # Validate loan exists and belongs to current user
    loan_res = supabase.table("loans").select("user_id").eq("id", loan_id).execute()
    if not loan_res.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Loan not found"
        )

    verify_user_ownership(loan_res.data[0]["user_id"], current_user)

    terms_data = {
        "id": str(uuid4()),
        "loan_id": loan_id,
        "principal": payload.principal,
        "disclosed_rate": payload.disclosed_rate,
        "tenure_months": payload.tenure_months,
        "fees": payload.fees,
        "entered_at": datetime.now(timezone.utc).isoformat(),
    }

    res = supabase.table("loan_manual_terms").insert(terms_data).execute()
    if not res.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to record manual terms in database",
        )

    # Append to audit_log (S-21)
    supabase.table("audit_log").insert(
        {
            "user_id": current_user.user_id,
            "action": "MANUAL_TERMS_ENTERED",
            "entity_type": "loan_manual_terms",
            "entity_id": terms_data["id"],
            "metadata": {"loan_id": loan_id},
        }
    ).execute()

    return LoanManualTermsResponse(**res.data[0])


@router.get("/{loan_id}/terms", response_model=Optional[LoanManualTermsResponse])
async def get_manual_terms(
    loan_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> Optional[LoanManualTermsResponse]:
    supabase = get_db_client()
    loan_res = supabase.table("loans").select("user_id").eq("id", loan_id).execute()
    if not loan_res.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Loan not found"
        )

    verify_user_ownership(loan_res.data[0]["user_id"], current_user)

    res = (
        supabase.table("loan_manual_terms")
        .select("*")
        .eq("loan_id", loan_id)
        .order("entered_at", desc=True)
        .limit(1)
        .execute()
    )
    if not res.data:
        return None
    return LoanManualTermsResponse(**res.data[0])


@router.post("/{loan_id}/report/pdf")
async def generate_loan_audit_pdf(
    loan_id: str,
    payload: Optional[AuditReportPdfRequest] = None,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> Response:
    """
    Generates a certified, multi-page Audit Verification Report PDF using PyMuPDF.
    Accepts full in-memory report details from the client or queries Supabase for saved loan state.
    """
    supabase = get_db_client()
    loan_name = payload.loan_name if payload else None
    lender_name = payload.lender_name if payload else None
    kfs_data = (payload.kfs if payload else None) or {}
    apr_data = (payload.apr if payload else None) or {}
    pipeline_res = (payload.pipeline_result if payload else None) or {}

    # Check if loan_id is in DB and verify ownership
    if loan_id and loan_id != "kfs":
        loan_record = supabase.table("loans").select("*").eq("id", loan_id).execute()
        if loan_record.data:
            verify_user_ownership(loan_record.data[0]["user_id"], current_user)
            if not loan_name:
                loan_name = loan_record.data[0].get("loan_name")
            if not lender_name:
                lender_name = loan_record.data[0].get("lender_name")

    loan_name = loan_name or "Retail Credit Facility"
    lender_name = (
        lender_name or kfs_data.get("bank_name") or "Regulated Lending Institution"
    )

    pdf_bytes = generate_audit_verification_report_pdf(
        loan_id=loan_id,
        loan_name=loan_name,
        lender_name=lender_name,
        kfs=kfs_data,
        apr=apr_data,
        pipeline_result=pipeline_res,
    )

    safe_name = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in loan_name)
    filename = f"GUARDIAN_Audit_Report_{safe_name}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Access-Control-Expose-Headers": "Content-Disposition",
        },
    )


@router.get("/{loan_id}/report/pdf")
async def get_loan_audit_pdf(
    loan_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> Response:
    """
    GET variant to generate or download the audit verification report PDF for a saved loan.
    """
    return await generate_loan_audit_pdf(
        loan_id=loan_id, payload=None, current_user=current_user
    )
