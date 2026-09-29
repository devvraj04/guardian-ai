from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from supabase import Client, create_client

from app.core.config import settings
from app.deps.auth import AuthenticatedUser, get_current_user
from app.schemas.audit import AuditLogEntry, AuditLogResponse

router = APIRouter(prefix="/audit", tags=["Audit Trail"])


def get_db_client() -> Client:
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)


@router.get("", response_model=AuditLogResponse)
async def list_user_audit_logs(
    loan_id: Optional[str] = Query(None, description="Optional loan_id filter"),
    limit: int = Query(50, ge=1, le=100),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> AuditLogResponse:
    """
    Retrieve audit trail entries for the authenticated user (S-21, S-22).
    Read-only endpoint: users can only view their own audit logs.
    No UPDATE or DELETE endpoints are ever exposed.
    """
    supabase = get_db_client()

    query = (
        supabase.table("audit_log")
        .select("*")
        .eq("user_id", current_user.user_id)
        .order("timestamp", desc=True)
        .limit(limit)
    )

    if loan_id:
        # Verify loan ownership first (S-3)
        loan_res = (
            supabase.table("loans")
            .select("id")
            .eq("id", loan_id)
            .eq("user_id", current_user.user_id)
            .execute()
        )
        if not loan_res.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Loan not found or access denied.",
            )
        # Filter entries where entity_id matches loan_id or metadata contains loan_id
        query = query.eq("entity_id", loan_id)

    res = query.execute()
    entries = [
        AuditLogEntry(
            id=str(r["id"]),
            user_id=r.get("user_id"),
            action=r["action"],
            entity_type=r["entity_type"],
            entity_id=r.get("entity_id"),
            metadata=r.get("metadata") or {},
            timestamp=r["timestamp"],
        )
        for r in res.data
    ]

    return AuditLogResponse(entries=entries, total=len(entries))
