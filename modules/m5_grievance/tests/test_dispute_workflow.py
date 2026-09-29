"""
Integration test for Dispute creation and tracking workflow.
"""

from supabase import create_client

from app.core.config import settings
from modules.m5_grievance.dispute_service import create_user_dispute, list_user_disputes

supabase_admin = create_client(
    settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY
)
users_list = supabase_admin.auth.admin.list_users()
test_user = next(
    (u for u in users_list if u.email == "test_borrower@guardian.local"), None
)

if test_user:
    TEST_USER_ID = test_user.id
else:
    test_user_res = supabase_admin.auth.admin.create_user(
        {
            "email": "test_borrower@guardian.local",
            "password": "TestPassword123!",  # pragma: allowlist secret
            "email_confirm": True,
        }
    )
    TEST_USER_ID = test_user_res.user.id


def test_dispute_creation_and_listing_workflow():
    # 1. Create a loan
    loan_record = (
        supabase_admin.table("loans")
        .insert(
            {
                "user_id": TEST_USER_ID,
                "loan_name": "Dispute Test Loan",
                "lender_name": "Axis Lenders",
                "status": "intake",
            }
        )
        .execute()
    )
    loan_id = loan_record.data[0]["id"]

    try:
        # 2. Submit a user grievance
        dispute_text = "The lender charged an undisclosed 8% processing fee and added illegal insurance charges."
        resp = create_user_dispute(
            loan_id=loan_id,
            user_id=TEST_USER_ID,
            free_text=dispute_text,
            supabase_client=supabase_admin,
        )

        assert resp.id is not None
        assert resp.loan_id == loan_id
        assert resp.user_id == TEST_USER_ID
        assert resp.category == "excessive_charges_and_hidden_fees"
        assert resp.status == "submitted"
        assert resp.redressal_tat_days == 30
        assert resp.claim_id is not None

        # 3. Verify dispute persisted in public.disputes
        db_dispute = (
            supabase_admin.table("disputes").select("*").eq("id", resp.id).execute()
        )
        assert len(db_dispute.data) == 1
        assert db_dispute.data[0]["status"] == "submitted"

        # 4. Verify tracking claim persisted in public.claims (RULES.md §1.3, §4.7)
        db_claim = (
            supabase_admin.table("claims")
            .select("*")
            .eq("claim_id", resp.claim_id)
            .execute()
        )
        assert len(db_claim.data) == 1
        assert db_claim.data[0]["source_module"] == "grievance"

        # 5. Verify listing disputes
        disputes_list = list_user_disputes(
            loan_id=loan_id,
            user_id=TEST_USER_ID,
            supabase_client=supabase_admin,
        )
        assert len(disputes_list) >= 1
        assert any(d.id == resp.id for d in disputes_list)

    finally:
        # Cleanup
        supabase_admin.table("loans").delete().eq("id", loan_id).execute()
