from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from supabase import Client, create_client

from app.core.config import settings
from app.deps.auth import AuthenticatedUser, get_current_user, verify_user_ownership
from app.schemas.chat import (
    ChatMessageRequest,
    ChatMessageResponse,
    ChatSessionHistoryResponse,
    ChatSessionResponse,
    CreateChatSessionRequest,
)
from modules.m6_chatbot.chat_service import (
    create_chat_session,
    get_session_history,
    process_chat_message,
)

router = APIRouter(prefix="/loans/{loan_id}/chat", tags=["RAG Chatbot"])


def get_db_client() -> Client:
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)


@router.post(
    "/sessions", response_model=ChatSessionResponse, status_code=status.HTTP_201_CREATED
)
async def create_session_endpoint(
    loan_id: str,
    payload: Optional[CreateChatSessionRequest] = None,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> ChatSessionResponse:
    """Creates a new consultation chat session for a loan."""
    supabase = get_db_client()

    # Verify loan ownership (Rule S-3)
    loan_res = supabase.table("loans").select("user_id").eq("id", loan_id).execute()
    if not loan_res.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Loan not found"
        )
    verify_user_ownership(loan_res.data[0]["user_id"], current_user)

    session = create_chat_session(
        loan_id=loan_id,
        user_id=current_user.user_id,
        supabase_client=supabase,
    )
    return session


@router.get(
    "/sessions",
    response_model=List[ChatSessionResponse],
    status_code=status.HTTP_200_OK,
)
async def list_sessions_endpoint(
    loan_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> List[ChatSessionResponse]:
    """Lists all chat sessions for a loan."""
    supabase = get_db_client()

    loan_res = supabase.table("loans").select("user_id").eq("id", loan_id).execute()
    if not loan_res.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Loan not found"
        )
    verify_user_ownership(loan_res.data[0]["user_id"], current_user)

    res = (
        supabase.table("chat_sessions")
        .select("*")
        .eq("loan_id", loan_id)
        .eq("user_id", current_user.user_id)
        .order("created_at", desc=True)
        .execute()
    )

    return [
        ChatSessionResponse(
            id=r["id"],
            loan_id=r["loan_id"],
            user_id=r["user_id"],
            created_at=r["created_at"],
        )
        for r in res.data
    ]


@router.post(
    "/sessions/{session_id}/messages",
    response_model=ChatMessageResponse,
    status_code=status.HTTP_200_OK,
)
async def post_message_endpoint(
    loan_id: str,
    session_id: str,
    payload: ChatMessageRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> ChatMessageResponse:
    """
    Processes a borrower's question: retrieves scoped context, generates an answer,
    routes the answer through the Sacred Verification Gate, and records conversation.
    """
    supabase = get_db_client()

    loan_res = supabase.table("loans").select("user_id").eq("id", loan_id).execute()
    if not loan_res.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Loan not found"
        )
    verify_user_ownership(loan_res.data[0]["user_id"], current_user)

    # Verify session
    sess_res = (
        supabase.table("chat_sessions")
        .select("*")
        .eq("id", session_id)
        .eq("loan_id", loan_id)
        .eq("user_id", current_user.user_id)
        .execute()
    )
    if not sess_res.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chat session {session_id} not found",
        )

    try:
        response = process_chat_message(
            session_id=session_id,
            loan_id=loan_id,
            user_id=current_user.user_id,
            user_message=payload.message,
            supabase_client=supabase,
            use_cache=True,
        )
        return response
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Chatbot failed to process message: {str(e)}",
        )


@router.get(
    "/sessions/{session_id}/messages",
    response_model=ChatSessionHistoryResponse,
    status_code=status.HTTP_200_OK,
)
async def get_history_endpoint(
    loan_id: str,
    session_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> ChatSessionHistoryResponse:
    """Retrieves full conversation history for a chat session."""
    supabase = get_db_client()

    loan_res = supabase.table("loans").select("user_id").eq("id", loan_id).execute()
    if not loan_res.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Loan not found"
        )
    verify_user_ownership(loan_res.data[0]["user_id"], current_user)

    try:
        history = get_session_history(
            session_id=session_id,
            loan_id=loan_id,
            user_id=current_user.user_id,
            supabase_client=supabase,
        )
        return history
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
