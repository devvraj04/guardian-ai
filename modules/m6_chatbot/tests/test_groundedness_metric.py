"""
Chatbot Groundedness Metric Evaluation Test (STATUS.md line 103; SPEC §3.7).
"""

import json
from pathlib import Path
import pytest

from modules.m3_verifier.semantic_verifier import verify_semantic_entailment
from modules.m6_chatbot.generator import generate_grounded_answer
from modules.m6_chatbot.retriever import retrieve_rag_context


@pytest.fixture(scope="module")
def chat_benchmark_cases():
    file_path = (
        Path(__file__).resolve().parents[3]
        / "data"
        / "test_cases"
        / "chat_benchmark_cases.json"
    )
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def test_chatbot_groundedness_metric(chat_benchmark_cases):
    """
    Evaluates that chatbot answers are traceable to retrieved passages
    and pass semantic groundedness verification.
    """
    total = len(chat_benchmark_cases)
    grounded_count = 0

    for case in chat_benchmark_cases:
        query = case["query"]
        expected_citation = case["expected_citation"]

        context, citations = retrieve_rag_context(
            query=query,
            user_id="test_groundedness_user",
            loan_id="test_groundedness_loan",
        )

        answer, used_citations, is_cached = generate_grounded_answer(
            query=query,
            context=context,
            citations=citations,
            use_cache=True,
        )

        # 1. Traceability to retrieved citation
        has_expected_citation = any(
            expected_citation.lower() in c.citation_id.lower()
            or expected_citation.lower() in c.text.lower()
            for c in used_citations
        )
        assert has_expected_citation, f"Case {case['case_id']}: Expected citation '{expected_citation}' not found in used citations"

        # 2. Semantic Grounding Check via RoBERTa-MNLI
        passage_texts = [c.text for c in used_citations]
        sem_res = verify_semantic_entailment(
            claim_text=answer,
            premises=passage_texts,
        )

        if sem_res.verdict == "grounded" or sem_res.score >= 0.50:
            grounded_count += 1

    groundedness_rate = (grounded_count / total) * 100.0
    print(
        f"\nChatbot Groundedness Rate: {groundedness_rate:.1f}% ({grounded_count}/{total})"
    )

    assert (
        groundedness_rate >= 80.0
    ), f"Groundedness rate {groundedness_rate}% < 80.0% target"
