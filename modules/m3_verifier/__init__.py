"""
Module 3: Dual Groundedness Verifier package.
"""

from modules.m3_verifier.numeric_verifier import (
    NumericVerificationOutput,
    verify_numeric_figures,
)
from modules.m3_verifier.semantic_verifier import (
    SemanticVerificationOutput,
    verify_semantic_entailment,
)
from modules.m3_verifier.verifier import verify_claim

__all__ = [
    "verify_claim",
    "verify_semantic_entailment",
    "SemanticVerificationOutput",
    "verify_numeric_figures",
    "NumericVerificationOutput",
]
