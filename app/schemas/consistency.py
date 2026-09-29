from typing import Any, List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field


class FieldComparison(BaseModel):
    """
    Comparison result for a single logical loan field across manual, T&C, and KFS sources.
    Strict Pydantic schema with extra='forbid' (S-6).
    """

    model_config = ConfigDict(extra="forbid")

    field_name: str = Field(
        ...,
        description="Logical field name (principal, disclosed_rate, tenure_months, fees, prepayment_clause)",
    )
    manual_value: Optional[Any] = Field(
        default=None, description="Value from manual entry"
    )
    tnc_value: Optional[Any] = Field(
        default=None, description="Value extracted from T&C document"
    )
    kfs_value: Optional[Any] = Field(
        default=None, description="Value extracted from KFS document"
    )
    match_status: Literal["match", "mismatch", "missing"] = Field(
        ..., description="Comparison status"
    )
    tolerance_applied: Optional[str] = Field(
        default=None,
        description="Tolerance rule applied for numeric or semantic comparison",
    )
    difference_notes: Optional[str] = Field(
        default=None, description="Human-readable explanation of discrepancy if any"
    )
    requires_human_review: bool = Field(
        default=False,
        description="Flag indicating human review is required (e.g. for prose contradiction)",
    )


class ConsistencyCheckResponse(BaseModel):
    """
    Complete response payload for loan consistency checking.
    Strict Pydantic schema with extra='forbid' (S-6).
    """

    model_config = ConfigDict(extra="forbid")

    loan_id: str
    overall_status: Literal["match", "mismatch", "missing"]
    mismatch_count: int = Field(..., ge=0)
    missing_count: int = Field(..., ge=0)
    match_count: int = Field(..., ge=0)
    checks: List[FieldComparison]
    claim_id: Optional[str] = Field(
        default=None,
        description="UUID of the generated unverified Claim in claims table",
    )
    summary_explanation: str = Field(..., description="Summary explanation of findings")
    requires_human_review: bool = Field(
        default=False,
        description="True if any clause or check requires manual confirmation",
    )
