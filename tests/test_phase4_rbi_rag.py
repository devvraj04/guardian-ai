import json
from pathlib import Path
import pytest
from rag.chroma_client import query_rbi_corpus
from rag.ingest_rbi_corpus import ingest_rbi_corpus_file


@pytest.fixture(scope="session", autouse=True)
def ensure_rbi_corpus_ingested():
    """Ensures rbi_corpus collection is populated before running retrieval benchmarks."""
    count = ingest_rbi_corpus_file()
    assert count >= 14, f"Expected at least 14 RBI clauses ingested, got {count}"


def test_rbi_retrieval_benchmark_accuracy():
    """
    Evaluates top-3 retrieval accuracy on the 10 canonical RBI benchmark queries.
    Gate: Retrieval must return relevant regulatory passages for >= 90% of queries (STATUS.md Phase 4).
    """
    benchmarks_path = Path(__file__).resolve().parents[1] / "data" / "test_cases" / "rbi_retrieval_benchmarks.json"
    with open(benchmarks_path, "r", encoding="utf-8") as f:
        benchmarks = json.load(f)

    assert len(benchmarks) == 10, "Expected exactly 10 benchmark queries"

    passed_queries = []
    failed_queries = []

    for item in benchmarks:
        query_text = item["query"]
        acceptable_clauses = item.get("acceptable_clause_ids", [item["target_clause_id"]])
        target_section = item["target_section"]
        expected_keywords = [kw.lower() for kw in item["expected_keywords"]]

        results = query_rbi_corpus([query_text], n_results=3)

        retrieved_docs = results["documents"][0] if results.get("documents") else []
        retrieved_metas = results["metadatas"][0] if results.get("metadatas") else []

        # Check if any acceptable clause ID appears in metadatas OR target section + keywords in documents
        clause_match = any(m.get("clause_id") in acceptable_clauses for m in retrieved_metas)
        section_match = any(m.get("section_id") == target_section for m in retrieved_metas)

        doc_text_combined = " ".join(retrieved_docs).lower()
        keyword_match = any(kw in doc_text_combined for kw in expected_keywords)

        if clause_match or (section_match and keyword_match):
            passed_queries.append(item["query_id"])
        else:
            failed_queries.append({
                "query_id": item["query_id"],
                "target_clause": target_clause_id,
                "retrieved_clauses": [m.get("clause_id") for m in retrieved_metas],
            })

    accuracy = len(passed_queries) / len(benchmarks)
    print(f"\nRBI RAG Benchmark Accuracy: {accuracy*100:.1f}% ({len(passed_queries)}/10 queries passed)")

    assert accuracy >= 0.90, (
        f"Retrieval gate failed: Accuracy {accuracy*100:.1f}% < 90%. "
        f"Failed queries: {failed_queries}"
    )


def test_rbi_corpus_metadata_integrity():
    """
    Verifies that all retrieved items contain proper audit metadata.
    """
    results = query_rbi_corpus(["Key Fact Statement APR fees"], n_results=3)
    assert results["documents"] and len(results["documents"][0]) > 0

    top_metadata = results["metadatas"][0][0]
    assert "source" in top_metadata
    assert top_metadata["source"] == "RBI_DIGITAL_LENDING_DIRECTIONS_2025"
    assert "clause_id" in top_metadata
    assert "section_id" in top_metadata
