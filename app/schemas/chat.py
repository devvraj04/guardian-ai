"""
Pydantic schemas for Phase 9 RAG Chatbot (Module 6).
Governing Rules: RULES.md §1.3, §2, §4.7; SPEC §3.4; IMPLEMENTATION_PLAN Phase 9.
"""

from datetime import datetime
from typing import List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.verification import VerifiedClaimResponse


class CreateChatSessionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_name: Optional[str] = Field(
        default=None,
        description="Optional friendly name for the loan consultation session.",
    )


class ChatSessionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., description="UUID of the chat session.")
    loan_id: str = Field(..., description="UUID of the loan.")
    user_id: str = Field(..., description="UUID of the borrower.")
    created_at: datetime = Field(..., description="Session creation timestamp.")


class ChatMessageRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str = Field(
        ...,
        min_length=2,
        max_length=2000,
        description="Borrower's question about their loan terms, fees, or RBI rights.",
    )


class RetrievedContextCitation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: Literal["user_documents", "rbi_corpus"] = Field(
        ..., description="Corpus source."
    )
    citation_id: str = Field(
        ..., description="Clause ID, section ID, or document type."
    )
    text: str = Field(..., description="Passage excerpt text.")


class ChatMessageResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., description="UUID of the message record.")
    session_id: str = Field(..., description="UUID of the chat session.")
    role: Literal["user", "assistant", "system"] = Field(
        ..., description="Sender role."
    )
    content: str = Field(..., description="Message text content.")
    claim_id: Optional[str] = Field(
        default=None, description="UUID of tracking claim passed through verifier."
    )
    verification: Optional[VerifiedClaimResponse] = Field(
        default=None,
        description="Module 3 Sacred Gate verification result for assistant answer.",
    )
    citations: List[RetrievedContextCitation] = Field(
        default_factory=list,
        description="Source passages used for RAG grounding.",
    )
    is_grounded: Optional[bool] = Field(
        default=None,
        description="Whether the answer passed the dual groundedness verification gate.",
    )
    verification_status: Optional[str] = Field(
        default=None,
        description="Verification status: 'grounded' or 'flagged'.",
    )
    warning_message: Optional[str] = Field(
        default=None,
        description="User-facing warning if the answer was flagged by the verification gate.",
    )
    created_at: datetime = Field(..., description="Message creation timestamp.")


class ChatSessionHistoryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session: ChatSessionResponse = Field(..., description="Session metadata.")
    messages: List[ChatMessageResponse] = Field(
        default_factory=list, description="Ordered conversation history."
    )
