"""
Unit tests for Vernacular Translator.
"""

import pytest
from modules.m4_vernacular.translator import translate_claim


def test_translate_claim_hindi_cached():
    text = (
        "For a principal of ₹100,000 at disclosed rate 12.00% over 12 months with fees of ₹2,000, "
        "the true effective APR is 15.89% with a monthly EMI of ₹8,884.88."
    )
    res = translate_claim(text, "hi")
    assert res.target_language == "hi"
    assert res.is_cached is True
    assert "₹100,000" in res.translated_text
    assert "15.89%" in res.back_translated_text
    assert "₹8,884.88" in res.back_translated_text


def test_translate_claim_marathi_cached():
    text = "Prepayment penalties are prohibited on floating-rate term loans granted to individual borrowers for purposes other than business."
    res = translate_claim(text, "mr")
    assert res.target_language == "mr"
    assert res.is_cached is True
    assert "मुदतपूर्व परतफेड दंड" in res.translated_text
    assert "prepayment penalties" in res.back_translated_text.lower()


def test_translate_unsupported_language_raises():
    with pytest.raises(ValueError, match="Unsupported vernacular language"):
        translate_claim("Some loan text", "fr")
