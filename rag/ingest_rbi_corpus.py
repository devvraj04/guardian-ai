import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional
from rag.chroma_client import RBI_CORPUS_COLLECTION, get_chroma_client


def parse_rbi_clauses(text: str) -> List[Dict[str, Any]]:
    """
    Parses the RBI Digital Lending Directions into structured clauses with rich metadata.
    """
    clauses = []
    lines = text.split("\n")

    current_section_id = ""
    current_section_title = ""
    current_clause_id = ""
    current_clause_lines = []

    def commit_clause():
        if current_clause_id and current_clause_lines:
            clause_text = " ".join([l.strip() for l in current_clause_lines if l.strip()])
            clauses.append({
                "id": f"rbi_clause_{current_clause_id.replace('.', '_')}",
                "document": f"[Section {current_section_id}: {current_section_title}] Clause {current_clause_id}: {clause_text}",
                "metadata": {
                    "source": "RBI_DIGITAL_LENDING_DIRECTIONS_2025",
                    "section_id": current_section_id,
                    "section_title": current_section_title,
                    "clause_id": current_clause_id,
                },
            })

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        # Check for section header, e.g., "1. Short Title and Commencement:"
        sec_match = re.match(r"^(\d+)\.\s+([A-Za-z0-9\s\(\)\-\,\/]+):$", stripped)
        if sec_match:
            commit_clause()
            current_section_id = sec_match.group(1)
            current_section_title = sec_match.group(2).strip()
            current_clause_id = ""
            current_clause_lines = []
            continue

        # Check for clause header, e.g., "1.1 These directions..."
        clause_match = re.match(r"^(\d+\.\d+)\s+(.*)$", stripped)
        if clause_match:
            commit_clause()
            current_clause_id = clause_match.group(1)
            current_clause_lines = [clause_match.group(2)]
            continue

        # Continuation line (e.g. sub-bullets in 3.2)
        if current_clause_id:
            current_clause_lines.append(stripped)

    commit_clause()
    return clauses


def ingest_rbi_corpus_file(file_path: Optional[str] = None) -> int:
    """
    Reads the raw RBI text file and inserts/upserts all parsed clauses into the rbi_corpus collection.
    Returns the number of clauses ingested.
    """
    if file_path is None:
        file_path = str(
            Path(__file__).resolve().parents[1]
            / "data"
            / "raw"
            / "rbi_digital_lending_directions_2025.txt"
        )

    with open(file_path, "r", encoding="utf-8") as f:
        text = f.read()

    clauses = parse_rbi_clauses(text)
    if not clauses:
        raise ValueError(f"No clauses parsed from {file_path}")

    client = get_chroma_client()
    collection = client.get_or_create_collection(
        name=RBI_CORPUS_COLLECTION,
        metadata={"description": "RBI Digital Lending Directions 2025 regulatory text"},
    )

    ids = [c["id"] for c in clauses]
    documents = [c["document"] for c in clauses]
    metadatas = [c["metadata"] for c in clauses]

    collection.upsert(
        ids=ids,
        documents=documents,
        metadatas=metadatas,
    )

    return len(clauses)


if __name__ == "__main__":
    count = ingest_rbi_corpus_file()
    print(f"Successfully ingested {count} RBI clauses into {RBI_CORPUS_COLLECTION}.")
