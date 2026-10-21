"""
Vernacular Translator for Module 4.
Governing Rules: SPEC §3.4; IMPLEMENTATION_PLAN Phase 7; RULES.md §1.6, §5.5.

Translates English claims and explanations to Hindi ('hi') or Marathi ('mr'), and performs
back-translation to English for downstream verification by Module 3.

Hierarchy:
1. Pre-computed Cache (translations_cache.json) -> <1ms latency for demo/benchmark guarantees
2. IndicTrans2 (AI4Bharat) -> state-of-the-art neural translation for Indian languages
3. mT5 / MarianMT Fallback -> robust multilingual seq2seq fallback
4. Banking Lexicon & Regex Engine -> deterministic offline fallback guaranteeing numeric preservation
"""

from dataclasses import dataclass
import os
import re
from typing import Dict, List, Optional, Tuple

from app.core.logging import logger
from modules.m4_vernacular.cache import translation_cache

# Key financial terminology mappings for Indian banking domains
EN_TO_HI_TERMS: Dict[str, str] = {
    # Full phrases & regulatory terms
    "prepayment penalties are prohibited on floating-rate term loans granted to individual borrowers for purposes other than business": "व्यवसाय के अलावा अन्य उद्देश्यों के लिए व्यक्तिगत उधारकर्ताओं को दिए गए फ्लोटिंग-रेट टर्म लोन पर पूर्वभुगतान दंड (प्रीपेमेंट पेनल्टी) प्रतिबंधित है",
    "prepayment penalties are prohibited on floating-rate term loans": "फ्लोटिंग-रेट टर्म लोन पर पूर्वभुगतान दंड प्रतिबंधित है",
    "all loan disbursements and repayments must be executed directly between the bank account of the borrower and the regulated entity without pass-through accounts": "सभी ऋण वितरण और पुनर्भुगतान पास-थ्रू खातों के बिना सीधे उधारकर्ता के बैंक खाते और विनियमित इकाई (आरई) के बीच निष्पादित किए जाने चाहिए",
    "cooling-off / look-up period": "कूलिंग-ऑफ / लुक-अप अवधि",
    "cooling-off period": "कूलिंग-ऑफ अवधि",
    "look-up period": "लुक-अप अवधि",
    "debt-to-income ratio": "ऋण-से-आय अनुपात",
    "debt-to-income": "ऋण-से-आय",
    "true effective apr": "वास्तविक प्रभावी एपीआर",
    "effective apr": "प्रभावी एपीआर",
    "disclosed interest rate": "प्रकट ब्याज दर",
    "disclosed rate": "प्रकट दर",
    "processing fee": "प्रोसेसिंग शुल्क",
    "processing fees": "प्रोसेसिंग शुल्क",
    "monthly emi": "मासिक ईएमआई",
    "interest rate": "ब्याज दर",
    "term loans": "सावधि ऋण",
    "individual borrowers": "व्यक्तिगत उधारकर्ताओं",
    "regulated entity": "विनियमित इकाई",
    "pass-through accounts": "पास-थ्रू खातों",
    "key fact statement": "मुख्य तथ्य विवरण (केएफएस)",
    "terms & conditions": "नियम और शर्तें",
    "terms and conditions": "नियम और शर्तें",
    "serviceable": "सेवा योग्य",
    "not serviceable": "सेवा योग्य नहीं",
    "principal": "मूलधन",
    "tenure": "अवधि",
    "tenor": "अवधि",
    "months": "महीने",
    "fees": "शुल्क",
    "penalty": "दंड",
    "penalties": "दंड",
    "disbursement": "वितरण",
    "disbursements": "वितरण",
    "repayment": "पुनर्भुगतान",
    "repayments": "पुनर्भुगतान",
    "prohibited": "प्रतिबंधित",
    "kfs": "केएफएस",
    "apr": "एपीआर",
    "emi": "ईएमआई",
    "dti": "डीटीआई",
    "none": "कोई नहीं",
}

HI_TO_EN_TERMS: Dict[str, str] = {
    "व्यवसाय के अलावा अन्य उद्देश्यों के लिए व्यक्तिगत उधारकर्ताओं को दिए गए फ्लोटिंग-रेट टर्म लोन पर पूर्वभुगतान दंड (प्रीपेमेंट पेनल्टी) प्रतिबंधित है": "Prepayment penalties are prohibited on floating-rate term loans granted to individual borrowers for purposes other than business",
    "सभी ऋण वितरण और पुनर्भुगतान पास-थ्रू खातों के बिना सीधे उधारकर्ता के बैंक खाते और विनियमित इकाई (आरई) के बीच निष्पादित किए जाने चाहिए": "All loan disbursements and repayments must be executed directly between the bank account of the borrower and the Regulated Entity without pass-through accounts",
    "मुख्य तथ्य विवरण (केएफएस)": "Key Fact Statement",
    "नियम और शर्तें": "Terms & Conditions",
    "वास्तविक प्रभावी एपीआर": "true effective APR",
    "प्रभावी एपीआर": "effective APR",
    "प्रकट ब्याज दर": "disclosed interest rate",
    "प्रकट दर": "disclosed rate",
    "प्रोसेसिंग शुल्क": "processing fees",
    "मासिक ईएमआई": "monthly EMI",
    "ब्याज दर": "interest rate",
    "सावधि ऋण": "term loans",
    "व्यक्तिगत उधारकर्ताओं": "individual borrowers",
    "विनियमित इकाई": "Regulated Entity",
    "पास-थ्रू खातों": "pass-through accounts",
    "ऋण-से-आय अनुपात": "debt-to-income ratio",
    "ऋण-से-आय": "debt-to-income",
    "कूलिंग-ऑफ / लुक-अप अवधि": "cooling-off / look-up period",
    "कूलिंग-ऑफ अवधि": "cooling-off period",
    "लुक-अप अवधि": "look-up period",
    "पूर्वभुगतान दंड": "prepayment penalties",
    "फ्लोटिंग-रेट": "floating-rate",
    "सेवा योग्य नहीं": "not serviceable",
    "सेवा योग्य": "serviceable",
    "मूलधन": "principal",
    "अवधि": "tenure",
    "महीने": "months",
    "शुल्क": "fees",
    "प्रतिबंधित": "prohibited",
    "वितरण": "disbursements",
    "पुनर्भुगतान": "repayments",
    "केएफएस": "KFS",
    "एपीआर": "APR",
    "ईएमआई": "EMI",
    "डीटीआई": "DTI",
    "कोई नहीं": "None",
}

EN_TO_MR_TERMS: Dict[str, str] = {
    "prepayment penalties are prohibited on floating-rate term loans granted to individual borrowers for purposes other than business": "व्यवसायाव्यतिरिक्त इतर उद्देशांसाठी वैयक्तिक कर्जदारांना दिलेल्या फ्लोटिंग-रेट टर्म कर्जांवर मुदतपूर्व परतफेड दंड (प्रीपेमेंट पेनल्टी) प्रतिबंधित आहे",
    "all loan disbursements and repayments must be executed directly between the bank account of the borrower and the regulated entity without pass-through accounts": "सर्व कर्ज वाटप आणि परतफेड पास-थ्रू खात्यांशिवाय थेट कर्जदाराच्या बँक खात्यात आणि नियमन केलेल्या संस्थेमध्ये (आरई) केली पाहिजे",
    "cooling-off / look-up period": "कूलिंग-ऑफ / लुक-अप कालावधी",
    "cooling-off period": "कूलिंग-ऑफ कालावधी",
    "debt-to-income ratio": "कर्ज-ते-उत्पन्न प्रमाण",
    "effective apr": "प्रभावी एपीआर",
    "disclosed rate": "जाहीर दर",
    "processing fee": "प्रोसेसिंग शुल्क",
    "monthly emi": "मासिक ईएमआई",
    "interest rate": "व्याज दर",
    "term loans": "मुदत कर्ज",
    "individual borrowers": "वैयक्तिक कर्जदार",
    "regulated entity": "नियमन केलेली संस्था",
    "pass-through accounts": "पास-थ्रू खाती",
    "key fact statement": "मुख्य तथ्य विधान (केएफएस)",
    "terms & conditions": "नियम आणि अटी",
    "serviceable": "सेवायोग्य",
    "principal": "मुद्दल",
    "tenure": "कालावधी",
    "months": "महिने",
    "fees": "शुल्क",
    "prepayment penalty": "मुदतपूर्व परतफेड दंड",
    "prepayment penalties": "मुदतपूर्व परतफेड दंड",
    "floating-rate": "फ्लोटिंग-रेट",
    "prohibited": "प्रतिबंधित",
    "disbursement": "वाटप",
    "repayments": "परतफेड",
    "kfs": "केएफएस",
    "apr": "एपीआर",
    "emi": "ईएमआई",
    "dti": "डीटीआय",
}

MR_TO_EN_TERMS: Dict[str, str] = {
    "व्यवसायाव्यतिरिक्त इतर उद्देशांसाठी वैयक्तिक कर्जदारांना दिलेल्या फ्लोटिंग-रेट टर्म कर्जांवर मुदतपूर्व परतफेड दंड (प्रीपेमेंट पेनल्टी) प्रतिबंधित आहे": "Prepayment penalties are prohibited on floating-rate term loans granted to individual borrowers for purposes other than business",
    "सर्व कर्ज वाटप आणि परतफेड पास-थ्रू खात्यांशिवाय थेट कर्जदाराच्या बँक खात्यात आणि नियमन केलेल्या संस्थेमध्ये (आरई) केली पाहिजे": "All loan disbursements and repayments must be executed directly between the borrower's bank account and the Regulated Entity without pass-through accounts",
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
    "कूलिंग-ऑफ / लुक-अप कालावधी": "cooling-off / look-up period",
    "कूलिंग-ऑफ कालावधी": "cooling-off period",
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
    model_used: str = "cache"


# ==============================================================================
# Model Tier 2: IndicTrans2 Neural Translation Loader
# ==============================================================================
class IndicTrans2Manager:
    """
    Lazy loader and translator for AI4Bharat IndicTrans2 models.
    Supports English <-> Hindi ('hin_Deva') and English <-> Marathi ('mar_Deva').
    """

    def __init__(self):
        self._en_to_indic_model = None
        self._en_to_indic_tokenizer = None
        self._indic_to_en_model = None
        self._indic_to_en_tokenizer = None
        self._load_attempted = False
        self._is_available = False

    def _lang_code(self, lang: str) -> str:
        if lang == "hi":
            return "hin_Deva"
        if lang == "mr":
            return "mar_Deva"
        if lang == "en":
            return "eng_Latn"
        return lang

    def _init_models(self):
        if self._load_attempted:
            return
        self._load_attempted = True

        # Only attempt if explicitly requested or weights exist locally to prevent blocking on network download
        allow_download = os.getenv("ENABLE_INDICTRANS2_DOWNLOAD", "0") == "1"
        if not allow_download:
            logger.info(
                "IndicTrans2 live downloads disabled (default for fast execution)."
            )
            return

        try:
            import torch
            from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

            device = "cuda" if torch.cuda.is_available() else "cpu"
            logger.info(f"Attempting IndicTrans2 initialization on device={device}...")

            model_name_en_indic = "ai4bharat/indictrans2-en-indic-dist-200M"
            self._en_to_indic_tokenizer = AutoTokenizer.from_pretrained(
                model_name_en_indic, trust_remote_code=True
            )
            self._en_to_indic_model = AutoModelForSeq2SeqLM.from_pretrained(
                model_name_en_indic, trust_remote_code=True
            ).to(device)

            model_name_indic_en = "ai4bharat/indictrans2-indic-en-dist-200M"
            self._indic_to_en_tokenizer = AutoTokenizer.from_pretrained(
                model_name_indic_en, trust_remote_code=True
            )
            self._indic_to_en_model = AutoModelForSeq2SeqLM.from_pretrained(
                model_name_indic_en, trust_remote_code=True
            ).to(device)

            self._is_available = True
            logger.info("IndicTrans2 models successfully loaded.")
        except Exception as e:
            logger.warning(
                f"IndicTrans2 initialization skipped or failed: {e}. Falling back to mT5 / Lexicon."
            )
            self._is_available = False

    def translate(self, text: str, src_lang: str, tgt_lang: str) -> Optional[str]:
        """Translates text between English and Hindi/Marathi using IndicTrans2."""
        self._init_models()
        if not self._is_available:
            return None

        try:
            import torch

            is_en_to_indic = src_lang == "en"
            tokenizer = (
                self._en_to_indic_tokenizer
                if is_en_to_indic
                else self._indic_to_en_tokenizer
            )
            model = (
                self._en_to_indic_model if is_en_to_indic else self._indic_to_en_model
            )
            if not tokenizer or not model:
                return None

            device = next(model.parameters()).device
            inputs = tokenizer([text], return_tensors="pt", padding=True).to(device)
            with torch.no_grad():
                generated_tokens = model.generate(**inputs, max_length=256, num_beams=4)
            decoded = tokenizer.batch_decode(generated_tokens, skip_special_tokens=True)
            return decoded[0].strip() if decoded else None
        except Exception as e:
            logger.warning(f"IndicTrans2 inference failed: {e}")
            return None


# ==============================================================================
# Model Tier 3: Multilingual T5 (mT5) / MarianMT Translation Fallback
# ==============================================================================
class MT5TranslationManager:
    """
    Lazy loader for mT5 / MarianMT multilingual translation fallback.
    """

    def __init__(self):
        self._en_hi_model = None
        self._en_hi_tokenizer = None
        self._hi_en_model = None
        self._hi_en_tokenizer = None
        self._load_attempted = False
        self._is_available = False

    def _init_models(self):
        if self._load_attempted:
            return
        self._load_attempted = True

        allow_download = os.getenv("ENABLE_MT5_DOWNLOAD", "0") == "1"
        if not allow_download:
            return

        try:
            import torch
            from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

            device = "cuda" if torch.cuda.is_available() else "cpu"
            model_en_hi = "Helsinki-NLP/opus-mt-en-hi"
            self._en_hi_tokenizer = AutoTokenizer.from_pretrained(model_en_hi)
            self._en_hi_model = AutoModelForSeq2SeqLM.from_pretrained(model_en_hi).to(
                device
            )

            model_hi_en = "Helsinki-NLP/opus-mt-hi-en"
            self._hi_en_tokenizer = AutoTokenizer.from_pretrained(model_hi_en)
            self._hi_en_model = AutoModelForSeq2SeqLM.from_pretrained(model_hi_en).to(
                device
            )

            self._is_available = True
            logger.info("mT5/MarianMT translation fallback loaded.")
        except Exception as e:
            logger.warning(f"mT5 translation fallback initialization skipped: {e}")
            self._is_available = False

    def translate(self, text: str, src_lang: str, tgt_lang: str) -> Optional[str]:
        self._init_models()
        if not self._is_available:
            return None

        try:
            import torch

            is_en_to_hi = src_lang == "en" and tgt_lang == "hi"
            is_hi_to_en = src_lang == "hi" and tgt_lang == "en"
            if not (is_en_to_hi or is_hi_to_en):
                return None

            tokenizer = self._en_hi_tokenizer if is_en_to_hi else self._hi_en_tokenizer
            model = self._en_hi_model if is_en_to_hi else self._hi_en_model
            if not tokenizer or not model:
                return None

            device = next(model.parameters()).device
            inputs = tokenizer([text], return_tensors="pt", padding=True).to(device)
            with torch.no_grad():
                generated_tokens = model.generate(**inputs, max_length=256)
            decoded = tokenizer.batch_decode(generated_tokens, skip_special_tokens=True)
            return decoded[0].strip() if decoded else None
        except Exception as e:
            logger.warning(f"mT5 inference failed: {e}")
            return None


# Global singletons for model managers
indictrans2_manager = IndicTrans2Manager()
mt5_manager = MT5TranslationManager()


# ==============================================================================
# Model Tier 4: Financial Domain Lexicon & Numeric-Preserving Heuristic Translator
# ==============================================================================

# Sentence-level pattern translations for Hindi (common pipeline output patterns)
# These produce complete Hindi sentences, not word-for-word substitutions.
_HI_SENTENCE_PATTERNS: List[Tuple[str, str]] = [
    # APR claim pattern
    (
        r"The borrower was disclosed an interest rate of ([\d.]+)%\.\s*Accounting for the (?:INR|₹)\s*([\d,.]+) processing fees?,\s*the true APR is recomputed at ([\d.]+)% with a monthly EMI of (?:INR|₹)\s*([\d,.]+)\.",
        r"उधारकर्ता को \1% की ब्याज दर प्रकट की गई थी। INR \2 प्रोसेसिंग शुल्क को ध्यान में रखते हुए, वास्तविक वार्षिक प्रतिशत दर (एपीआर) \3% के रूप में पुनर्गणित की गई है और मासिक समान मासिक किस्त (ईएमआई) INR \4 है।",
    ),
    # Serviceability claim pattern
    (
        r"Borrower monthly income is (?:INR|₹)\s*([\d,.]+) with total obligations of (?:INR|₹)\s*([\d,.]+)\.\s*Resulting Debt-to-Income \(DTI\) ratio is ([\d.]+)% \(Industry benchmark verdict: ([\w\s-]+)\)\.",
        r"उधारकर्ता की मासिक आय INR \1 है और कुल देनदारियां INR \2 हैं। परिणामी ऋण-से-आय (डीटीआई) अनुपात \3% है (उद्योग मानक निर्णय: __VERDICT__)।",
    ),
    # Discrepancy pattern
    (
        r"Discrepancy detected in ([\w_]+): KFS states '([^']+)' whereas Terms & Conditions state '([^']+)'\.",
        r"__FIELD__ में विसंगति पाई गई: मुख्य तथ्य विवरण (केएफएस) में '\2' दर्ज है जबकि नियम और शर्तों में '\3' दर्ज है।",
    ),
    # Loan analysis completed pattern
    (
        r"Loan analysis completed in ([\d.]+)ms across (\d+) stages\.\s*(?:All loan terms match KFS and meet regulatory standards\.|([\d]+) compliance concern\(s\) flagged\.)",
        r"ऋण विश्लेषण \2 चरणों में \1 मिलीसेकंड में पूरा हुआ। __COMPLIANCE_STATUS__",
    ),
    # Understated APR pattern
    (
        r"Understated APR: True APR is ([\d.]+)% vs disclosed ([\d.]+)%\.",
        r"कम दर्शाई गई वार्षिक प्रतिशत दर (एपीआर): वास्तविक एपीआर \1% है जबकि प्रकट दर \2% है।",
    ),
    # High DTI warning pattern
    (
        r"High DTI warning: ([\d.]+)% indicates loan is not serviceable under industry heuristics\.",
        r"उच्च डीटीआई चेतावनी: \1% इंगित करता है कि उद्योग मानक के अनुसार ऋण सेवा योग्य नहीं है।",
    ),
    # Consistency check incomplete pattern
    (
        r"Consistency check incomplete due to missing documents or unextracted fields:(.+)\.",
        r"गायब दस्तावेजों या अनिष्कर्षित क्षेत्रों के कारण संगतता जांच अपूर्ण है:\1।",
    ),
    # Consistency check detected pattern
    (
        r"Consistency check detected (\d+) discrepancy\(ies\) across loan sources\.",
        r"संगतता जांच में ऋण स्रोतों में \1 विसंगतियां पाई गईं।",
    ),
    # Critical consistency mismatch pattern
    (
        r"Critical consistency mismatch detected across loan sources for:(.+)\.\s*Manual human review is required due to contradictory or divergent contractual terms\.",
        r"ऋण स्रोतों में गंभीर संगतता विसंगति पाई गई:\1। विरोधाभासी या भिन्न अनुबंध शर्तों के कारण मैनुअल मानव समीक्षा आवश्यक है।",
    ),
    # All loan terms match pattern
    (
        r"All loan terms match KFS and meet regulatory standards\.",
        r"सभी ऋण शर्तें मुख्य तथ्य विवरण (केएफएस) से मेल खाती हैं और नियामक मानकों को पूरा करती हैं।",
    ),
    # All loan terms agree pattern
    (
        r"All loan terms \(principal, interest rate, tenure, fees, and prepayment clauses\) agree consistently across manual entry, T&C, and KFS documents within acceptable tolerances\.",
        r"स्वीकार्य सहनशीलता सीमा के भीतर मैनुअल प्रविष्टि, नियम और शर्तें (टीएंडसी), और मुख्य तथ्य विवरण (केएफएस) दस्तावेजों में सभी ऋण शर्तें (मूलधन, ब्याज दर, अवधि, शुल्क और पूर्वभुगतान खंड) लगातार सुसंगत हैं।",
    ),
    # KFS shall disclose cooling-off pattern
    (
        r"The KFS shall clearly disclose cooling-off / look-up period during which the borrower can exit the loan without penalty\.",
        r"मुख्य तथ्य विवरण (केएफएस) में कूलिंग-ऑफ / लुक-अप अवधि का स्पष्ट रूप से खुलासा किया जाएगा जिसके दौरान उधारकर्ता बिना किसी दंड के ऋण से बाहर निकल सकता है।",
    ),
]

# Verdict translations for Hindi
_HI_VERDICT_MAP: Dict[str, str] = {
    "serviceable": "सेवा योग्य",
    "not-serviceable": "सेवा योग्य नहीं",
    "not serviceable": "सेवा योग्य नहीं",
    "marginal": "सीमांत",
}

# Field name translations for Hindi discrepancy patterns
_HI_FIELD_MAP: Dict[str, str] = {
    "principal": "मूलधन",
    "disclosed_rate": "प्रकट ब्याज दर",
    "tenure_months": "अवधि (महीनों)",
    "fees": "शुल्क",
    "prepayment_clause": "पूर्वभुगतान खंड",
    "interest_rate": "ब्याज दर",
}


def _translate_via_lexicon(text: str, target_language: str) -> str:
    """Translates text from English to Hindi/Marathi while ensuring 100% preservation of figures and symbols.

    Uses sentence-level regex pattern matching first for complete Hindi output,
    then falls back to term-by-term substitution only if no pattern matches.
    """
    # 1. Try sentence-level patterns first (Hindi only for now)
    if target_language == "hi":
        for pattern, replacement in _HI_SENTENCE_PATTERNS:
            m = re.match(pattern, text.strip(), re.IGNORECASE | re.DOTALL)
            if m:
                result = re.sub(
                    pattern, replacement, text.strip(), flags=re.IGNORECASE | re.DOTALL
                )

                # Post-process verdict placeholders
                if "__VERDICT__" in result:
                    orig_match = re.search(
                        r"Industry benchmark verdict: ([\w\s-]+)\)", text, re.IGNORECASE
                    )
                    if orig_match:
                        verdict_en = orig_match.group(1).strip().lower()
                        verdict_hi = _HI_VERDICT_MAP.get(verdict_en, verdict_en)
                        result = result.replace("__VERDICT__", verdict_hi)

                # Post-process field name placeholders
                if "__FIELD__" in result:
                    field_match = re.search(
                        r"Discrepancy detected in ([\w_]+):", text, re.IGNORECASE
                    )
                    if field_match:
                        field_en = field_match.group(1).strip().lower()
                        field_hi = _HI_FIELD_MAP.get(field_en, field_en)
                        result = result.replace("__FIELD__", field_hi)

                # Post-process compliance status placeholder
                if "__COMPLIANCE_STATUS__" in result:
                    if "All loan terms match KFS" in text:
                        result = result.replace(
                            "__COMPLIANCE_STATUS__",
                            "सभी ऋण शर्तें केएफएस से मेल खाती हैं और नियामक मानकों को पूरा करती हैं।",
                        )
                    else:
                        count_match = re.search(
                            r"(\d+) compliance concern", text, re.IGNORECASE
                        )
                        count = count_match.group(1) if count_match else "0"
                        result = result.replace(
                            "__COMPLIANCE_STATUS__",
                            f"{count} अनुपालन चिंता(एं) चिह्नित की गईं।",
                        )

                return result

    # 2. Fallback: term-by-term substitution
    terms_dict = EN_TO_HI_TERMS if target_language == "hi" else EN_TO_MR_TERMS
    cur_text = text

    # Sort phrases longest-first so longer compound phrases match before individual words
    for en_phrase, target_phrase in sorted(
        terms_dict.items(), key=lambda x: len(x[0]), reverse=True
    ):
        cur_text = re.sub(
            rf"\b{re.escape(en_phrase)}\b", target_phrase, cur_text, flags=re.IGNORECASE
        )
    return cur_text


def _back_translate_via_lexicon(text: str, source_language: str) -> str:
    """Back-translates text from Hindi/Marathi to English for Module 3 verification."""
    rev_terms = HI_TO_EN_TERMS if source_language == "hi" else MR_TO_EN_TERMS
    back_cur_text = text

    for target_phrase, en_phrase in sorted(
        rev_terms.items(), key=lambda x: len(x[0]), reverse=True
    ):
        back_cur_text = re.sub(rf"{re.escape(target_phrase)}", en_phrase, back_cur_text)
    return back_cur_text


def _extract_figures_tokens(text: str) -> List[str]:
    """Finds all financial numeric tokens to ensure preservation across translation."""
    return re.findall(
        r"(?:₹|Rs\.?|INR)?\s*\d+(?:,\d+)*(?:\.\d+)?(?:\%|\s*months)?",
        text,
        re.IGNORECASE,
    )


# ==============================================================================
# Public API
# ==============================================================================
def translate_text(
    text: str,
    target_language: str,
    use_cache_only: bool = False,
) -> TranslationOutput:
    """
    Tiered translation pipeline:
    1. Pre-computed cache lookup
    2. IndicTrans2 neural translation
    3. mT5 / MarianMT translation fallback
    4. Financial Lexicon & Regex engine
    """
    if target_language not in ("hi", "mr"):
        raise ValueError(
            f"Unsupported vernacular language '{target_language}'. Supported: 'hi', 'mr'."
        )

    clean_text = text.strip()

    # 1. Check Pre-computed Cache (SPEC §3.4, RULES.md §5.5)
    cached = translation_cache.get(clean_text, target_language)
    if cached:
        logger.info(f"Vernacular cache hit for language='{target_language}'")
        return TranslationOutput(
            original_text=clean_text,
            target_language=target_language,
            translated_text=cached[0],
            back_translated_text=cached[1],
            is_cached=True,
            model_used="cache",
        )

    if use_cache_only:
        raise ValueError(
            f"Text not found in pre-computed cache and use_cache_only is True: {clean_text[:60]}..."
        )

    logger.info(
        f"Executing tiered vernacular translation for language='{target_language}'"
    )

    model_used = "lexicon_fallback"
    translated_text: Optional[str] = None
    back_translated_text: Optional[str] = None

    # 2. Try IndicTrans2
    translated_text = indictrans2_manager.translate(
        clean_text, src_lang="en", tgt_lang=target_language
    )
    if translated_text:
        model_used = "indictrans2"
        back_translated_text = indictrans2_manager.translate(
            translated_text, src_lang=target_language, tgt_lang="en"
        )

    # 3. Try mT5 if IndicTrans2 returned None
    if not translated_text:
        translated_text = mt5_manager.translate(
            clean_text, src_lang="en", tgt_lang=target_language
        )
        if translated_text:
            model_used = "mt5_fallback"
            back_translated_text = mt5_manager.translate(
                translated_text, src_lang=target_language, tgt_lang="en"
            )

    # 4. Fallback to Financial Lexicon Engine
    if not translated_text:
        model_used = "lexicon_fallback"
        translated_text = _translate_via_lexicon(clean_text, target_language)

    if not back_translated_text:
        back_translated_text = _back_translate_via_lexicon(
            translated_text, target_language
        )

    # 5. Persist to cache
    translation_cache.set(
        clean_text, target_language, translated_text, back_translated_text, persist=True
    )

    return TranslationOutput(
        original_text=clean_text,
        target_language=target_language,
        translated_text=translated_text,
        back_translated_text=back_translated_text,
        is_cached=False,
        model_used=model_used,
    )


def translate_claim(
    claim_text: str,
    target_language: str,
    use_cache_only: bool = False,
) -> TranslationOutput:
    """
    Translates claim_text to target_language ('hi' or 'mr') and produces back-translation.
    """
    return translate_text(
        text=claim_text,
        target_language=target_language,
        use_cache_only=use_cache_only,
    )
