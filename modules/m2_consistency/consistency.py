import re
from typing import Any, Dict, List, Literal, Optional, Tuple
import numpy as np

from app.schemas.consistency import FieldComparison


# ==============================================================================
# Tolerance Thresholds (RULES.md & IMPLEMENTATION_PLAN.md Phase 3)
# ==============================================================================
TOLERANCE_RULES = {
    "principal": {"type": "rel_or_abs", "rel": 0.001, "abs": 10.0, "unit": "INR"},
    "disclosed_rate": {"type": "abs", "abs": 0.05, "unit": "%"},
    "tenure_months": {"type": "abs", "abs": 0.0, "unit": "months"},
    "fees": {"type": "rel_or_abs", "rel": 0.005, "abs": 10.0, "unit": "INR"},
}

_embedding_function = None


def get_embedding_function():
    """Lazy loader for dense ChromaDB embedding function to avoid unnecessary overhead."""
    global _embedding_function
    if _embedding_function is None:
        try:
            from chromadb.utils.embedding_functions import DefaultEmbeddingFunction
            _embedding_function = DefaultEmbeddingFunction()
        except Exception:
            _embedding_function = None
    return _embedding_function


def compute_cosine_similarity(text1: str, text2: str) -> float:
    """Compute cosine similarity between two prose text clauses."""
    ef = get_embedding_function()
    if ef is None:
        # Fallback to Jaccard token overlap if ONNX embedding model is unavailable
        t1_tokens = set(re.findall(r"\w+", text1.lower()))
        t2_tokens = set(re.findall(r"\w+", text2.lower()))
        if not t1_tokens or not t2_tokens:
            return 0.0
        return float(len(t1_tokens & t2_tokens) / len(t1_tokens | t2_tokens))

    embeddings = ef([text1, text2])
    v1 = np.array(embeddings[0], dtype=np.float32)
    v2 = np.array(embeddings[1], dtype=np.float32)
    norm1 = np.linalg.norm(v1)
    norm2 = np.linalg.norm(v2)
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return float(np.dot(v1, v2) / (norm1 * norm2))


def compare_numeric_field(
    field_name: str,
    manual_val: Optional[Any],
    tnc_val: Optional[Any],
    kfs_val: Optional[Any],
) -> FieldComparison:
    """
    Tolerance-based comparison for numeric loan terms across manual, T&C, and KFS sources.
    """
    rule = TOLERANCE_RULES.get(field_name, {"type": "abs", "abs": 0.01, "unit": ""})
    tolerance_desc = f"{rule['abs']} {rule['unit']}" if rule["type"] == "abs" else f"{rule['abs']} {rule['unit']} or {rule['rel']*100}%"

    values = {
        "manual": float(manual_val) if manual_val is not None and str(manual_val).strip() != "" else None,
        "tnc": float(tnc_val) if tnc_val is not None and str(tnc_val).strip() != "" else None,
        "kfs": float(kfs_val) if kfs_val is not None and str(kfs_val).strip() != "" else None,
    }

    present_values = {src: val for src, val in values.items() if val is not None}

    # Case 1: Missing in one or more sources
    if len(present_values) < 3:
        # Even if some values are missing, check if the available ones already conflict
        if len(present_values) >= 2:
            sources = list(present_values.keys())
            v1, v2 = present_values[sources[0]], present_values[sources[1]]
            diff = abs(v1 - v2)
            max_v = max(abs(v1), abs(v2))
            allowed_tol = rule["abs"]
            if rule["type"] == "rel_or_abs":
                allowed_tol = max(rule["abs"], rule["rel"] * max_v)

            if diff > allowed_tol:
                return FieldComparison(
                    field_name=field_name,
                    manual_value=values["manual"],
                    tnc_value=values["tnc"],
                    kfs_value=values["kfs"],
                    match_status="mismatch",
                    tolerance_applied=tolerance_desc,
                    difference_notes=f"Mismatch detected between {sources[0]} ({v1}) and {sources[1]} ({v2}) [diff: {diff:.2f} > allowed tol {allowed_tol:.2f}].",
                    requires_human_review=False,
                )

        missing_sources = [src for src, val in values.items() if val is None]
        return FieldComparison(
            field_name=field_name,
            manual_value=values["manual"],
            tnc_value=values["tnc"],
            kfs_value=values["kfs"],
            match_status="missing",
            tolerance_applied=tolerance_desc,
            difference_notes=f"Missing values in source(s): {', '.join(missing_sources)}.",
            requires_human_review=False,
        )

    # Case 2: All 3 sources present — pairwise comparison
    pairs = [("manual", "tnc"), ("manual", "kfs"), ("tnc", "kfs")]
    mismatches = []
    for s1, s2 in pairs:
        v1, v2 = values[s1], values[s2]
        diff = abs(v1 - v2)
        max_v = max(abs(v1), abs(v2))
        allowed_tol = rule["abs"]
        if rule["type"] == "rel_or_abs":
            allowed_tol = max(rule["abs"], rule["rel"] * max_v)

        if diff > allowed_tol:
            mismatches.append(f"{s1} ({v1}) vs {s2} ({v2}) diff {diff:.2f} > tol {allowed_tol:.2f}")

    if mismatches:
        return FieldComparison(
            field_name=field_name,
            manual_value=values["manual"],
            tnc_value=values["tnc"],
            kfs_value=values["kfs"],
            match_status="mismatch",
            tolerance_applied=tolerance_desc,
            difference_notes="; ".join(mismatches),
            requires_human_review=False,
        )

    return FieldComparison(
        field_name=field_name,
        manual_value=values["manual"],
        tnc_value=values["tnc"],
        kfs_value=values["kfs"],
        match_status="match",
        tolerance_applied=tolerance_desc,
        difference_notes="All sources agree within specified tolerance.",
        requires_human_review=False,
    )


def extract_prepayment_penalty_pct(clause_text: str) -> Optional[float]:
    """Extract percentage penalty if present in prepayment clause text."""
    if not clause_text:
        return None
    match = re.search(r"(\d+(?:\.\d+)?)\s*%", clause_text)
    if match:
        return float(match.group(1))
    return None


def is_nil_prepayment(clause_text: str) -> bool:
    """Check if the clause explicitly indicates nil, zero, or waived prepayment/foreclosure charges."""
    if not clause_text:
        return False
    lower = clause_text.lower()
    nil_patterns = [
        r"\bnil\b",
        r"\bzero\b",
        r"\bno\s+(?:foreclosure|prepayment|penalty|charges|fee)\b",
        r"\bwaived\b",
        r"\bnone\b",
        r"\b0\s*%",
    ]
    return any(re.search(pat, lower) for pat in nil_patterns)


def compare_prepayment_clauses(
    tnc_clause: Optional[str],
    kfs_clause: Optional[str],
) -> FieldComparison:
    """
    Prose comparison for prepayment/foreclosure terms via semantic similarity and domain heuristic rules.
    Flagged for human review upon disagreement (IMPLEMENTATION_PLAN.md §Phase 3.3).
    """
    tnc_val = tnc_clause.strip() if tnc_clause and tnc_clause.strip() else None
    kfs_val = kfs_clause.strip() if kfs_clause and kfs_clause.strip() else None

    if not tnc_val or not kfs_val:
        missing_srcs = []
        if not tnc_val:
            missing_srcs.append("T&C")
        if not kfs_val:
            missing_srcs.append("KFS")
        return FieldComparison(
            field_name="prepayment_clause",
            manual_value=None,
            tnc_value=tnc_val,
            kfs_value=kfs_val,
            match_status="missing",
            tolerance_applied="Semantic similarity & clause domain heuristics",
            difference_notes=f"Prepayment clause missing in {', '.join(missing_srcs)}.",
            requires_human_review=False,
        )

    tnc_nil = is_nil_prepayment(tnc_val)
    kfs_nil = is_nil_prepayment(kfs_val)
    tnc_pct = extract_prepayment_penalty_pct(tnc_val)
    kfs_pct = extract_prepayment_penalty_pct(kfs_val)

    # Contradiction: One says nil, other specifies a positive fee or penalty percentage
    if (tnc_nil and kfs_pct is not None and kfs_pct > 0) or (kfs_nil and tnc_pct is not None and tnc_pct > 0):
        notes = (
            f"Direct contradiction detected: T&C indicates {'nil charges' if tnc_nil else f'{tnc_pct}% penalty'} "
            f"whereas KFS states {'nil charges' if kfs_nil else f'{kfs_pct}% penalty'}."
        )
        return FieldComparison(
            field_name="prepayment_clause",
            manual_value=None,
            tnc_value=tnc_val,
            kfs_value=kfs_val,
            match_status="mismatch",
            tolerance_applied="Semantic contradiction check",
            difference_notes=notes,
            requires_human_review=True,  # Disagreements flagged for human review (RULES.md)
        )

    # Both specify positive penalty percentages but different amounts
    if tnc_pct is not None and kfs_pct is not None and abs(tnc_pct - kfs_pct) > 0.01:
        return FieldComparison(
            field_name="prepayment_clause",
            manual_value=None,
            tnc_value=tnc_val,
            kfs_value=kfs_val,
            match_status="mismatch",
            tolerance_applied="Percentage penalty equality",
            difference_notes=f"Penalty percentage mismatch: T&C states {tnc_pct}% vs KFS states {kfs_pct}%.",
            requires_human_review=True,
        )

    # Both explicitly indicate zero/nil charges
    if tnc_nil and kfs_nil:
        return FieldComparison(
            field_name="prepayment_clause",
            manual_value=None,
            tnc_value=tnc_val,
            kfs_value=kfs_val,
            match_status="match",
            tolerance_applied="Both clauses declare zero/nil prepayment charges",
            difference_notes="Both documents agree that no prepayment/foreclosure penalties apply.",
            requires_human_review=False,
        )

    # General prose semantic similarity
    sim = compute_cosine_similarity(tnc_val, kfs_val)
    if sim >= 0.80:
        return FieldComparison(
            field_name="prepayment_clause",
            manual_value=None,
            tnc_value=tnc_val,
            kfs_value=kfs_val,
            match_status="match",
            tolerance_applied="Cosine similarity >= 0.80",
            difference_notes=f"Clauses match with high semantic similarity ({sim:.2f}).",
            requires_human_review=False,
        )
    else:
        return FieldComparison(
            field_name="prepayment_clause",
            manual_value=None,
            tnc_value=tnc_val,
            kfs_value=kfs_val,
            match_status="mismatch",
            tolerance_applied="Cosine similarity >= 0.80",
            difference_notes=f"Semantic divergence between clauses (cosine similarity {sim:.2f} < 0.80).",
            requires_human_review=True,
        )


def run_consistency_check(
    manual_terms: Optional[Dict[str, Any]],
    tnc_extracted: Optional[Dict[str, Any]],
    kfs_extracted: Optional[Dict[str, Any]],
) -> Tuple[List[FieldComparison], Literal["match", "mismatch", "missing"], str, bool]:
    """
    Executes three-way consistency checks across manual terms, T&C extracted fields, and KFS extracted fields.
    Returns:
        checks: List of FieldComparison objects
        overall_status: "match" | "mismatch" | "missing"
        summary_explanation: Concise narrative suitable for Claim generation
        requires_human_review: True if any field requires human review
    """
    manual = manual_terms or {}
    tnc = tnc_extracted or {}
    kfs = kfs_extracted or {}

    # Numeric fields
    principal_check = compare_numeric_field("principal", manual.get("principal"), tnc.get("principal"), kfs.get("principal"))
    rate_check = compare_numeric_field("disclosed_rate", manual.get("disclosed_rate"), tnc.get("disclosed_rate"), kfs.get("disclosed_rate"))
    tenure_check = compare_numeric_field("tenure_months", manual.get("tenure_months"), tnc.get("tenure_months"), kfs.get("tenure_months"))

    # Fee mapping: manual uses 'fees', extraction uses 'processing_fee'
    manual_fees = manual.get("fees")
    tnc_fees = tnc.get("processing_fee") if tnc.get("processing_fee") is not None else tnc.get("fees")
    kfs_fees = kfs.get("processing_fee") if kfs.get("processing_fee") is not None else kfs.get("fees")
    fees_check = compare_numeric_field("fees", manual_fees, tnc_fees, kfs_fees)

    # Prose clause comparison
    prepayment_check = compare_prepayment_clauses(tnc.get("prepayment_clause"), kfs.get("prepayment_clause"))

    checks = [principal_check, rate_check, tenure_check, fees_check, prepayment_check]

    mismatches = [c for c in checks if c.match_status == "mismatch"]
    missings = [c for c in checks if c.match_status == "missing"]
    matches = [c for c in checks if c.match_status == "match"]

    requires_human_review = any(c.requires_human_review for c in checks)

    # Determine overall status
    if mismatches:
        overall_status: Literal["match", "mismatch", "missing"] = "mismatch"
    elif missings:
        overall_status = "missing"
    else:
        overall_status = "match"

    # Construct narrative explanation for Claim (RULES.md §1.8)
    if mismatches:
        mismatched_names = [c.field_name for c in mismatches]
        explanation = f"Critical consistency mismatch detected across loan sources for: {', '.join(mismatched_names)}."
        if requires_human_review:
            explanation += " Manual human review is required due to contradictory or divergent contractual terms."
    elif missings:
        missing_names = [c.field_name for c in missings]
        explanation = f"Consistency check incomplete due to missing documents or unextracted fields: {', '.join(missing_names)}."
    else:
        explanation = "All loan terms (principal, interest rate, tenure, fees, and prepayment clauses) agree consistently across manual entry, T&C, and KFS documents within acceptable tolerances."

    return checks, overall_status, explanation, requires_human_review
