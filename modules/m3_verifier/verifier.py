"""
Module 3: Dual Groundedness Verifier Coordinator.
Governing Rules: RULES.md §1, §2, §4.3, §4.7; SPEC §3.4; IMPLEMENTATION_PLAN Phase 6.

Coordinates dual semantic (RoBERTa-MNLI) and numeric (Module 1/1b recompute) verification.
Every Claim from any module or chatbot must pass through here.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4
from supabase import Client

from app.core.config import settings
from app.core.logging import logger
from app.schemas.claim import Claim
from app.schemas.verification import VerificationResult
from modules.m3_verifier.numeric_verifier import verify_numeric_figures
from modules.m3_verifier.semantic_verifier import verify_semantic_entailment
from rag.chroma_client import query_rbi_corpus, query_user_documents


def get_default_supabase() -> Client:
    from supabase import create_client

    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)


def verify_claim(
    claim: Claim,
    user_id: str,
    loan_id: str,
    supabase_client: Optional[Client] = None,
    custom_premises: Optional[List[str]] = None,
    persist: bool = True,
) -> VerificationResult:
    """
    Executes the Dual Groundedness Verification pipeline for a given Claim (RULES.md §1).

    1. Retrieves candidate evidence:
       - user_documents scoped to (user_id, loan_id) via Phase 5 wrapper
       - rbi_corpus regulatory clauses
    2. Runs RoBERTa-MNLI Semantic Entailment Verifier.
    3. Runs Deterministic Numeric Verifier using Module 1 & 1b.
    4. Produces composite VerificationResult with strict error classification.
    5. Persists result in verification_results and updates claims status.
    6. Logs event in append-only audit_log.
    """
    verification_id = str(uuid4())
    logger.info(
        f"Initiating Module 3 Dual Verification for claim_id={claim.claim_id} (source={claim.source_module})"
    )

    # Step 1: Evidence Retrieval (RULES.md §2)
    source_passages: List[str] = []
    retrieved_sources_metadata: List[Dict[str, Any]] = []

    if custom_premises:
        source_passages.extend(custom_premises)
        retrieved_sources_metadata.extend(
            [{"source": "custom_fixture", "text": p} for p in custom_premises]
        )
    else:
        # 1a. Retrieve from scoped user documents (Phase 5 secure wrapper)
        try:
            user_doc_results = query_user_documents(
                user_id=user_id,
                loan_id=loan_id,
                query_texts=[claim.claim_text],
                n_results=4,
            )
            if user_doc_results.get("documents") and user_doc_results["documents"][0]:
                for doc_text, meta in zip(
                    user_doc_results["documents"][0], user_doc_results["metadatas"][0]
                ):
                    source_passages.append(doc_text)
                    retrieved_sources_metadata.append(
                        {
                            "source": "user_documents",
                            "doc_type": meta.get("doc_type"),
                            "text": doc_text,
                        }
                    )
        except Exception as e:
            logger.warning(f"Error retrieving user_documents during verification: {e}")

        # 1b. Retrieve from shared RBI regulatory corpus
        try:
            rbi_results = query_rbi_corpus(
                query_texts=[claim.claim_text],
                n_results=4,
            )
            if rbi_results.get("documents") and rbi_results["documents"][0]:
                for doc_text, meta in zip(
                    rbi_results["documents"][0], rbi_results["metadatas"][0]
                ):
                    source_passages.append(doc_text)
                    retrieved_sources_metadata.append(
                        {
                            "source": "rbi_corpus",
                            "clause_id": meta.get("clause_id"),
                            "section_id": meta.get("section_id"),
                            "text": doc_text,
                        }
                    )
        except Exception as e:
            logger.warning(f"Error retrieving rbi_corpus during verification: {e}")

    # Step 2: Semantic Verification (RoBERTa-MNLI)
    # Recompute-only claims with deterministic calculations can evaluate against premise if available
    semantic_output = verify_semantic_entailment(
        claim_text=claim.claim_text,
        premises=source_passages,
    )

    # Step 3: Numeric Truth Verification (Module 1 / Module 1b)
    numeric_output = verify_numeric_figures(
        claim_text=claim.claim_text,
        supporting_figures=claim.supporting_figures,
    )

    # Step 4: Determine Composite Final Verdict & Error Type (RULES.md §1.4)
    # Truth matrix:
    # - If numeric check ran and failed: flagged
    # - If semantic check failed with contradiction: flagged
    # - For pure recompute/serviceability claims (where arithmetic is the primary thesis):
    #   if numeric check passed and no semantic contradiction exists, mark grounded.
    # - For regulatory/chat text claims: semantic entailment must pass.

    is_semantic_pass = semantic_output.verdict == "grounded"
    is_numeric_pass = numeric_output.verdict in ("grounded", "not_applicable")

    # Special handling for pure arithmetic recompute/serviceability claims
    if (
        claim.source_module in ("recompute", "serviceability")
        and numeric_output.verdict == "grounded"
    ):
        # Unless directly contradicted by contractual premise, numeric grounding holds
        if semantic_output.error_type != "semantic_mismatch":
            is_semantic_pass = True

    if not is_semantic_pass and not is_numeric_pass:
        final_verdict = "flagged"
        error_type = "both"
    elif not is_semantic_pass:
        final_verdict = "flagged"
        error_type = semantic_output.error_type or "semantic_mismatch"
    elif not is_numeric_pass:
        final_verdict = "flagged"
        error_type = "numeric_mismatch"
    else:
        final_verdict = "grounded"
        error_type = None

    verdict_time = datetime.now(timezone.utc)

    # Step 5: Construct canonical VerificationResult
    result = VerificationResult(
        id=verification_id,
        claim_id=claim.claim_id,
        semantic_verdict=semantic_output.verdict,
        numeric_verdict=numeric_output.verdict,
        final_verdict=final_verdict,
        error_type=error_type,
        semantic_score=semantic_output.score,
        numeric_details=numeric_output.details,
        retrieved_sources=retrieved_sources_metadata[:5],
        verified_at=verdict_time,
    )

    # Step 6: Persist to Supabase Database (public.verification_results & public.claims)
    if persist:
        supabase = supabase_client or get_default_supabase()
        if supabase:
            try:
                # Check if claim exists in database before inserting to avoid FK violation in unit/benchmark fixtures
                claim_exists = (
                    supabase.table("claims")
                    .select("claim_id")
                    .eq("claim_id", claim.claim_id)
                    .execute()
                )
                if claim_exists.data:
                    supabase.table("verification_results").insert(
                        {
                            "id": result.id,
                            "claim_id": result.claim_id,
                            "semantic_verdict": result.semantic_verdict,
                            "numeric_verdict": result.numeric_verdict,
                            "final_verdict": result.final_verdict,
                            "error_type": result.error_type,
                            "verified_at": result.verified_at.isoformat(),
                        }
                    ).execute()

                    # Update claim verification status
                    supabase.table("claims").update(
                        {
                            "verification_status": result.final_verdict,
                        }
                    ).eq("claim_id", claim.claim_id).execute()

                    # Append to audit_log (Rule S-21)
                    supabase.table("audit_log").insert(
                        {
                            "user_id": user_id,
                            "action": "CLAIM_VERIFIED",
                            "entity_type": "verification_results",
                            "entity_id": result.id,
                            "metadata": {
                                "claim_id": claim.claim_id,
                                "final_verdict": result.final_verdict,
                                "error_type": result.error_type,
                                "semantic_score": result.semantic_score,
                            },
                        }
                    ).execute()
                else:
                    logger.debug(
                        f"Claim {claim.claim_id} not committed in database; skipping DB persistence"
                    )
            except Exception as e:
                logger.error(f"Failed to persist verification result to database: {e}")

    return result
