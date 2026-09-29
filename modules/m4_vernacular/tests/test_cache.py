"""
Unit tests for Vernacular Translation Cache (SPEC §3.4).
"""

from pathlib import Path
import tempfile
from modules.m4_vernacular.cache import TranslationCache


def test_cache_set_and_get():
    with tempfile.TemporaryDirectory() as tmpdir:
        cache_path = Path(tmpdir) / "test_cache.json"
        cache = TranslationCache(cache_file=cache_path)

        # Cache miss
        assert cache.get("Test claim text", "hi") is None

        # Set entry
        cache.set(
            "Test claim text",
            "hi",
            translated="परीक्षण दावा पाठ",
            back_translated="Test claim text",
            persist=True,
        )

        # Cache hit
        hit = cache.get("Test claim text", "hi")
        assert hit is not None
        assert hit[0] == "परीक्षण दावा पाठ"
        assert hit[1] == "Test claim text"

        # Reload from disk
        new_cache = TranslationCache(cache_file=cache_path)
        reload_hit = new_cache.get("Test claim text", "hi")
        assert reload_hit is not None
        assert reload_hit[0] == "परीक्षण दावा पाठ"
