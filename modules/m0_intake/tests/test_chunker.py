import pytest
from modules.m0_intake.chunker import chunk_document_text


def test_chunk_empty_text():
    assert chunk_document_text("") == []
    assert chunk_document_text("   ") == []


def test_chunk_short_text():
    text = "The borrower shall repay the loan principal in 24 equal monthly installments."
    chunks = chunk_document_text(text, chunk_size=500)
    assert len(chunks) == 1
    assert chunks[0] == text


def test_chunk_long_contract():
    paragraphs = [
        f"Clause {i}: The annual percentage rate is fixed at 12.5% for all transactions in category {i}."
        for i in range(1, 25)
    ]
    full_text = " ".join(paragraphs)
    chunks = chunk_document_text(full_text, chunk_size=300, overlap=50)

    assert len(chunks) > 1
    # Verify no chunk is empty or smaller than minimum length
    for chunk in chunks:
        assert len(chunk) > 20
