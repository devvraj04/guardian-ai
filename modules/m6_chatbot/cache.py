"""
Chatbot Answer Cache for Module 6.
Governing Rules: RULES.md §5.5; SPEC §3.4; IMPLEMENTATION_PLAN Phase 9.

Pre-computes and caches scripted demo queries to guarantee sub-millisecond response
times and eliminate external dependency failures during viva demonstrations.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

CACHE_FILE_PATH = (
    Path(__file__).resolve().parents[2] / "data" / "cache" / "chat_cache.json"
)


class ChatCache:
    """Manages pre-computed RAG answers and citations for demo and benchmark queries."""

    def __init__(self, cache_file: Optional[Path] = None):
        self.cache_file = cache_file or CACHE_FILE_PATH
        self._cache: Dict[str, Dict[str, Any]] = {}
        self.load()

    def load(self) -> None:
        if self.cache_file.exists():
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    self._cache = json.load(f)
            except Exception:
                self._cache = {}
        else:
            self._cache = {}

    def get(self, query: str) -> Optional[Tuple[str, List[Dict[str, str]]]]:
        """
        Retrieves cached (answer, citations) for a normalized query string.
        Uses strict exact-match only so that novel queries always flow through
        the real RAG retrieval + Groq generation pipeline.
        """
        clean_q = query.strip().lower()
        # Exact match only — no fuzzy substring matching
        entry = self._cache.get(clean_q)
        if entry:
            return (entry["answer"], entry.get("citations", []))

        return None

    def set(self, query: str, answer: str, citations: List[Dict[str, str]]) -> None:
        clean_q = query.strip().lower()
        self._cache[clean_q] = {
            "answer": answer,
            "citations": citations,
        }


chat_cache = ChatCache()
