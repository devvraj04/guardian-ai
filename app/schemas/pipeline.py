from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.consistency import ConsistencyCheckResponse
from app.schemas.serviceability import RecomputeResponse, ServiceabilityResponse
from app.schemas.verification import VerifiedClaimResponse
from app.schemas.vernacular import VernacularVerificationResponse


class PipelineStage(str, Enum):
    """Orchestration state machine stages (IMPLEMENTATION_PLAN.md line 187)."""

    IDLE = "idle"
    INGESTING = "ingesting"
    EXTRACTING = "extracting"
    CONSISTENCY_CHECKING = "consistency_checking"
    RECOMPUTING_SERVICEABILITY = "recomputing_serviceability"
    GENERATING_CLAIM = "generating_claim"
    RETRIEVING_REGULATORY = "retrieving_regulatory"
    VERIFYING = "verifying"
    TRANSLATING_VERNACULAR = "translating_vernacular"
    COMPLETED = "completed"
    FAILED = "failed"


class StageTiming(BaseModel):
    model_config = ConfigDict(extra="forbid")

    stage: PipelineStage
    duration_ms: float


class RunPipelineRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_language: Optional[str] = Field(
        None,
        description="Optional ISO 639-1 vernacular code (e.g. 'hi' for Hindi, 'mr' for Marathi)",
    )
    monthly_income: Optional[float] = Field(
        None, gt=0, description="Monthly income for serviceability assessment"
    )
    existing_obligations: Optional[float] = Field(
        None, ge=0, description="Existing EMI obligations for serviceability assessment"
    )


class LoanAnalysisPipelineResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    loan_id: str
    status: PipelineStage
    total_duration_ms: float
    timings: List[StageTiming]
    apr_result: Optional[RecomputeResponse] = None
    serviceability_result: Optional[ServiceabilityResponse] = None
    consistency_result: Optional[ConsistencyCheckResponse] = None
    verified_claims: List[VerifiedClaimResponse] = Field(default_factory=list)
    vernacular_translations: Optional[List[VernacularVerificationResponse]] = None
    extracted_kfs: Optional[dict] = Field(default=None, description="All structured fields extracted from the Key Fact Statement")
    summary: str
    is_fully_compliant: bool
    warnings: List[str] = Field(default_factory=list)
