from datetime import datetime, timezone
from typing import Any, Dict, Literal
from uuid import uuid4
from pydantic import BaseModel, ConfigDict, Field

SourceModuleType = Literal[
    "recompute",
    "consistency",
    "serviceability",
    "chatbot",
    "grievance",
]

VerificationStatusType = Literal[
    "pending",
    "grounded",
    "flagged",
]


class Claim(BaseModel):
    """
    The canonical Claim schema (RULES.md §1.3, §4.7; SPEC §3.3).
    Strictly enforced as the single definition in the entire repository.
    Strict Pydantic v2 validation with extra="forbid" (S-6).
    """

    model_config = ConfigDict(
        extra="forbid",
        frozen=False,
    )

    claim_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique claim identifier UUID",
    )
    source_module: SourceModuleType = Field(
        ...,
        description="Evidentiary module producing the claim: recompute | consistency | serviceability | chatbot | grievance",
    )
    user_id: str = Field(
        ...,
        description="ID of the user who owns this loan and claim",
    )
    loan_id: str = Field(
        ...,
        description="ID of the loan this claim pertains to",
    )
    claim_text: str = Field(
        ...,
        description="Natural language statement produced by LLM or rule engine requiring verification",
    )
    supporting_figures: Dict[str, Any] = Field(
        default_factory=dict,
        description="Extracted or recomputed numeric figures associated with the claim",
    )
    source_record_id: str = Field(
        ...,
        description="ID of the source document, extracted field row, or manual terms record",
    )
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp when the claim was constructed",
    )
    verification_status: VerificationStatusType = Field(
        default="pending",
        description="Verification gate status: pending | grounded | flagged",
    )
