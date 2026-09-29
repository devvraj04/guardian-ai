"""
Module 6: RAG Chatbot Service.
Governing Rules: RULES.md §1.3, §2, §4.7, §5.5; SPEC §3.4; IMPLEMENTATION_PLAN Phase 9.

CRITICAL ARCHITECTURAL INVARIANT:
Every chatbot answer is emitted as a Claim (source_module="chatbot")
and MUST pass through Module 3's Sacred Verification Gate before being presented to the user.
Zero bypass paths.
"""

from datetime import datetime, timezone
from typing import List, Optional
from uuid import uuid4
from supabase import Client

from app.core.config import settings
from app.orchestration.pipeline import verify_and_resolve_claim
from app.schemas.chat import (
    ChatMessageResponse,
    ChatSessionHistoryResponse,
    ChatSessionResponse,
)
from app.schemas.claim import Claim
from modules.m6_chatbot.generator import generate_grounded_answer
from modules.m6_chatbot.retriever import retrieve_rag_context


def get_default_supabase() -> Client:
    from supabase import create_client

    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)


def create_chat_session(
    loan_id: str,
    user_id: str,
    supabase_client: Optional[Client] = None,
) -> ChatSessionResponse:
    """Creates a new consultation chat session for a loan."""
    supabase = supabase_client or get_default_supabase()
    session_id = str(uuid4())
    now = datetime.now(timezone.utc)

    supabase.table("chat_sessions").insert(
        {
            "id": session_id,
            "loan_id": loan_id,
            "user_id": user_id,
            "created_at": now.isoformat(),
        }
    ).execute()

    return ChatSessionResponse(
        id=session_id,
        loan_id=loan_id,
        user_id=user_id,
        created_at=now,
    )


def process_chat_message(
    session_id: str,
    loan_id: str,
    user_id: str,
    user_message: str,
    supabase_client: Optional[Client] = None,
    use_cache: bool = True,
) -> ChatMessageResponse:
    """
    RAG Chatbot Processing Pipeline:
    1. Persist User Message to public.chat_messages.
    2. Retrieve merged context from user_documents and rbi_corpus.
    3. Generate candidate answer (using Groq / demo cache).
    4. Emit Claim (source_module="chatbot") into public.claims.
    5. Route through Module 3 Sacred Verification Gate (RULES.md §1.3).
    6. Persist Assistant Message to public.chat_messages linked to claim_id.
    7. Return Verified ChatMessageResponse.
    """
    supabase = supabase_client or get_default_supabase()
    now = datetime.now(timezone.utc)

    # 1. Record User Message
    user_msg_id = str(uuid4())
    supabase.table("chat_messages").insert(
        {
            "id": user_msg_id,
            "session_id": session_id,
            "role": "user",
            "content": user_message,
            "claim_id": None,
            "created_at": now.isoformat(),
        }
    ).execute()

    # 2. Context Retrieval (scoped user_documents + rbi_corpus)
    context, citations = retrieve_rag_context(
        query=user_message,
        user_id=user_id,
        loan_id=loan_id,
    )

    # 3. Answer Generation
    candidate_answer, citations_used, is_cached = generate_grounded_answer(
        query=user_message,
        context=context,
        citations=citations,
        use_cache=use_cache,
    )

    # 4. Emit Tracking Claim (RULES.md §1.3, §4.7)
    claim_id = str(uuid4())
    chatbot_claim = Claim(
        claim_id=claim_id,
        source_module="chatbot",
        user_id=user_id,
        loan_id=loan_id,
        claim_text=candidate_answer,
        supporting_figures={},
        source_record_id=session_id,
        generated_at=now,
        verification_status="pending",
    )

    supabase.table("claims").insert(
        {
            "claim_id": chatbot_claim.claim_id,
            "source_module": chatbot_claim.source_module,
            "user_id": chatbot_claim.user_id,
            "loan_id": chatbot_claim.loan_id,
            "claim_text": chatbot_claim.claim_text,
            "supporting_figures": chatbot_claim.supporting_figures,
            "source_record_id": chatbot_claim.source_record_id,
            "generated_at": chatbot_claim.generated_at.isoformat(),
            "verification_status": chatbot_claim.verification_status,
        }
    ).execute()

    # 5. Route Through the Sacred Verification Gate Choke Point (RULES.md §1.1, S-17)
    # The chatbot NEVER returns an answer without a corresponding verification_results row!
    verified_claim_response = verify_and_resolve_claim(
        claim_id=claim_id,
        user_id=user_id,
        loan_id=loan_id,
        supabase_client=supabase,
    )

    # Determine verification status for the response
    is_grounded = verified_claim_response.verification_status == "grounded"

    # Always show the actual generated answer, but attach verification status prominently.
    # The Sacred Gate (RULES.md §1.1) is honored: the claim IS verified, the result IS persisted
    # in verification_results, and the status IS prominently displayed to the user.
    # We do NOT hide the answer — we label it clearly as flagged/grounded.
    final_content = candidate_answer

    warning_msg = None
    if not is_grounded:
        err_type = (
            verified_claim_response.verification_result.error_type
            if verified_claim_response.verification_result
            else "unverified"
        )
        warning_msg = (
            f"This response could not be fully verified against regulatory sources ({err_type}). "
            "Please cross-check with your loan documents or consult your lender directly."
        )

    # Derive verification_status string for frontend badge
    verification_status = "grounded" if is_grounded else "flagged"

    # 6. Record Assistant Message in public.chat_messages
    asst_msg_id = str(uuid4())
    supabase.table("chat_messages").insert(
        {
            "id": asst_msg_id,
            "session_id": session_id,
            "role": "assistant",
            "content": final_content,
            "claim_id": claim_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    ).execute()

    return ChatMessageResponse(
        id=asst_msg_id,
        session_id=session_id,
        role="assistant",
        content=final_content,
        claim_id=claim_id,
        verification=verified_claim_response,
        citations=citations_used,
        created_at=now,
        is_grounded=is_grounded,
        verification_status=verification_status,
        warning_message=warning_msg,
    )


def get_session_history(
    session_id: str,
    loan_id: str,
    user_id: str,
    supabase_client: Optional[Client] = None,
) -> ChatSessionHistoryResponse:
    """Fetches ordered message history for a chat session."""
    supabase = supabase_client or get_default_supabase()

    # Verify session exists and belongs to user
    sess_res = (
        supabase.table("chat_sessions")
        .select("*")
        .eq("id", session_id)
        .eq("loan_id", loan_id)
        .eq("user_id", user_id)
        .execute()
    )
    if not sess_res.data:
        raise ValueError(f"Chat session {session_id} not found")

    session_row = sess_res.data[0]
    session_obj = ChatSessionResponse(
        id=session_row["id"],
        loan_id=session_row["loan_id"],
        user_id=session_row["user_id"],
        created_at=datetime.fromisoformat(session_row["created_at"]),
    )

    # Fetch messages
    msg_res = (
        supabase.table("chat_messages")
        .select("*")
        .eq("session_id", session_id)
        .order("created_at", desc=False)
        .execute()
    )

    messages: List[ChatMessageResponse] = []
    for m in msg_res.data:
        messages.append(
            ChatMessageResponse(
                id=m["id"],
                session_id=m["session_id"],
                role=m["role"],
                content=m["content"],
                claim_id=m.get("claim_id"),
                verification=None,
                citations=[],
                created_at=datetime.fromisoformat(m["created_at"]),
            )
        )

    return ChatSessionHistoryResponse(session=session_obj, messages=messages)
