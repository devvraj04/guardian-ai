"""
Integration test for Chat session and message processing workflow.
"""

from supabase import create_client

from app.core.config import settings
from modules.m6_chatbot.chat_service import (
    create_chat_session,
    get_session_history,
    process_chat_message,
)

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


def test_chat_session_and_message_processing():
    # 1. Create a loan
    loan_record = (
        supabase_admin.table("loans")
        .insert(
            {
                "user_id": TEST_USER_ID,
                "loan_name": "Chat Consultation Loan",
                "lender_name": "Federal Bank",
                "status": "intake",
            }
        )
        .execute()
    )
    loan_id = loan_record.data[0]["id"]

    try:
        # 2. Create Chat Session
        session = create_chat_session(
            loan_id=loan_id,
            user_id=TEST_USER_ID,
            supabase_client=supabase_admin,
        )
        assert session.id is not None
        assert session.loan_id == loan_id
        assert session.user_id == TEST_USER_ID

        # 3. Process User Question (Prepayment penalty query)
        user_query = "Can the lender charge me a prepayment penalty if I decide to repay my floating rate loan early?"
        msg_resp = process_chat_message(
            session_id=session.id,
            loan_id=loan_id,
            user_id=TEST_USER_ID,
            user_message=user_query,
            supabase_client=supabase_admin,
            use_cache=True,
        )

        assert msg_resp.role == "assistant"
        assert msg_resp.session_id == session.id
        assert msg_resp.claim_id is not None
        assert "prepayment penalties are prohibited" in msg_resp.content.lower()

        # Invariant: Claim was emitted and verified
        assert msg_resp.verification is not None
        assert msg_resp.verification.claim_id == msg_resp.claim_id
        assert msg_resp.verification.verification_status == "grounded"

        # Invariant: A row in verification_results exists for this chatbot claim
        verif_row = (
            supabase_admin.table("verification_results")
            .select("*")
            .eq("claim_id", msg_resp.claim_id)
            .execute()
        )
        assert len(verif_row.data) == 1

        # 4. Get Session History
        history = get_session_history(
            session_id=session.id,
            loan_id=loan_id,
            user_id=TEST_USER_ID,
            supabase_client=supabase_admin,
        )
        assert len(history.messages) == 2  # 1 user + 1 assistant
        assert history.messages[0].role == "user"
        assert history.messages[1].role == "assistant"

    finally:
        # Cleanup (cascades to chat_sessions, chat_messages, claims, verification_results)
        supabase_admin.table("loans").delete().eq("id", loan_id).execute()
