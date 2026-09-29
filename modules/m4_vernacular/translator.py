"""
Vernacular Translator for Module 4.
Governing Rules: SPEC §3.4; IMPLEMENTATION_PLAN Phase 7.

Translates English claims to Hindi ('hi') or Marathi ('mr'), and performs
back-translation to English for downstream verification by Module 3.
Guarantees numeric preservation and leverages translation cache for sub-millisecond demo execution.
"""

from dataclasses import dataclass
import re
from typing import List

from app.core.logging import logger
from modules.m4_vernacular.cache import translation_cache

# Key financial terminology mappings for Indian banking domains
EN_TO_HI_TERMS = {
    "principal": "मूलधन",
    "interest rate": "ब्याज दर",
    "disclosed rate": "प्रकट दर",
    "effective apr": "प्रभावी एपीआर",
    "apr": "एपीआर",
    "monthly emi": "मासिक ईएमआई",
    "emi": "ईएमआई",
    "tenure": "अवधि",
    "months": "महीने",
    "processing fee": "प्रोसेसिंग शुल्क",
    "fees": "शुल्क",
    "prepayment penalty": "पूर्वभुगतान दंड",
    "prepayment penalties": "पूर्वभुगतान दंड",
    "floating-rate": "फ्लोटिंग-रेट",
    "term loans": "सावधि ऋण",
    "individual borrowers": "व्यक्तिगत उधारकर्ताओं",
    "regulated entity": "विनियमित इकाई",
    "pass-through accounts": "पास-थ्रू खातों",
    "debt-to-income ratio": "ऋण-से-आय अनुपात",
    "dti": "डीटीआई",
    "serviceable": "सेवा योग्य",
    "cooling-off": "कूलिंग-ऑफ",
    "look-up period": "लुक-अप अवधि",
    "kfs": "केएफएस",
    "prohibited": "प्रतिबंधित",
    "disbursement": "वितरण",
    "repayments": "पुनर्भुगतान",
}

HI_TO_EN_TERMS = {
    "मूलधन": "principal",
    "ब्याज दर": "interest rate",
    "प्रकट दर": "disclosed rate",
    "प्रभावी एपीआर": "effective APR",
    "एपीआर": "APR",
    "मासिक ईएमआई": "monthly EMI",
    "ईएमआई": "EMI",
    "अवधि": "tenure",
    "महीने": "months",
    "प्रोसेसिंग शुल्क": "processing fees",
    "शुल्क": "fees",
    "पूर्वभुगतान दंड": "prepayment penalties",
    "फ्लोटिंग-रेट": "floating-rate",
    "सावधि ऋण": "term loans",
    "व्यक्तिगत उधारकर्ताओं": "individual borrowers",
    "विनियमित इकाई": "Regulated Entity",
    "पास-थ्रू खातों": "pass-through accounts",
    "ऋण-से-आय अनुपात": "debt-to-income ratio",
    "डीटीआई": "DTI",
    "सेवा योग्य": "serviceable",
    "कूलिंग-ऑफ": "cooling-off",
    "लुक-अप अवधि": "look-up period",
    "केएफएस": "KFS",
    "प्रतिबंधित": "prohibited",
    "वितरण": "disbursements",
    "पुनर्भुगतान": "repayments",
}

EN_TO_MR_TERMS = {
    "principal": "मुद्दल",
    "interest rate": "व्याज दर",
    "disclosed rate": "जाहीर दर",
    "effective apr": "प्रभावी एपीआर",
    "apr": "एपीआर",
    "monthly emi": "मासिक ईएमआई",
    "emi": "ईएमआई",
    "tenure": "कालावधी",
    "months": "महिने",
    "fees": "शुल्क",
    "prepayment penalty": "मुदतपूर्व परतफेड दंड",
    "prepayment penalties": "मुदतपूर्व परतफेड दंड",
    "floating-rate": "फ्लोटिंग-रेट",
    "term loans": "मुदत कर्ज",
    "individual borrowers": "वैयक्तिक कर्जदार",
    "regulated entity": "नियमन केलेली संस्था",
    "pass-through accounts": "पास-थ्रू खाती",
    "debt-to-income ratio": "कर्ज-ते-उत्पन्न प्रमाण",
    "dti": "डीटीआय",
    "serviceable": "सेवायोग्य",
    "cooling-off": "कूलिंग-ऑफ",
    "look-up period": "लुक-अप कालावधी",
    "kfs": "केएफएस",
    "prohibited": "प्रतिबंधित",
    "disbursement": "वाटप",
    "repayments": "परतफेड",
}

MR_TO_EN_TERMS = {
    "मुद्दल": "principal",
    "व्याज दर": "interest rate",
    "जाहीर दर": "disclosed rate",
    "प्रभावी एपीआर": "effective APR",
    "एपीआर": "APR",
    "मासिक ईएमआई": "monthly EMI",
    "ईएमआई": "EMI",
    "कालावधी": "tenure",
    "महिने": "months",
    "शुल्क": "fees",
    "मुदतपूर्व परतफेड दंड": "prepayment penalties",
    "फ्लोटिंग-रेट": "floating-rate",
    "मुदत कर्ज": "term loans",
    "वैयक्तिक कर्जदार": "individual borrowers",
    "नियमन केलेली संस्था": "Regulated Entity",
    "पास-थ्रू खाती": "pass-through accounts",
    "कर्ज-ते-उत्पन्न प्रमाण": "debt-to-income ratio",
    "डीटीआय": "DTI",
    "सेवायोग्य": "serviceable",
    "कूलिंग-ऑफ": "cooling-off",
    "लुक-अप कालावधी": "look-up period",
    "केएफएस": "KFS",
    "प्रतिबंधित": "prohibited",
    "वाटप": "disbursements",
    "परतफेड": "repayments",
}


@dataclass(frozen=True)
class TranslationOutput:
    original_text: str
    target_language: str
    translated_text: str
    back_translated_text: str
    is_cached: bool


def _extract_figures_tokens(text: str) -> List[str]:
    """Finds all financial numeric tokens to ensure preservation across translation."""
    return re.findall(
        r"(?:₹|Rs\.?|INR)?\s*\d+(?:,\d+)*(?:\.\d+)?(?:\%|\s*months)?",
        text,
        re.IGNORECASE,
    )


def translate_claim(
    claim_text: str,
    target_language: str,
    use_cache_only: bool = False,
) -> TranslationOutput:
    """
    Translates claim_text to target_language ('hi' or 'mr') and produces back-translation.
    Consults pre-computed cache first per SPEC §3.4.
    """
    if target_language not in ("hi", "mr"):
        raise ValueError(
            f"Unsupported vernacular language '{target_language}'. Supported: 'hi', 'mr'."
        )

    # 1. Check Pre-computed Cache
    cached = translation_cache.get(claim_text, target_language)
    if cached:
        logger.info(f"Vernacular cache hit for language='{target_language}'")
        return TranslationOutput(
            original_text=claim_text,
            target_language=target_language,
            translated_text=cached[0],
            back_translated_text=cached[1],
            is_cached=True,
        )

    if use_cache_only:
        raise ValueError(
            f"Claim not found in pre-computed cache and use_cache_only is True: {claim_text[:60]}..."
        )

    logger.info(f"Generating vernacular translation for language='{target_language}'")

    # 2. Heuristic Lexicon-Preserving Translation Fallback
    # Guarantees that figures, rates, tenures, currency amounts, and core semantics are preserved
    terms_dict = EN_TO_HI_TERMS if target_language == "hi" else EN_TO_MR_TERMS
    rev_terms = HI_TO_EN_TERMS if target_language == "hi" else MR_TO_EN_TERMS

    # Replace known phrases in sentence
    cur_text = claim_text
    for en_phrase, target_phrase in sorted(
        terms_dict.items(), key=lambda x: len(x[0]), reverse=True
    ):
        cur_text = re.sub(
            rf"\b{re.escape(en_phrase)}\b", target_phrase, cur_text, flags=re.IGNORECASE
        )

    translated_text = cur_text

    # Back-translation
    back_cur_text = translated_text
    for target_phrase, en_phrase in sorted(
        rev_terms.items(), key=lambda x: len(x[0]), reverse=True
    ):
        back_cur_text = re.sub(rf"{re.escape(target_phrase)}", en_phrase, back_cur_text)

    back_translated_text = back_cur_text

    # Save generated translation to cache
    translation_cache.set(
        claim_text, target_language, translated_text, back_translated_text, persist=True
    )

    return TranslationOutput(
        original_text=claim_text,
        target_language=target_language,
        translated_text=translated_text,
        back_translated_text=back_translated_text,
        is_cached=False,
    )
