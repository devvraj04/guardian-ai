import re
from pathlib import Path
from uuid import uuid4
import pytest

from rag.chroma_client import (
    insert_user_document_chunks,
    query_user_documents,
)


def test_cross_user_vector_isolation():
    """
    Security Invariant Test (RULES.md §2.1, §2.4, S-3):
    Authenticated User B querying ChromaDB MUST NEVER retrieve User A's documents,
    even when using User A's loan_id or matching User A's exact semantic terms.
    """
    user_a = f"user_a_{uuid4().hex[:8]}"
    loan_a = f"loan_a_{uuid4().hex[:8]}"
    doc_a = f"doc_a_{uuid4().hex[:8]}"
    chunk_a_id = f"chunk_a_{uuid4().hex[:8]}"
    doc_a_text = "CONFIDENTIAL FINANCES ALICE: Monthly income INR 1,20,000 with Apex Bank loan agreement."

    user_b = f"user_b_{uuid4().hex[:8]}"
    loan_b = f"loan_b_{uuid4().hex[:8]}"
    doc_b = f"doc_b_{uuid4().hex[:8]}"
    chunk_b_id = f"chunk_b_{uuid4().hex[:8]}"
    doc_b_text = "CONFIDENTIAL FINANCES BOB: Monthly salary INR 65,000 with Zenith Bank credit facility."

    # 1. Ingest User A's confidential chunk
    insert_user_document_chunks(
        user_id=user_a,
        loan_id=loan_a,
        doc_type="tnc",
        doc_id=doc_a,
        chunks=[doc_a_text],
        chunk_ids=[chunk_a_id],
    )

    # 2. Ingest User B's confidential chunk
    insert_user_document_chunks(
        user_id=user_b,
        loan_id=loan_b,
        doc_type="kfs",
        doc_id=doc_b,
        chunks=[doc_b_text],
        chunk_ids=[chunk_b_id],
    )

    # Attack Scenario 1: User B queries using User A's loan_id
    res_tamper_loan = query_user_documents(
        user_id=user_b,
        loan_id=loan_a,
        query_texts=["Apex Bank Alice income"],
    )
    docs_tamper = (
        res_tamper_loan["documents"][0] if res_tamper_loan.get("documents") else []
    )
    assert (
        len(docs_tamper) == 0
    ), f"Security violation: User B accessed User A's loan documents via loan_id spoofing! Leaked: {docs_tamper}"

    # Attack Scenario 2: User B queries their own loan but searches for User A's exact secrets
    res_semantic_leak = query_user_documents(
        user_id=user_b,
        loan_id=loan_b,
        query_texts=["Apex Bank Alice 120000"],
    )
    docs_b = (
        res_semantic_leak["documents"][0] if res_semantic_leak.get("documents") else []
    )
    # Assert Bob's results NEVER contain Alice's text
    for d in docs_b:
        assert (
            "Alice" not in d
        ), f"Security violation: Alice's text leaked to Bob! Leaked: {d}"
        assert (
            "Apex Bank" not in d
        ), f"Security violation: Alice's bank details leaked to Bob! Leaked: {d}"

    # Legitimate Scenario 3: User A queries their own document
    res_alice = query_user_documents(
        user_id=user_a,
        loan_id=loan_a,
        query_texts=["Apex Bank loan agreement"],
    )
    docs_a = res_alice["documents"][0] if res_alice.get("documents") else []
    assert (
        len(docs_a) > 0
    ), "Legitimate query by User A failed to retrieve their own document."
    assert "alice" in docs_a[0].lower()


@pytest.mark.parametrize("invalid_user_id", ["", "   ", "\t\n", None])
def test_query_rejects_invalid_user_id(invalid_user_id):
    """
    Security Invariant Test (RULES.md §2):
    ChromaDB wrapper must immediately reject invalid/empty user_id.
    """
    with pytest.raises(ValueError, match="user_id must be a non-empty string"):
        query_user_documents(
            user_id=invalid_user_id,
            loan_id="loan_valid_123",
            query_texts=["test query"],
        )


@pytest.mark.parametrize("invalid_loan_id", ["", "   ", "\t\n", None])
def test_query_rejects_invalid_loan_id(invalid_loan_id):
    """
    Security Invariant Test (RULES.md §2):
    ChromaDB wrapper must immediately reject invalid/empty loan_id.
    """
    with pytest.raises(ValueError, match="loan_id must be a non-empty string"):
        query_user_documents(
            user_id="user_valid_123",
            loan_id=invalid_loan_id,
            query_texts=["test query"],
        )


def test_no_raw_user_documents_queries_outside_wrapper():
    """
    Architectural Invariant Test (RULES.md §2.2):
    Verifies that no file in app/ or modules/ queries the 'user_documents' collection directly.
    All retrieval code MUST go through rag/chroma_client.py.
    """
    root_dir = Path(__file__).resolve().parents[1]
    dirs_to_check = [root_dir / "app", root_dir / "modules"]

    raw_query_pattern = re.compile(r"collection\.query\s*\(")
    get_user_docs_pattern = re.compile(
        r'get_collection\s*\(\s*["\']user_documents["\']\s*\)'
    )

    violations = []
    for d in dirs_to_check:
        for py_file in d.rglob("*.py"):
            with open(py_file, "r", encoding="utf-8") as f:
                content = f.read()
                if get_user_docs_pattern.search(content) or raw_query_pattern.search(
                    content
                ):
                    violations.append(str(py_file.relative_to(root_dir)))

    assert (
        len(violations) == 0
    ), f"Security violation (RULES.md §2.2): Raw ChromaDB queries detected outside wrapper in: {violations}"
