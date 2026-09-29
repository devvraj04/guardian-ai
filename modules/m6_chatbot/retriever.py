"""
Retriever for Module 6 (RAG Chatbot).
Governing Rules: RULES.md §2, §2.4; SPEC §3.4; IMPLEMENTATION_PLAN Phase 9.

Combines top-k passages from scoped user_documents (via Phase 5 security wrapper)
and shared rbi_corpus. Never retrieves cross-user documents.
"""

from typing import List, Tuple

from app.core.logging import logger
from app.schemas.chat import RetrievedContextCitation
from rag.chroma_client import query_rbi_corpus, query_user_documents


def retrieve_rag_context(
    query: str,
    user_id: str,
    loan_id: str,
    n_user_results: int = 3,
    n_rbi_results: int = 3,
) -> Tuple[str, List[RetrievedContextCitation]]:
    """
    Retrieves and merges candidate context passages for the chatbot from:
    1. Scoped user_documents (Phase 5 secure wrapper)
    2. Shared rbi_corpus
    Returns combined prompt context string and structured citation list.
    """
    citations: List[RetrievedContextCitation] = []
    passages: List[str] = []

    # 1. Scoped User Documents Retrieval
    try:
        user_res = query_user_documents(
            user_id=user_id,
            loan_id=loan_id,
            query_texts=[query],
            n_results=n_user_results,
        )
        if user_res.get("documents") and user_res["documents"][0]:
            for doc_text, meta in zip(
                user_res["documents"][0], user_res["metadatas"][0]
            ):
                doc_type = meta.get("doc_type", "document")
                citations.append(
                    RetrievedContextCitation(
                        source="user_documents",
                        citation_id=doc_type,
                        text=doc_text,
                    )
                )
                passages.append(f"[SOURCE: User Document ({doc_type})]\n{doc_text}")
    except Exception as e:
        logger.warning(f"Error querying user_documents during chat retrieval: {e}")

    # 2. Shared RBI Regulatory Corpus Retrieval
    try:
        rbi_res = query_rbi_corpus(
            query_texts=[query],
            n_results=n_rbi_results,
        )
        if rbi_res.get("documents") and rbi_res["documents"][0]:
            for doc_text, meta in zip(rbi_res["documents"][0], rbi_res["metadatas"][0]):
                clause_id = meta.get("clause_id", meta.get("section_id", "RBI Clause"))
                citations.append(
                    RetrievedContextCitation(
                        source="rbi_corpus",
                        citation_id=clause_id,
                        text=doc_text,
                    )
                )
                passages.append(f"[SOURCE: RBI Regulation ({clause_id})]\n{doc_text}")
    except Exception as e:
        logger.warning(f"Error querying rbi_corpus during chat retrieval: {e}")

    combined_context = "\n\n".join(passages)
    return combined_context, citations
