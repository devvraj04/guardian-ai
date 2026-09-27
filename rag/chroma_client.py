import chromadb
from chromadb.config import Settings as ChromaSettings
from typing import Any, Dict, List, Optional
from app.core.config import settings
from app.core.logging import logger

_chroma_client: Optional[chromadb.HttpClient] = None

RBI_CORPUS_COLLECTION = "rbi_corpus"
USER_DOCUMENTS_COLLECTION = "user_documents"


def get_chroma_client() -> chromadb.HttpClient:
    """
    Returns the singleton ChromaDB HTTP client connected to the Docker container.
    """
    global _chroma_client
    if _chroma_client is None:
        _chroma_client = chromadb.HttpClient(
            host=settings.CHROMA_HOST,
            port=settings.CHROMA_PORT,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
    return _chroma_client


def get_or_create_collections() -> Dict[str, chromadb.Collection]:
    """
    Initializes and returns the two mandatory ChromaDB collections:
    1. rbi_corpus (shared regulatory corpus)
    2. user_documents (scoped per-user/per-loan document chunks)
    """
    client = get_chroma_client()
    rbi_col = client.get_or_create_collection(
        name=RBI_CORPUS_COLLECTION,
        metadata={"description": "RBI Digital Lending Directions 2025 regulatory text"},
    )
    user_docs_col = client.get_or_create_collection(
        name=USER_DOCUMENTS_COLLECTION,
        metadata={"description": "User uploaded T&C and KFS document chunks"},
    )
    return {
        RBI_CORPUS_COLLECTION: rbi_col,
        USER_DOCUMENTS_COLLECTION: user_docs_col,
    }


def query_user_documents(
    user_id: str,
    loan_id: str,
    query_texts: List[str],
    n_results: int = 5,
    doc_type: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Security-critical query wrapper for user_documents collection (RULES.md §2.1, §2.2).

    MANDATORY SECURITY ENFORCEMENT:
    ChromaDB does NOT possess row-level security. Every query against user_documents
    MUST pass an explicit where filter containing BOTH user_id and loan_id.
    Direct calls to the raw collection from modules or routes are strictly forbidden.
    """
    if not user_id or not isinstance(user_id, str) or not user_id.strip():
        raise ValueError("Security violation: user_id must be a non-empty string for querying user_documents")
    if not loan_id or not isinstance(loan_id, str) or not loan_id.strip():
        raise ValueError("Security violation: loan_id must be a non-empty string for querying user_documents")

    user_id = user_id.strip()
    loan_id = loan_id.strip()

    # Enforce strict metadata filter
    metadata_filter: Dict[str, Any]
    if doc_type:
        metadata_filter = {
            "$and": [
                {"user_id": {"$eq": user_id}},
                {"loan_id": {"$eq": loan_id}},
                {"doc_type": {"$eq": doc_type}},
            ]
        }
    else:
        metadata_filter = {
            "$and": [
                {"user_id": {"$eq": user_id}},
                {"loan_id": {"$eq": loan_id}},
            ]
        }

    client = get_chroma_client()
    collection = client.get_collection(USER_DOCUMENTS_COLLECTION)

    results = collection.query(
        query_texts=query_texts,
        n_results=n_results,
        where=metadata_filter,
    )
    return results


def insert_user_document_chunks(
    user_id: str,
    loan_id: str,
    doc_type: str,
    doc_id: str,
    chunks: List[str],
    chunk_ids: List[str],
    extra_metadatas: Optional[List[Dict[str, Any]]] = None,
) -> None:
    """
    Inserts chunks into user_documents, guaranteeing user_id and loan_id are always stamped.
    """
    if not user_id or not isinstance(user_id, str) or not user_id.strip():
        raise ValueError("Security violation: user_id must be a non-empty string to stamp chunks")
    if not loan_id or not isinstance(loan_id, str) or not loan_id.strip():
        raise ValueError("Security violation: loan_id must be a non-empty string to stamp chunks")
    if not doc_id or not isinstance(doc_id, str) or not doc_id.strip():
        raise ValueError("Security violation: doc_id must be a non-empty string to stamp chunks")

    user_id = user_id.strip()
    loan_id = loan_id.strip()
    doc_id = doc_id.strip()

    client = get_chroma_client()
    collection = client.get_collection(USER_DOCUMENTS_COLLECTION)

    metadatas: List[Dict[str, Any]] = []
    for idx in range(len(chunks)):
        meta = {
            "user_id": user_id,
            "loan_id": loan_id,
            "doc_type": doc_type,
            "doc_id": doc_id,
            "chunk_index": idx,
        }
        if extra_metadatas and idx < len(extra_metadatas):
            meta.update(extra_metadatas[idx])
        metadatas.append(meta)

    collection.add(
        ids=chunk_ids,
        documents=chunks,
        metadatas=metadatas,
    )


def query_rbi_corpus(
    query_texts: List[str],
    n_results: int = 5,
) -> Dict[str, Any]:
    """
    Queries the shared RBI regulatory corpus.
    """
    client = get_chroma_client()
    collection = client.get_collection(RBI_CORPUS_COLLECTION)
    return collection.query(
        query_texts=query_texts,
        n_results=n_results,
    )
