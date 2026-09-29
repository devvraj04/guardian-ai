"""
Module 4: Vernacular Verification (Hindi and Marathi).
Governing Rules: RULES.md §1.6; SPEC §3.4; IMPLEMENTATION_PLAN Phase 7.
"""

from modules.m4_vernacular.cache import translation_cache
from modules.m4_vernacular.translator import translate_claim
from modules.m4_vernacular.vernacular_verifier import (
    compute_cross_lingual_metrics,
    verify_vernacular_claim,
)

__all__ = [
    "translation_cache",
    "translate_claim",
    "compute_cross_lingual_metrics",
    "verify_vernacular_claim",
]
