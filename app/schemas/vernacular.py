"""
Schemas for Phase 7 Vernacular Translation and Verification (Module 4).
Governing Rules: RULES.md §1.6; SPEC §3.4; IMPLEMENTATION_PLAN Phase 7.
"""

from typing import List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.verification import VerificationResult

VernacularLanguage = Literal["hi", "mr"]


class VernacularTranslationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_language: VernacularLanguage = Field(
        ...,
        description="Target vernacular language code: 'hi' (Hindi) or 'mr' (Marathi).",
    )
    use_cache_only: bool = Field(
        default=False,
        description="If True, only use pre-computed cached translations.",
    )


class VernacularMetricReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    numeric_preservation_rate: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Percentage of financial figures preserved accurately across translation (0.0 - 100.0%).",
    )
    semantic_drift_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="RoBERTa-MNLI entailment score of back-translated text against original claim (1.0 = zero drift).",
    )
    clause_drop_rate: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Percentage of clauses dropped or omitted during translation (0.0% is optimal).",
    )
    preserved_figures_count: int = Field(
        ..., description="Number of numeric figures preserved."
    )
    total_figures_count: int = Field(
        ..., description="Total numeric figures detected in original claim."
    )
    dropped_clauses: List[str] = Field(
        default_factory=list, description="Clauses missing in back-translation."
    )


class VernacularVerificationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    claim_id: str = Field(..., description="UUID of the verified claim.")
    original_text: str = Field(..., description="Original English claim text.")
    target_language: VernacularLanguage = Field(
        ..., description="Vernacular language code ('hi' or 'mr')."
    )
    translated_text: str = Field(
        ..., description="Forward-translated claim in target vernacular language."
    )
    back_translated_text: str = Field(
        ..., description="Back-translated English text for verification."
    )
    metrics: VernacularMetricReport = Field(
        ..., description="Cross-lingual evaluation metrics."
    )
    verification_verdict: Literal["grounded", "flagged"] = Field(
        ...,
        description="Module 3 verdict on the back-translated claim.",
    )
    verification_details: Optional[VerificationResult] = Field(
        default=None,
        description="Detailed Module 3 verification result for the back-translation.",
    )
    is_cached: bool = Field(
        ..., description="True if returned from pre-computed demo cache."
    )
