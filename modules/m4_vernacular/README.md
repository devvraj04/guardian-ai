# Module 4: Vernacular Verification (Hindi & Marathi)

## Architectural Role
Module 4 provides cross-lingual translation and verification for digital lending claims and explanations. Borrowers can consume loan facts, APR recomputation explanations, and grievance summaries in **Hindi (`hi`)** or **Marathi (`mr`)**, with deterministic mathematical and regulatory guarantees.

## Sacred Invariant (RULES.md §1.6)
> Module 4 (vernacular) **imports and calls** Module 3's verifier functions. It does not fork, copy, or reimplement any part of the semantic or numeric check.
> **Compute in English, Present in Hindi**: All underlying calculations (APR recompute, amortization, DTI ratios, tolerances) compute strictly in standard English numeric domains. Vernacular translation is strictly a presentation and cross-lingual audit layer.

## Translation Pipeline Hierarchy
1. **Tier 1: Pre-computed Cache** (`data/cache/translations_cache.json`): Instant (<1ms) response for benchmark & demo scenarios (RULES.md §5.5).
2. **Tier 2: IndicTrans2** (`ai4bharat/indictrans2-en-indic-dist-200M`): State-of-the-art neural translation custom-tailored for Indian languages.
3. **Tier 3: Multilingual T5 (mT5) / MarianMT Fallback** (`Helsinki-NLP/opus-mt-en-hi` or `google/mt5-small`): Robust seq2seq neural fallback.
4. **Tier 4: Financial Domain Lexicon**: Deterministic regex-based fallback preserving exact amounts, currency signs, and regulatory terms.

## Cross-Lingual Verification Loop
```
Original Claim / Explanation (English)
       │
       ▼
Forward Translation (IndicTrans2 / mT5 fallback / Cache)
       │ (Hindi / Marathi)
       ▼
Back Translation (English')
       │
       ├──► Cross-Lingual Metrics:
       │      ├─ Numeric Preservation Rate (%) [>=95% required]
       │      ├─ Semantic Drift Score (RoBERTa-MNLI Entailment)
       │      └─ Clause-Drop Rate (%) [<=15% required]
       │
       ▼
Module 3 Dual Verifier (imported from modules.m3_verifier)
       ├─ Deterministic Numeric Verifier
       └─ RoBERTa-MNLI Semantic Verifier
       │
       ▼
Verified Vernacular Output (Presented on UI with bilingual audit trail)
```

## Performance & Demo Caching
Per SPEC §3.4 and IMPLEMENTATION_PLAN Phase 7, all benchmark and demo translations are pre-computed and stored in `data/cache/translations_cache.json`.
- Cached execution time: **<1 ms**
- Cross-lingual numeric preservation: **100%**
- Clause-drop rate: **0.0%**
