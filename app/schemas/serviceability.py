from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class RecomputeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    principal: float = Field(..., gt=0, description="Principal amount in INR")
    disclosed_rate: float = Field(
        ..., ge=0, le=100, description="Disclosed annual interest rate percentage"
    )
    tenure_months: int = Field(..., gt=0, le=360, description="Tenure in months")
    fees: float = Field(
        default=0.0, ge=0, description="Total upfront fees and charges in INR"
    )


class RecomputeResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    principal: float
    disclosed_rate: float
    tenure_months: int
    fees: float
    disbursed_amount: float
    monthly_emi: float
    total_payment: float
    total_interest: float
    recomputed_apr: float
    fee_impact_apr: float
    claim_id: Optional[str] = None


class ServiceabilityRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    monthly_income: float = Field(..., gt=0, description="Net monthly income in INR")
    existing_emis: float = Field(
        default=0.0, ge=0, description="Total current monthly EMI commitments in INR"
    )
    monthly_expenses: float = Field(
        default=0.0,
        ge=0,
        description="Estimated mandatory monthly living expenses in INR",
    )


class ServiceabilityResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    loan_id: str
    monthly_income: float
    existing_emis: float
    monthly_expenses: float
    new_emi: float
    total_emis: float
    dti_ratio: float
    disposable_income: float
    verdict: str
    is_heuristic: bool = True
    disclaimer: str = "Thresholds are lending-industry heuristics, not RBI-mandated rules (RULES.md §6.4)"
    claim_id: str
    claim_verification_status: str
    claim_text_unverified: str
    computed_at: datetime
