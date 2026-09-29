"""
End-to-End API Integration Test for Phase 7 Vernacular Verification (Module 4).
"""

from uuid import uuid4
from fastapi.testclient import TestClient
from supabase import create_client

from app.core.config import settings
from app.deps.auth import AuthenticatedUser, get_current_user
from app.main import app

# Supabase Auth user setup
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


def test_phase7_vernacular_translation_and_verification_pipeline():
    # 1. Create a Loan
    create_resp = client.post(
        "/api/v1/loans",
        json={
            "loan_name": "Vernacular Test Loan",
            "lender_name": "Heritage Bank",
        },
    )
    assert create_resp.status_code == 201
    loan_id = create_resp.json()["id"]

    try:
        # 2. Insert a Claim into Supabase claims table
        claim_id = str(uuid4())
        claim_text = (
            "For a principal of ₹100,000 at disclosed rate 12.00% over 12 months with fees of ₹2,000, "
            "the true effective APR is 15.89% with a monthly EMI of ₹8,884.88."
        )

        supabase_admin.table("claims").insert(
            {
                "claim_id": claim_id,
                "source_module": "recompute",
                "user_id": TEST_USER_ID,
                "loan_id": loan_id,
                "claim_text": claim_text,
                "supporting_figures": {
                    "principal": 100000.0,
                    "disclosed_rate": 12.0,
                    "tenure_months": 12,
                    "fees": 2000.0,
                },
                "source_record_id": loan_id,
                "verification_status": "grounded",
            }
        ).execute()

        # 3. Request Hindi Translation & Verification
        hi_resp = client.post(
            f"/api/v1/loans/{loan_id}/claims/{claim_id}/translate",
            json={"target_language": "hi", "use_cache_only": False},
        )
        assert hi_resp.status_code == 200
        hi_data = hi_resp.json()

        assert hi_data["claim_id"] == claim_id
        assert hi_data["target_language"] == "hi"
        assert "₹100,000" in hi_data["translated_text"]
        assert hi_data["verification_verdict"] == "grounded"
        assert hi_data["metrics"]["numeric_preservation_rate"] >= 95.0
        assert hi_data["metrics"]["clause_drop_rate"] <= 5.0
        assert hi_data["metrics"]["semantic_drift_score"] >= 0.70

        # 4. Request Marathi Translation & Verification
        mr_resp = client.post(
            f"/api/v1/loans/{loan_id}/claims/{claim_id}/translate",
            json={"target_language": "mr", "use_cache_only": False},
        )
        assert mr_resp.status_code == 200
        mr_data = mr_resp.json()

        assert mr_data["claim_id"] == claim_id
        assert mr_data["target_language"] == "mr"
        assert mr_data["verification_verdict"] == "grounded"
        assert mr_data["metrics"]["numeric_preservation_rate"] >= 95.0
        assert mr_data["metrics"]["clause_drop_rate"] <= 5.0

    finally:
        # Cleanup
        supabase_admin.table("loans").delete().eq("id", loan_id).execute()
