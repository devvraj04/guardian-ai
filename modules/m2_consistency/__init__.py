"""
GUARDIAN Module 2 — Consistency Matching Layer.
Cross-source comparison between Manual Entry, T&C extracted fields, and KFS extracted fields.
"""

from modules.m2_consistency.consistency import (
    compare_numeric_field,
    compare_prepayment_clauses,
    run_consistency_check,
)

__all__ = [
    "compare_numeric_field",
    "compare_prepayment_clauses",
    "run_consistency_check",
]
