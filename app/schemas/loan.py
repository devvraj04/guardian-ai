from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4
from pydantic import BaseModel, ConfigDict, Field


class LoanCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    loan_name: str = Field(..., min_length=2, max_length=100, description="Name or identifier of the loan offer")
    lender_name: str = Field(..., min_length=2, max_length=100, description="Financial institution or bank name")


class LoanResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    user_id: str
    loan_name: str
    lender_name: str
    status: str
    created_at: datetime


class LoanManualTermsCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    principal: float = Field(..., gt=0, description="Loan principal amount in INR")
    disclosed_rate: float = Field(..., gt=0, le=100, description="Annual interest rate disclosed in percentage")
    tenure_months: int = Field(..., gt=0, le=360, description="Loan tenure duration in months")
    fees: float = Field(default=0.0, ge=0, description="Total upfront fees, charges or processing fee in INR")


class LoanManualTermsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    loan_id: str
    principal: float
    disclosed_rate: float
    tenure_months: int
    fees: float
    entered_at: datetime
