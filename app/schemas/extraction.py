from datetime import datetime
from typing import Any, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class FieldConfidence(BaseModel):
    model_config = ConfigDict(extra="ignore")

    principal: float = Field(default=1.0, ge=0.0, le=1.0)
    disclosed_rate: float = Field(default=1.0, ge=0.0, le=1.0)
    tenure_months: float = Field(default=1.0, ge=0.0, le=1.0)
    processing_fee: float = Field(default=1.0, ge=0.0, le=1.0)
    prepayment_clause: float = Field(default=1.0, ge=0.0, le=1.0)
    monthly_emi: Optional[float] = Field(default=1.0, ge=0.0, le=1.0)
    apr: Optional[float] = Field(default=1.0, ge=0.0, le=1.0)


class ExtractedTerms(BaseModel):
    """
    Schema for structured extraction output (S-6).
    Accommodates standard RBI Key Fact Statements (KFS) including Bandhan Bank.
    """

    model_config = ConfigDict(extra="ignore")

    principal: Optional[float] = Field(
        default=None, description="Disclosed loan amount in INR"
    )
    disclosed_rate: Optional[float] = Field(
        default=None, description="Disclosed annual interest rate percentage"
    )
    tenure_months: Optional[int] = Field(
        default=None, description="Loan tenure in months"
    )
    processing_fee: Optional[float] = Field(
        default=0.0, description="Processing fees or upfront charges in INR"
    )
    prepayment_clause: Optional[str] = Field(
        default=None,
        description="Exact text or clause discussing prepayment/foreclosure charges",
    )
    monthly_emi: Optional[float] = Field(
        default=None, description="Equated Periodic Instalment (EPI/EMI) in INR"
    )
    apr: Optional[float] = Field(
        default=None, description="Annual Percentage Rate disclosed in percentage"
    )
    penal_charges: Optional[str] = Field(
        default=None, description="Disclosed late payment or penal charges"
    )
    bounce_charges: Optional[float] = Field(
        default=None, description="Disclosed cheque/NACH bounce charges in INR"
    )
    bank_name: Optional[str] = Field(
        default=None, description="Identified bank / lender name"
    )
    grievance_email: Optional[str] = Field(
        default=None, description="Nodal grievance redressal email"
    )
    grievance_phone: Optional[str] = Field(
        default=None, description="Grievance helpline or nodal phone"
    )
    loan_type: Optional[str] = Field(
        default=None, description="Category of loan (e.g. Housing, Personal, MSME, Vehicle)"
    )
    interest_type: Optional[str] = Field(
        default=None, description="Interest rate type: Fixed, Floating, or Hybrid"
    )
    benchmark_rate: Optional[float] = Field(
        default=None, description="Benchmark rate percentage if floating rate"
    )
    spread: Optional[float] = Field(
        default=None, description="Spread percentage over benchmark"
    )
    reset_periodicity: Optional[str] = Field(
        default=None, description="Interest rate reset frequency (e.g. 3 months, 1 year)"
    )
    net_disbursed_amount: Optional[float] = Field(
        default=None, description="Net amount disbursed to borrower in INR (Principal minus upfront fees)"
    )
    total_interest_amount: Optional[float] = Field(
        default=None, description="Total interest payable over the entire loan tenor in INR"
    )
    total_repayment_amount: Optional[float] = Field(
        default=None, description="Total amount to be paid by the borrower (Principal + Total Interest) in INR"
    )
    cooling_off_period: Optional[str] = Field(
        default=None, description="Cooling-off / look-up period clause for loan cancellation"
    )
    field_confidences: FieldConfidence = Field(
        default_factory=FieldConfidence,
        description="Confidence scores from 0.0 to 1.0 for each field",
    )


class ExtractedFieldItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    doc_id: str
    field_name: str
    extracted_value: Any
    confidence: float
    extraction_method: str
    needs_manual_confirmation: bool
    created_at: datetime


class DocumentUploadResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    doc_id: str
    loan_id: str
    doc_type: str
    storage_path: str
    version: int
    uploaded_at: datetime
    extraction_status: str
    extracted_fields: List[ExtractedFieldItem]
