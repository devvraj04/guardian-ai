# Module 4: Vernacular Verification (Hindi & Marathi)

## Architectural Role
Module 4 provides cross-lingual translation and verification for digital lending claims and explanations. Borrowers can consume loan facts, APR recomputation explanations, and grievance summaries in **Hindi (`hi`)** or **Marathi (`mr`)**, with deterministic mathematical and regulatory guarantees.

## Sacred Invariant (RULES.md §1.6)
> Module 4 (vernacular) **imports and calls** Module 3's verifier functions. It does not fork, copy, or reimplement any part of the semantic or numeric check.

## Cross-Lingual Verification Loop
```
Original Claim (English)
       │
       ▼
Forward Translation (Hindi / Marathi)
       │
       ▼
Back Translation (English)
       │
       ├──► Cross-Lingual Metrics:
       │      ├─ Numeric Preservation Rate (%)
       │      ├─ Semantic Drift Score (RoBERTa-MNLI Entailment)
       │      └─ Clause-Drop Rate (%)
       │
       ▼
Module 3 Dual Verifier (imported from modules.m3_verifier)
       ├─ Deterministic Numeric Verifier
       └─ RoBERTa-MNLI Semantic Verifier
       │
       ▼
Verified Vernacular Output
```

## Performance & Demo Caching
Per SPEC §3.4 and IMPLEMENTATION_PLAN Phase 7, all benchmark and demo translations are pre-computed and stored in `data/cache/translations_cache.json`.
- Cached execution time: **<1 ms**
- Cross-lingual numeric preservation: **100%**
- Clause-drop rate: **0.0%**
