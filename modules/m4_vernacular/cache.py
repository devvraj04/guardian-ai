"""
Translation Cache Manager for Module 4 (Vernacular).
Governing Rules: SPEC §3.4; IMPLEMENTATION_PLAN Phase 7.

Ensures that demo translations and frequently used claims return immediately
without invoking heavy live translation pipelines during demo/presentation.
"""

import json
from pathlib import Path
from typing import Dict, Optional, Tuple

CACHE_FILE_PATH = (
    Path(__file__).resolve().parents[2] / "data" / "cache" / "translations_cache.json"
)


class TranslationCache:
    """Manages persistent and in-memory cache of vernacular translations."""

    def __init__(self, cache_file: Optional[Path] = None):
        self.cache_file = cache_file or CACHE_FILE_PATH
        self._cache: Dict[str, Dict[str, Dict[str, str]]] = {}
        self.load()

    def load(self) -> None:
        """Loads cached translations from disk."""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    self._cache = json.load(f)
            except Exception:
                self._cache = {}
        else:
            self._cache = {}

    def save(self) -> None:
        """Persists memory cache to disk."""
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.cache_file, "w", encoding="utf-8") as f:
            json.dump(self._cache, f, indent=2, ensure_ascii=False)

    def get(self, text: str, target_lang: str) -> Optional[Tuple[str, str]]:
        """
        Retrieves (translated_text, back_translated_text) for a given English text
        and target language ('hi' or 'mr'). Returns None if not cached.
        """
        clean_text = text.strip()
        lang_data = self._cache.get(clean_text)
        if not lang_data:
            return None
        target_entry = lang_data.get(target_lang)
        if not target_entry:
            return None
        return (
            target_entry.get("translated", ""),
            target_entry.get("back_translated", ""),
        )

    def set(
        self,
        text: str,
        target_lang: str,
        translated: str,
        back_translated: str,
        persist: bool = True,
    ) -> None:
        """Stores a translation pair in cache."""
        clean_text = text.strip()
        if clean_text not in self._cache:
            self._cache[clean_text] = {}
        self._cache[clean_text][target_lang] = {
            "translated": translated,
            "back_translated": back_translated,
        }
        if persist:
            self.save()


# Singleton instance
translation_cache = TranslationCache()
