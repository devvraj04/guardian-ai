from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional
from uuid import uuid4
from pydantic import BaseModel, ConfigDict, Field


class VerificationResult(BaseModel):
    """
    VerificationResult schema (RULES.md §1.4, SPEC §3.4, IMPLEMENTATION_PLAN Phase 6).
    Enforced strictly with extra="forbid" (Rule S-6).
    Persisted to public.verification_results table in Supabase.
    """

    model_config = ConfigDict(
        extra="forbid",
        frozen=False,
    )

    id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique verification result UUID",
    )
    claim_id: str = Field(
        ...,
        description="UUID of the claim evaluated",
    )
    semantic_verdict: Literal["grounded", "flagged", "not_applicable"] = Field(
        ...,
        description="Verdict of NLI entailment against retrieved sources: grounded | flagged | not_applicable",
    )
    numeric_verdict: Literal["grounded", "flagged", "not_applicable"] = Field(
        ...,
        description="Verdict of deterministic arithmetic recompute: grounded | flagged | not_applicable",
    )
    final_verdict: Literal["grounded", "flagged"] = Field(
        ...,
        description="Composite verification verdict: grounded if both pass, flagged if either fails",
    )
    error_type: Optional[
        Literal[
            "semantic_mismatch", "numeric_mismatch", "both", "insufficient_evidence"
        ]
    ] = Field(
        default=None,
        description="Explicit failure categorization when flagged (RULES.md §1.4)",
    )
    semantic_score: Optional[float] = Field(
        default=None,
        description="Highest entailment probability score from RoBERTa-MNLI",
    )
    numeric_details: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Itemized numeric verification comparisons and tolerances",
    )
    retrieved_sources: Optional[List[Dict[str, Any]]] = Field(
        default_factory=list,
        description="Source passages from rbi_corpus and user_documents used for semantic grounding",
    )
    verified_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp when verification occurred",
    )


class VerifiedClaimResponse(BaseModel):
    """
    The user-facing response container for a claim processed through the Sacred Verification Gate (RULES.md §1.1).
    """

    model_config = ConfigDict(extra="forbid")

    claim_id: str
    source_module: str
    loan_id: str
    claim_text: str
    verification_status: Literal["grounded", "flagged"]
    is_safe_to_present: bool = Field(
        ...,
        description="True only if final_verdict is grounded. If flagged, unverified text is never presented as fact.",
    )
    warning_message: Optional[str] = None
    verification_result: VerificationResult
