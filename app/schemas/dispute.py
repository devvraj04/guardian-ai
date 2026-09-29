"""
Pydantic schemas for Phase 8 Grievance Classification & Redressal (Module 5).
Governing Rules: RULES.md §1.3, §4.7; SPEC §3.4, §3.7; IMPLEMENTATION_PLAN Phase 8.
"""

from datetime import datetime
from typing import List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field

DisputeCategory = Literal[
    "excessive_charges_and_hidden_fees",
    "recovery_harassment_and_privacy",
    "unauthorized_disbursal_or_credit_limit",
    "transparency_and_kfs_violation",
    "repayment_and_noc_delay",
    "general_service_deficiency",
]

DisputeStatus = Literal[
    "submitted",
    "under_review",
    "escalated_to_ombudsman",
    "resolved",
]


class CreateDisputeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    free_text: str = Field(
        ...,
        min_length=10,
        max_length=5000,
        description="Borrower's free-text description of the dispute or grievance.",
    )
    category_override: Optional[DisputeCategory] = Field(
        default=None,
        description="Optional borrower-selected category override if automatic classification is disputed.",
    )


class DisputeClassificationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category: DisputeCategory = Field(
        ..., description="RBI-aligned grievance category."
    )
    category_label: str = Field(..., description="Human-readable category label.")
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Classifier prediction confidence score."
    )
    rbi_clause_reference: str = Field(
        ..., description="Relevant RBI Digital Lending clause citation."
    )
    redressal_tat_days: int = Field(
        default=30, description="Mandated resolution Turnaround Time (30 days per RBI)."
    )


class DisputeResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., description="UUID of the dispute record in public.disputes.")
    loan_id: str = Field(..., description="UUID of the associated loan.")
    user_id: str = Field(..., description="UUID of the borrower.")
    category: str = Field(..., description="Classified RBI grievance category.")
    category_label: str = Field(..., description="User-friendly category label.")
    confidence: float = Field(..., description="Classification confidence score.")
    free_text: str = Field(..., description="Original borrower grievance text.")
    status: DisputeStatus = Field(..., description="Current status of the dispute.")
    rbi_clause_reference: str = Field(
        ..., description="Applicable RBI guideline clause reference."
    )
    redressal_tat_days: int = Field(
        default=30, description="Turnaround time (TAT) limit in days."
    )
    claim_id: Optional[str] = Field(
        default=None,
        description="UUID of the tracking claim emitted for Module 3 verification.",
    )
    created_at: datetime = Field(
        ..., description="Timestamp when dispute was submitted."
    )


class DisputeListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    disputes: List[DisputeResponse] = Field(
        default_factory=list, description="List of borrower's disputes."
    )
    total: int = Field(..., description="Total number of disputes for this loan.")
