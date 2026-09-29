"""
Unit tests for RAG Context Retriever (Module 6).
"""

from uuid import uuid4
from modules.m6_chatbot.retriever import retrieve_rag_context


def test_retrieve_rag_context_merges_sources():
    test_user_id = str(uuid4())
    test_loan_id = str(uuid4())

    query = "prepayment penalties on floating rate loans"
    context, citations = retrieve_rag_context(
        query=query,
        user_id=test_user_id,
        loan_id=test_loan_id,
        n_user_results=2,
        n_rbi_results=2,
    )

    # RBI corpus should return relevant regulatory clauses
    assert len(citations) >= 1
    assert any(c.source == "rbi_corpus" for c in citations)
    assert "prepayment" in context.lower()
