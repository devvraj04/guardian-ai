"""
Dispute and Grievance Management Service for Module 5.
Governing Rules: RULES.md §1.3, §4.7; SPEC §3.4; IMPLEMENTATION_PLAN Phase 8.

Ensures disputes are strictly user-initiated, recorded in public.disputes,
emits a tracking Claim with source_module="grievance", and logs to audit_log.
"""

from datetime import datetime, timezone
from typing import List, Optional
from uuid import uuid4
from supabase import Client

from app.core.config import settings
from app.core.logging import logger
from app.schemas.claim import Claim
from app.schemas.dispute import (
    DisputeCategory,
    DisputeResponse,
)
from modules.m5_grievance.classifier import grievance_classifier
from modules.m5_grievance.dataset import CATEGORY_METADATA


def get_default_supabase() -> Client:
    from supabase import create_client

    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)


def create_user_dispute(
    loan_id: str,
    user_id: str,
    free_text: str,
    category_override: Optional[DisputeCategory] = None,
    supabase_client: Optional[Client] = None,
) -> DisputeResponse:
    """
    Handles user-initiated grievance submission.
    1. Classifies complaint text using GrievanceClassifier.
    2. Inserts dispute into public.disputes.
    3. Emits tracking Claim (source_module="grievance").
    4. Logs to public.audit_log.
    """
    supabase = supabase_client or get_default_supabase()

    # Step 1: Run Classification
    classification = grievance_classifier.classify(free_text)
    final_category: DisputeCategory = category_override or classification.category
    cat_meta = CATEGORY_METADATA.get(
        final_category,
        {
            "label": classification.category_label,
            "rbi_clause": classification.rbi_clause_reference,
        },
    )

    dispute_id = str(uuid4())
    claim_id = str(uuid4())
    now = datetime.now(timezone.utc)

    # Step 2: Insert into public.disputes table
    supabase.table("disputes").insert(
        {
            "id": dispute_id,
            "loan_id": loan_id,
            "user_id": user_id,
            "category": final_category,
            "free_text": free_text,
            "status": "submitted",
            "created_at": now.isoformat(),
        }
    ).execute()

    # Step 3: Emit tracking Claim conforming to shared Claim schema (RULES.md §4.7)
    claim = Claim(
        claim_id=claim_id,
        source_module="grievance",
        user_id=user_id,
        loan_id=loan_id,
        claim_text=f"Dispute [{cat_meta['label']}]: {free_text}",
        supporting_figures={},
        source_record_id=dispute_id,
        generated_at=now,
        verification_status="pending",
    )

    try:
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
    except Exception as e:
        logger.error(f"Failed to record tracking claim for dispute {dispute_id}: {e}")

    # Step 4: Record in Audit Log (Rule S-21)
    try:
        supabase.table("audit_log").insert(
            {
                "user_id": user_id,
                "action": "DISPUTE_SUBMITTED",
                "entity_type": "disputes",
                "entity_id": dispute_id,
                "metadata": {
                    "category": final_category,
                    "confidence": classification.confidence,
                    "claim_id": claim_id,
                    "tat_days": 30,
                },
            }
        ).execute()
    except Exception as e:
        logger.error(f"Failed to log dispute submission to audit_log: {e}")

    return DisputeResponse(
        id=dispute_id,
        loan_id=loan_id,
        user_id=user_id,
        category=final_category,
        category_label=cat_meta["label"],
        confidence=classification.confidence,
        free_text=free_text,
        status="submitted",
        rbi_clause_reference=cat_meta["rbi_clause"],
        redressal_tat_days=30,
        claim_id=claim_id,
        created_at=now,
    )


def list_user_disputes(
    loan_id: str,
    user_id: str,
    supabase_client: Optional[Client] = None,
) -> List[DisputeResponse]:
    """Retrieves all disputes filed for a loan by the authenticated user."""
    supabase = supabase_client or get_default_supabase()

    res = (
        supabase.table("disputes")
        .select("*")
        .eq("loan_id", loan_id)
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .execute()
    )

    disputes: List[DisputeResponse] = []
    for row in res.data:
        cat = row["category"]
        meta = CATEGORY_METADATA.get(
            cat,
            {
                "label": "Loan Dispute",
                "rbi_clause": "RBI Digital Lending Directions",
            },
        )
        disputes.append(
            DisputeResponse(
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
        )
    return disputes
