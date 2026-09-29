from app.core.logging import logger
from modules.m0_intake.chunker import chunk_document_text
from rag.chroma_client import insert_user_document_chunks


def ingest_document_into_chroma(
    user_id: str,
    loan_id: str,
    doc_type: str,
    doc_id: str,
    raw_text: str,
) -> int:
    """
    Chunks document text and embeds into the user_documents collection via chroma_client (RULES.md §2).
    Returns the number of chunks successfully inserted.
    """
    if not raw_text or not raw_text.strip():
        logger.warning(f"No text available to ingest for doc_id: {doc_id}")
        return 0

    chunks = chunk_document_text(raw_text)
    if not chunks:
        logger.warning(f"Chunker produced 0 chunks for doc_id: {doc_id}")
        return 0

    chunk_ids = [f"{doc_id}_chunk_{i}" for i in range(len(chunks))]

    insert_user_document_chunks(
        user_id=user_id,
        loan_id=loan_id,
        doc_type=doc_type,
        doc_id=doc_id,
        chunks=chunks,
        chunk_ids=chunk_ids,
    )

    logger.info(
        f"Ingested {len(chunks)} chunks into ChromaDB user_documents for doc_id: {doc_id}"
    )
    return len(chunks)
