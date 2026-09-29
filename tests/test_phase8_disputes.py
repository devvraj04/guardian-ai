"""
End-to-End API Integration Test for Phase 8 Grievance Classification & Redressal (Module 5).
"""

from fastapi.testclient import TestClient
from supabase import create_client

from app.core.config import settings
from app.deps.auth import AuthenticatedUser, get_current_user
from app.main import app

# Retrieve or create real test user from Supabase Auth
supabase_admin = create_client(
    settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY
)
users_list = supabase_admin.auth.admin.list_users()
test_user = next(
    (u for u in users_list if u.email == "test_borrower@guardian.local"), None
)

if test_user is None:
    test_user_res = supabase_admin.auth.admin.create_user(
        {
            "email": "test_borrower@guardian.local",
            "password": "TestPassword123!",
            "email_confirm": True,
        }
    )
    TEST_USER_ID = test_user_res.user.id
else:
    TEST_USER_ID = test_user.id


async def override_get_current_user():
    return AuthenticatedUser(
        user_id=TEST_USER_ID,
        email="test_borrower@guardian.local",
        role="authenticated",
    )


app.dependency_overrides[get_current_user] = override_get_current_user
client = TestClient(app)


def test_phase8_dispute_classification_and_tracking_pipeline():
    # 1. Create a Loan
    create_resp = client.post(
        "/api/v1/loans",
        json={
            "loan_name": "Grievance Test Loan",
            "lender_name": "QuickCash Finance",
        },
    )
    assert create_resp.status_code == 201
    loan_id = create_resp.json()["id"]

    try:
        # 2. Submit a User Dispute (Recovery Harassment)
        complaint_text = (
            "Recovery agents illegally accessed my phone contact list and are sending abusive "
            "and threatening messages to my coworkers and relatives."
        )
        post_resp = client.post(
            f"/api/v1/loans/{loan_id}/disputes",
            json={"free_text": complaint_text},
        )
        assert post_resp.status_code == 201
        dispute_data = post_resp.json()

        assert dispute_data["loan_id"] == loan_id
        assert dispute_data["user_id"] == TEST_USER_ID
        assert dispute_data["category"] == "recovery_harassment_and_privacy"
        assert dispute_data["status"] == "submitted"
        assert dispute_data["redressal_tat_days"] == 30
        assert "Clause 5.4" in dispute_data["rbi_clause_reference"]
        assert dispute_data["claim_id"] is not None
        dispute_id = dispute_data["id"]

        # 3. Verify Claim Emitted with source_module="grievance" (RULES.md §1.3, §4.7)
        claim_res = (
            supabase_admin.table("claims")
            .select("*")
            .eq("claim_id", dispute_data["claim_id"])
            .execute()
        )
        assert len(claim_res.data) == 1
        assert claim_res.data[0]["source_module"] == "grievance"

        # 4. List Disputes for Loan
        list_resp = client.get(f"/api/v1/loans/{loan_id}/disputes")
        assert list_resp.status_code == 200
        list_data = list_resp.json()
        assert list_data["total"] >= 1
        assert any(d["id"] == dispute_id for d in list_data["disputes"])

        # 5. Get Specific Dispute
        get_resp = client.get(f"/api/v1/loans/{loan_id}/disputes/{dispute_id}")
        assert get_resp.status_code == 200
        get_data = get_resp.json()
        assert get_data["id"] == dispute_id
        assert get_data["category"] == "recovery_harassment_and_privacy"
        assert get_data["status"] == "submitted"

        # 6. Submit Dispute with User Category Override
        override_text = "The lender charged an unexpected platform convenience fee of Rs 1,500 on my loan."
        override_resp = client.post(
            f"/api/v1/loans/{loan_id}/disputes",
            json={
                "free_text": override_text,
                "category_override": "excessive_charges_and_hidden_fees",
            },
        )
        assert override_resp.status_code == 201
        assert override_resp.json()["category"] == "excessive_charges_and_hidden_fees"

    finally:
        # Cleanup loan (cascades to disputes and claims)
        supabase_admin.table("loans").delete().eq("id", loan_id).execute()
