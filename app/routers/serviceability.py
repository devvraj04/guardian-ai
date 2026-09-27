from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException, status
from supabase import Client, create_client
from app.core.config import settings
from app.deps.auth import AuthenticatedUser, get_current_user, verify_user_ownership
from app.schemas.claim import Claim
from app.schemas.serviceability import ServiceabilityRequest, ServiceabilityResponse
from modules.m1_recompute.apr_recompute import calculate_reducing_balance_emi
from modules.m1b_serviceability.serviceability import (
    assess_serviceability,
    generate_serviceability_claim_text,
)

router = APIRouter(prefix="/loans/{loan_id}/serviceability", tags=["Serviceability"])


def get_db_client() -> Client:
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)


@router.post("", response_model=ServiceabilityResponse, status_code=status.HTTP_201_CREATED)
async def evaluate_serviceability(
    loan_id: str,
    payload: ServiceabilityRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> ServiceabilityResponse:
    """
    Evaluates debt-to-income affordability (Module 1b).
    Enforces RULES.md §1.7 (imports Module 1 EMI function), §1.8 (emits unverified Claim),
    and §6.4 (explicit heuristic labeling).
    """
    supabase = get_db_client()

    # Step 1: Verify loan ownership (S-3)
    loan_res = supabase.table("loans").select("user_id").eq("id", loan_id).execute()
    if not loan_res.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Loan not found")

    verify_user_ownership(loan_res.data[0]["user_id"], current_user)

    # Step 2: Retrieve loan terms to compute new EMI via Module 1
    terms_res = (
        supabase.table("loan_manual_terms")
        .select("*")
        .eq("loan_id", loan_id)
        .order("entered_at", desc=True)
        .limit(1)
        .execute()
    )
    if not terms_res.data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot assess serviceability: please enter loan terms first (/terms).",
        )

    t = terms_res.data[0]
    principal = float(t["principal"])
    rate = float(t["disclosed_rate"])
    tenure = int(t["tenure_months"])

    # Single-source EMI computation (RULES.md §1.7)
    new_emi = calculate_reducing_balance_emi(principal, rate, tenure)

    # Step 3: Record income and expense inputs
    input_id = str(uuid4())
    supabase.table("income_expense_inputs").insert({
        "id": input_id,
        "loan_id": loan_id,
        "monthly_income": payload.monthly_income,
        "existing_emis": payload.existing_emis,
        "monthly_expenses": payload.monthly_expenses,
        "entered_at": datetime.now(timezone.utc).isoformat(),
    }).execute()

    # Step 4: Run deterministic serviceability assessment (RULES.md §1.7)
    serv_result = assess_serviceability(
        monthly_income=payload.monthly_income,
        existing_emis=payload.existing_emis,
        monthly_expenses=payload.monthly_expenses,
        new_emi=new_emi,
    )

    # Step 5: Store serviceability result in database
    result_id = str(uuid4())
    supabase.table("serviceability_results").insert({
        "id": result_id,
        "loan_id": loan_id,
        "dti_ratio": serv_result.dti_ratio,
        "disposable_income": serv_result.disposable_income,
        "verdict": serv_result.verdict,
        "computed_at": datetime.now(timezone.utc).isoformat(),
    }).execute()

    # Step 6: Emit natural language Claim (RULES.md §1.8: must pass Module 3 before presentation)
    claim_id = str(uuid4())
    claim_text = generate_serviceability_claim_text(serv_result)

    claim = Claim(
        claim_id=claim_id,
        source_module="serviceability",
        user_id=current_user.user_id,
        loan_id=loan_id,
        claim_text=claim_text,
        supporting_figures={
            "monthly_income": serv_result.monthly_income,
            "existing_emis": serv_result.existing_emis,
            "monthly_expenses": serv_result.monthly_expenses,
            "new_emi": serv_result.new_emi,
            "total_emis": serv_result.total_emis,
            "dti_ratio": serv_result.dti_ratio,
            "disposable_income": serv_result.disposable_income,
            "verdict": serv_result.verdict,
        },
        source_record_id=result_id,
        generated_at=datetime.now(timezone.utc),
        verification_status="pending",
    )

    supabase.table("claims").insert({
        "claim_id": claim.claim_id,
        "source_module": claim.source_module,
        "user_id": claim.user_id,
        "loan_id": claim.loan_id,
        "claim_text": claim.claim_text,
        "supporting_figures": claim.supporting_figures,
        "source_record_id": claim.source_record_id,
        "generated_at": claim.generated_at.isoformat(),
        "verification_status": claim.verification_status,
    }).execute()

    # Step 7: Log action to audit_log (S-21)
    supabase.table("audit_log").insert({
        "user_id": current_user.user_id,
        "action": "SERVICEABILITY_ASSESSED",
        "entity_type": "serviceability_results",
        "entity_id": result_id,
        "metadata": {
            "loan_id": loan_id,
            "verdict": serv_result.verdict,
            "dti_ratio": serv_result.dti_ratio,
        },
    }).execute()

    return ServiceabilityResponse(
        loan_id=loan_id,
        monthly_income=serv_result.monthly_income,
        existing_emis=serv_result.existing_emis,
        monthly_expenses=serv_result.monthly_expenses,
        new_emi=serv_result.new_emi,
        total_emis=serv_result.total_emis,
        dti_ratio=serv_result.dti_ratio,
        disposable_income=serv_result.disposable_income,
        verdict=serv_result.verdict,
        is_heuristic=True,
        claim_id=claim_id,
        claim_verification_status="pending",
        claim_text_unverified=claim_text,
        computed_at=datetime.now(timezone.utc),
    )


@router.get("", response_model=Optional[dict])
async def get_latest_serviceability(
    loan_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> Optional[dict]:
    supabase = get_db_client()
    loan_res = supabase.table("loans").select("user_id").eq("id", loan_id).execute()
    if not loan_res.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Loan not found")

    verify_user_ownership(loan_res.data[0]["user_id"], current_user)

    res = (
        supabase.table("serviceability_results")
        .select("*")
        .eq("loan_id", loan_id)
        .order("computed_at", desc=True)
        .limit(1)
        .execute()
    )
    if not res.data:
        return None
    return res.data[0]
