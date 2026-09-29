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


def test_recompute_and_serviceability_pipeline():
    # 1. Create a Loan
    create_resp = client.post(
        "/api/v1/loans",
        json={"loan_name": "Deterministic Test Loan", "lender_name": "Standard Bank"},
    )
    assert create_resp.status_code == 201
    loan_id = create_resp.json()["id"]

    # 2. Enter Manual Terms: 100000, 12% p.a., 12 months, Rs 2000 fee
    terms_payload = {
        "principal": 100000.0,
        "disclosed_rate": 12.0,
        "tenure_months": 12,
        "fees": 2000.0,
    }
    client.post(f"/api/v1/loans/{loan_id}/terms", json=terms_payload)

    # 3. Test POST /loans/{id}/recompute
    recomp_resp = client.post(f"/api/v1/loans/{loan_id}/recompute")
    assert recomp_resp.status_code == 200
    recomp_data = recomp_resp.json()
    assert abs(recomp_data["monthly_emi"] - 8884.88) <= 0.10
    assert abs(recomp_data["recomputed_apr"] - 15.89) <= 0.05
    assert recomp_data["claim_id"] is not None

    # Verify claim exists in Supabase claims table
    claim_row = (
        supabase_admin.table("claims")
        .select("*")
        .eq("claim_id", recomp_data["claim_id"])
        .execute()
    )
    assert len(claim_row.data) == 1
    assert claim_row.data[0]["source_module"] == "recompute"
    assert claim_row.data[0]["verification_status"] == "pending"

    # 4. Test POST /loans/{id}/serviceability (Serviceable Scenario)
    serv_payload = {
        "monthly_income": 80000.0,
        "existing_emis": 10000.0,
        "monthly_expenses": 30000.0,
    }
    serv_resp = client.post(
        f"/api/v1/loans/{loan_id}/serviceability", json=serv_payload
    )
    assert serv_resp.status_code == 201
    serv_data = serv_resp.json()
    assert serv_data["verdict"] == "serviceable"
    assert abs(serv_data["dti_ratio"] - 0.2361) <= 0.005
    assert serv_data["claim_verification_status"] == "pending"
    assert "23.6%" in serv_data["claim_text_unverified"]

    # Verify claim row for serviceability
    serv_claim = (
        supabase_admin.table("claims")
        .select("*")
        .eq("claim_id", serv_data["claim_id"])
        .execute()
    )
    assert len(serv_claim.data) == 1
    assert serv_claim.data[0]["source_module"] == "serviceability"
    assert serv_claim.data[0]["verification_status"] == "pending"

    # 5. Test Marginal Scenario
    marginal_payload = {
        "monthly_income": 50000.0,
        "existing_emis": 14000.0,
        "monthly_expenses": 20000.0,
    }
    marginal_resp = client.post(
        f"/api/v1/loans/{loan_id}/serviceability", json=marginal_payload
    )
    assert marginal_resp.status_code == 201
    assert marginal_resp.json()["verdict"] == "marginal"

    # 6. Test Not-Serviceable Scenario (Excessive DTI)
    unserv_payload = {
        "monthly_income": 30000.0,
        "existing_emis": 15000.0,
        "monthly_expenses": 10000.0,
    }
    unserv_resp = client.post(
        f"/api/v1/loans/{loan_id}/serviceability", json=unserv_payload
    )
    assert unserv_resp.status_code == 201
    assert unserv_resp.json()["verdict"] == "not-serviceable"
