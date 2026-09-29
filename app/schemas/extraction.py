from datetime import datetime
from typing import Any, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class FieldConfidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    principal: float = Field(default=1.0, ge=0.0, le=1.0)
    disclosed_rate: float = Field(default=1.0, ge=0.0, le=1.0)
    tenure_months: float = Field(default=1.0, ge=0.0, le=1.0)
    processing_fee: float = Field(default=1.0, ge=0.0, le=1.0)
    prepayment_clause: float = Field(default=1.0, ge=0.0, le=1.0)


class ExtractedTerms(BaseModel):
    """
    Strict schema for Groq LLM structured extraction output (S-6).
    """

    model_config = ConfigDict(extra="forbid")

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
