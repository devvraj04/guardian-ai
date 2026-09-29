from uuid import uuid4
from fastapi.testclient import TestClient
from supabase import create_client

from app.core.config import settings
from app.deps.auth import AuthenticatedUser, get_current_user
from app.main import app

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


def test_phase6_dual_groundedness_verifier_end_to_end():
    """
    Phase 6 End-to-End Verification Pipeline Test.
    Tests claim verification through the Sacred Verification Gate HTTP API.
    """
    # 1. Create a Loan
    create_resp = client.post(
        "/api/v1/loans",
        json={"loan_name": "Phase 6 Verification Loan", "lender_name": "Truth Bank"},
    )
    assert create_resp.status_code == 201
    loan_id = create_resp.json()["id"]

    # 2. Enter Manual Terms: 100,000, 12% p.a., 12 months, Rs 2000 fee
    terms_payload = {
        "principal": 100000.0,
        "disclosed_rate": 12.0,
        "tenure_months": 12,
        "fees": 2000.0,
    }
    client.post(f"/api/v1/loans/{loan_id}/terms", json=terms_payload)

    # 3. Generate a Recompute Claim
    recomp_resp = client.post(f"/api/v1/loans/{loan_id}/recompute")
    assert recomp_resp.status_code == 200
    recomp_claim_id = recomp_resp.json()["claim_id"]

    # 4. Verify Grounded Claim via Verification Gate Endpoint
    verify_resp = client.post(
        f"/api/v1/loans/{loan_id}/claims/{recomp_claim_id}/verify"
    )
    assert verify_resp.status_code == 200
    data = verify_resp.json()

    assert data["claim_id"] == recomp_claim_id
    assert data["verification_status"] == "grounded"
    assert data["is_safe_to_present"] is True
    assert data["warning_message"] is None
    assert data["verification_result"]["final_verdict"] == "grounded"
    assert data["verification_result"]["numeric_verdict"] == "grounded"

    # Verify database persistence in verification_results
    v_rows = (
        supabase_admin.table("verification_results")
        .select("*")
        .eq("claim_id", recomp_claim_id)
        .execute()
    )
    assert len(v_rows.data) >= 1
    assert v_rows.data[0]["final_verdict"] == "grounded"

    # Verify claim status updated in claims table
    c_row = (
        supabase_admin.table("claims")
        .select("*")
        .eq("claim_id", recomp_claim_id)
        .execute()
    )
    assert c_row.data[0]["verification_status"] == "grounded"

    # Verify audit_log entry (S-21)
    audit_rows = (
        supabase_admin.table("audit_log")
        .select("*")
        .eq("entity_id", data["verification_result"]["id"])
        .eq("action", "CLAIM_VERIFIED")
        .execute()
    )
    assert len(audit_rows.data) >= 1

    # 5. Inject an Adversarial / Flagged Claim
    fake_claim_id = str(uuid4())
    supabase_admin.table("claims").insert(
        {
            "claim_id": fake_claim_id,
            "source_module": "chatbot",
            "user_id": TEST_USER_ID,
            "loan_id": loan_id,
            "claim_text": "Borrowers with floating-rate loans are subject to mandatory 5% prepayment foreclosure charges.",
            "supporting_figures": {},
            "source_record_id": loan_id,
            "verification_status": "pending",
        }
    ).execute()

    flagged_resp = client.post(f"/api/v1/loans/{loan_id}/claims/{fake_claim_id}/verify")
    assert flagged_resp.status_code == 200
    flagged_data = flagged_resp.json()

    assert flagged_data["verification_status"] == "flagged"
    assert flagged_data["is_safe_to_present"] is False
    assert flagged_data["warning_message"] is not None
    assert "failed dual groundedness verification" in flagged_data["warning_message"]
    assert flagged_data["verification_result"]["semantic_verdict"] == "flagged"
