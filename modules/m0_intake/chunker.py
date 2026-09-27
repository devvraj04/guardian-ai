import re
from typing import List


def chunk_document_text(text: str, chunk_size: int = 500, overlap: int = 100) -> List[str]:
    """
    Splits extracted document text into overlapping clause-level chunks.
    Attempts to respect paragraph and clause boundaries (e.g. numbered clauses, periods).
    """
    clean_text = re.sub(r"\s+", " ", text).strip()
    if not clean_text:
        return []

    if len(clean_text) <= chunk_size:
        return [clean_text]

    chunks: List[str] = []
    start = 0
    while start < len(clean_text):
        end = start + chunk_size
        if end >= len(clean_text):
            chunks.append(clean_text[start:].strip())
            break

        # Look for natural sentence or clause boundary within the last 50 chars of the window
        search_window = clean_text[end - 50 : end + 50]
        boundary = -1
        for sep in [". ", "; ", "\n", ": "]:
            pos = search_window.rfind(sep)
            if pos != -1:
                boundary = (end - 50) + pos + len(sep)
                break

        if boundary != -1 and boundary > start:
            chunks.append(clean_text[start:boundary].strip())
            start = max(boundary - overlap, start + 1)
        else:
            chunks.append(clean_text[start:end].strip())
            start = end - overlap

    return [c for c in chunks if len(c) > 20]
