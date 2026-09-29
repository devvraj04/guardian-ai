"""
Module 4: Vernacular Verification Coordinator.
Governing Rules: RULES.md §1.6; SPEC §3.4; IMPLEMENTATION_PLAN Phase 7.

CRITICAL INVARIANT (RULES.md §1.6):
Module 4 MUST import and call Module 3's verifier functions.
It does NOT fork, copy, or reimplement any part of the semantic or numeric check.
"""

import re
from typing import List, Optional

from app.schemas.claim import Claim
from app.schemas.vernacular import (
    VernacularLanguage,
    VernacularMetricReport,
    VernacularVerificationResponse,
)
from modules.m3_verifier.semantic_verifier import verify_semantic_entailment
from modules.m3_verifier.verifier import verify_claim
from modules.m4_vernacular.translator import translate_claim


def _extract_all_numbers(text: str) -> List[float]:
    """Extracts all floating point and integer numbers from text for exact numeric preservation check."""
    # Matches patterns like 100,000 or 15.89 or 23 or 8884.88
    raw_nums = re.findall(r"\b\d+(?:,\d+)*(?:\.\d+)?\b", text)
    clean_nums: List[float] = []
    for rn in raw_nums:
        try:
            val = float(rn.replace(",", ""))
            clean_nums.append(val)
        except ValueError:
            continue
    return clean_nums


def compute_cross_lingual_metrics(
    original_text: str,
    back_translated_text: str,
) -> VernacularMetricReport:
    """
    Computes Cross-Lingual Numeric Preservation Rate, Semantic Drift Score,
    and Clause-Drop Rate using Module 3's semantic verifier (RoBERTa-MNLI).
    """
    # 1. Cross-Lingual Numeric Preservation Rate
    orig_nums = _extract_all_numbers(original_text)
    back_nums = _extract_all_numbers(back_translated_text)

    if not orig_nums:
        numeric_preservation_rate = 100.0
        preserved_count = 0
        total_count = 0
    else:
        total_count = len(orig_nums)
        # Check how many original numbers appear within 1% or exact match in back-translated numbers
        preserved_count = 0
        matched_indices = set()
        for on in orig_nums:
            for j, bn in enumerate(back_nums):
                if j not in matched_indices:
                    diff = abs(on - bn)
                    # Tolerance: within 0.05 or relative 1%
                    if diff <= 0.05 or (on > 0 and (diff / on) <= 0.01):
                        preserved_count += 1
                        matched_indices.add(j)
                        break

        numeric_preservation_rate = round((preserved_count / total_count) * 100.0, 2)

    # 2. Semantic Drift Score (entailment probability via Module 3 RoBERTa-MNLI)
    semantic_eval = verify_semantic_entailment(
        claim_text=back_translated_text,
        premises=[original_text],
    )
    # Drift score = entailment score (1.0 = identical semantics / zero drift)
    semantic_drift_score = round(semantic_eval.score, 4)

    # 3. Clause-Drop Rate
    # Split original claim into major clauses (sentences or semicolon-separated clauses), avoiding decimal points
    raw_clauses = [
        c.strip()
        for c in re.split(r"(?<!\d)\.(?!\d)|[;\n]+", original_text)
        if c.strip() and len(c.strip().split()) >= 3
    ]

    dropped_clauses: List[str] = []
    if not raw_clauses:
        clause_drop_rate = 0.0
    else:
        for clause in raw_clauses:
            clause_eval = verify_semantic_entailment(
                claim_text=clause,
                premises=[back_translated_text],
            )
            # If the back-translated text does not entail the clause, it was dropped
            if clause_eval.verdict != "grounded" and clause_eval.score < 0.40:
                dropped_clauses.append(clause)

        clause_drop_rate = round((len(dropped_clauses) / len(raw_clauses)) * 100.0, 2)

    return VernacularMetricReport(
        numeric_preservation_rate=numeric_preservation_rate,
        semantic_drift_score=semantic_drift_score,
        clause_drop_rate=clause_drop_rate,
        preserved_figures_count=preserved_count,
        total_figures_count=total_count,
        dropped_clauses=dropped_clauses,
    )


def verify_vernacular_claim(
    claim: Claim,
    user_id: str,
    loan_id: str,
    target_language: VernacularLanguage,
    custom_premises: Optional[List[str]] = None,
    use_cache_only: bool = False,
) -> VernacularVerificationResponse:
    """
    Complete Phase 7 Vernacular Verification Workflow:
    1. Forward-translates claim to target vernacular (Hindi or Marathi).
    2. Back-translates claim to English.
    3. Computes cross-lingual preservation metrics.
    4. Re-runs Module 3's own verify_claim function on the back-translated text.
    """
    # 1. Translate & Back-Translate
    translation_output = translate_claim(
        claim_text=claim.claim_text,
        target_language=target_language,
        use_cache_only=use_cache_only,
    )

    # 2. Compute Cross-Lingual Metrics
    metrics = compute_cross_lingual_metrics(
        original_text=claim.claim_text,
        back_translated_text=translation_output.back_translated_text,
    )

    # 3. Re-run Module 3's own functions on the back-translated Claim (RULES.md §1.6)
    back_translated_claim = Claim(
        claim_id=claim.claim_id,
        source_module=claim.source_module,
        user_id=claim.user_id,
        loan_id=claim.loan_id,
        claim_text=translation_output.back_translated_text,
        supporting_figures=claim.supporting_figures,
        source_record_id=claim.source_record_id,
    )

    # Note: persist=False so vernacular verification does not overwrite primary claim records
    verification_result = verify_claim(
        claim=back_translated_claim,
        user_id=user_id,
        loan_id=loan_id,
        custom_premises=custom_premises,
        persist=False,
    )

    return VernacularVerificationResponse(
        claim_id=claim.claim_id,
        original_text=claim.claim_text,
        target_language=target_language,
        translated_text=translation_output.translated_text,
        back_translated_text=translation_output.back_translated_text,
        metrics=metrics,
        verification_verdict=verification_result.final_verdict,
        verification_details=verification_result,
        is_cached=translation_output.is_cached,
    )
