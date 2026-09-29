"""
Module 3: Semantic Groundedness Verifier (NLI Entailment).
Governing Rules: RULES.md §1.4, §1.6; SPEC §3.4; IMPLEMENTATION_PLAN Phase 6.

Evaluates (retrieved_source_passage, claim_text) using RoBERTa-MNLI (roberta-large-mnli).
Determines whether retrieved regulatory or contract evidence strictly entails the claim text.
"""

from dataclasses import dataclass
from typing import List, Optional, Tuple
import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from app.core.logging import logger

MODEL_NAME = "roberta-large-mnli"

_tokenizer: Optional[AutoTokenizer] = None
_model: Optional[AutoModelForSequenceClassification] = None
_device: Optional[torch.device] = None


@dataclass(frozen=True)
class SemanticVerificationOutput:
    verdict: str  # "grounded" | "flagged"
    score: float  # Entailment probability [0.0, 1.0]
    error_type: Optional[str] = (
        None  # None | "semantic_mismatch" | "insufficient_evidence"
    )
    best_passage: Optional[str] = None
    contradiction_score: float = 0.0


def get_nli_model() -> (
    Tuple[AutoTokenizer, AutoModelForSequenceClassification, torch.device]
):
    """
    Lazy-loads and returns the singleton RoBERTa-MNLI model and tokenizer.
    Uses GPU acceleration when CUDA is available.
    """
    global _tokenizer, _model, _device
    if _model is None or _tokenizer is None:
        logger.info(f"Initializing Semantic Verifier model: {MODEL_NAME}")
        _device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        _tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
        _model = AutoModelForSequenceClassification.from_pretrained(MODEL_NAME)
        _model.to(_device)
        _model.eval()
        logger.info(f"Loaded {MODEL_NAME} on device: {_device}")
    return _tokenizer, _model, _device


def verify_semantic_entailment(
    claim_text: str,
    premises: List[str],
    entailment_threshold: float = 0.55,
    contradiction_threshold: float = 0.70,
) -> SemanticVerificationOutput:
    """
    Performs NLI inference over candidate source premises against claim_text.

    RoBERTa-MNLI label mapping:
    0: CONTRADICTION
    1: NEUTRAL
    2: ENTAILMENT
    """
    if not claim_text or not claim_text.strip():
        return SemanticVerificationOutput(
            verdict="flagged",
            score=0.0,
            error_type="insufficient_evidence",
            best_passage=None,
        )

    # Filter out empty or whitespace-only premises
    valid_premises = [p.strip() for p in premises if p and p.strip()]
    if not valid_premises:
        return SemanticVerificationOutput(
            verdict="flagged",
            score=0.0,
            error_type="insufficient_evidence",
            best_passage=None,
        )

    tokenizer, model, device = get_nli_model()

    best_entailment = 0.0
    highest_contradiction = 0.0
    best_passage = None

    for premise in valid_premises:
        # Tokenize premise (source evidence) and hypothesis (claim text)
        encoded = tokenizer(
            premise,
            claim_text,
            truncation=True,
            max_length=512,
            return_tensors="pt",
        )
        encoded = {k: v.to(device) for k, v in encoded.items()}

        with torch.no_grad():
            logits = model(**encoded).logits
            probs = torch.softmax(logits, dim=-1)[0]

        contra_prob = float(probs[0].item())
        entail_prob = float(probs[2].item())

        if contra_prob > highest_contradiction:
            highest_contradiction = contra_prob

        if entail_prob > best_entailment:
            best_entailment = entail_prob
            best_passage = premise

    # Evaluation Rules:
    # 1. Direct contradiction detected (contradiction is dominant and meets threshold)
    if (
        highest_contradiction >= contradiction_threshold
        and highest_contradiction > best_entailment
    ):
        return SemanticVerificationOutput(
            verdict="flagged",
            score=round(best_entailment, 4),
            error_type="semantic_mismatch",
            best_passage=best_passage,
            contradiction_score=round(highest_contradiction, 4),
        )

    # 2. Strong entailment verified
    if (
        best_entailment >= entailment_threshold
        and best_entailment >= highest_contradiction
    ):
        return SemanticVerificationOutput(
            verdict="grounded",
            score=round(best_entailment, 4),
            error_type=None,
            best_passage=best_passage,
            contradiction_score=round(highest_contradiction, 4),
        )

    # 3. Neither entailed nor contradictory -> Neutral / Insufficient evidence
    return SemanticVerificationOutput(
        verdict="flagged",
        score=round(best_entailment, 4),
        error_type="insufficient_evidence",
        best_passage=best_passage,
        contradiction_score=round(highest_contradiction, 4),
    )
