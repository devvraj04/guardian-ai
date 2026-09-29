"""
End-to-End API Integration Test for Phase 9 RAG Chatbot (Module 6).
"""

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


def test_phase9_rag_chatbot_pipeline_and_sacred_gate():
    # 1. Create a Loan
    create_resp = client.post(
        "/api/v1/loans",
        json={
            "loan_name": "RAG Chatbot Test Loan",
            "lender_name": "Canara Digital Bank",
        },
    )
    assert create_resp.status_code == 201
    loan_id = create_resp.json()["id"]

    try:
        # 2. Create Chat Session
        session_resp = client.post(f"/api/v1/loans/{loan_id}/chat/sessions")
        assert session_resp.status_code == 201
        session_data = session_resp.json()
        session_id = session_data["id"]

        # 3. Post User Query
        user_query = "Can the lender charge me a prepayment penalty if I decide to repay my floating rate loan early?"
        msg_resp = client.post(
            f"/api/v1/loans/{loan_id}/chat/sessions/{session_id}/messages",
            json={"message": user_query},
        )
        assert msg_resp.status_code == 200
        msg_data = msg_resp.json()

        assert msg_data["role"] == "assistant"
        assert msg_data["session_id"] == session_id
        assert msg_data["claim_id"] is not None
        assert "prepayment penalties are prohibited" in msg_data["content"].lower()

        # Invariant: Claim was emitted with source_module="chatbot" (RULES.md §1.3, §4.7)
        claim_res = (
            supabase_admin.table("claims")
            .select("*")
            .eq("claim_id", msg_data["claim_id"])
            .execute()
        )
        assert len(claim_res.data) == 1
        assert claim_res.data[0]["source_module"] == "chatbot"

        # Invariant: Chatbot answer MUST have a corresponding row in verification_results (S-17)
        verif_res = (
            supabase_admin.table("verification_results")
            .select("*")
            .eq("claim_id", msg_data["claim_id"])
            .execute()
        )
        assert len(verif_res.data) == 1
        assert verif_res.data[0]["final_verdict"] == "grounded"

        # Invariant: Citations are returned
        assert len(msg_data["citations"]) >= 1
        assert any(c["source"] == "rbi_corpus" for c in msg_data["citations"])

        # 4. Retrieve History
        hist_resp = client.get(
            f"/api/v1/loans/{loan_id}/chat/sessions/{session_id}/messages"
        )
        assert hist_resp.status_code == 200
        hist_data = hist_resp.json()
        assert len(hist_data["messages"]) == 2
        assert hist_data["messages"][0]["role"] == "user"
        assert hist_data["messages"][1]["role"] == "assistant"

    finally:
        # Cleanup
        supabase_admin.table("loans").delete().eq("id", loan_id).execute()
