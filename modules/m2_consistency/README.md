# Module 2 — Consistency Matching Layer (`m2_consistency`)

The **Consistency Matching Layer** is the multi-source cross-verification engine of GUARDIAN. It performs audit-grade cross-checks across the three primary representations of any loan:
1. **User Manual Terms** (`loan_manual_terms`): What the borrower entered or believes they agreed to.
2. **Contract Terms & Conditions** (`extracted_fields` from `loan_documents` with `doc_type = 'tnc'`): The full legal contract.
3. **Key Fact Statement** (`extracted_fields` from `loan_documents` with `doc_type = 'kfs'`): The regulatory summary sheet mandated by the Reserve Bank of India.

Surfacing discrepancies across these three documents is the single highest-value borrower-facing capability in the system, preventing hidden fees, rate markups, and predatory terms from passing unnoticed.

---

## 1. Comparison Methodologies & Tolerances

### 1.1 Numeric Terms Comparison
Exact string equality fails on real-world financial documents due to rounding conventions and notation variations. Module 2 implements strict absolute and relative tolerances:

| Field Name | Description | Comparison Rule | Tolerance ($\epsilon$) |
|---|---|---|---|
| `principal` | Disclosed principal amount in INR | Relative / Absolute difference | $\le \max(10.0, 0.001 \times P)$ (₹10 or 0.1%) |
| `disclosed_rate` | Annual interest rate percentage | Absolute difference | $\le 0.05\%$ (e.g. 12.0% vs 12.04% matches; 12.10% mismatches) |
| `tenure_months` | Loan tenure in months | Integer equality | $0\text{ months}$ (exact integer match required) |
| `fees` | Upfront charges or processing fee in INR | Relative / Absolute difference | $\le \max(10.0, 0.005 \times F)$ (₹10 or 0.5%) |

### 1.2 Status Determinations
- **`match`**: All available sources report values that fall within tolerance.
- **`mismatch`**: Any two available sources differ beyond tolerance (e.g., KFS declares ₹500 fee, but T&C stipulates ₹3,500 fee).
- **`missing`**: One or more source documents or fields have not been uploaded or extracted.

### 1.3 Prose / Clause Semantic Comparison (`prepayment_clause`)
Prose clauses that cannot be reduced to a scalar number (e.g., prepayment / foreclosure penalties) are evaluated using a hybrid semantic approach:
1. **Semantic Embeddings**: Cosine similarity computed between dense vectors from ChromaDB's `DefaultEmbeddingFunction` (`all-MiniLM-L6-v2`).
2. **Regulatory & Penalty Domain Rules**: Explicit heuristic checks for nil/zero/waiver terms vs. positive percentage penalties (e.g., "3.5% penalty" vs. "Nil foreclosure charges").
3. **Human Review Gate (RULES.md §1)**: Any clause divergence or contradiction sets `match_status = "mismatch"` and `requires_human_review = True`. Disagreements are **never auto-resolved**.

---

## 2. Sacred Verification Gate Integration (RULES.md §1)

Following the Sacred Verification Gate rules:
- The natural-language summary synthesized by the consistency check is emitted as a canonical `Claim` object:
  ```json
  {
    "source_module": "consistency",
    "verification_status": "pending",
    "claim_text": "Critical consistency mismatch detected across loan sources for: fees. Processing fee differs between KFS (500.0) and T&C (3500.0)."
  }
  ```
- This claim is stored in `public.claims` with `verification_status="pending"` and is **never** presented to the user as verified truth until it passes Module 3 (Phase 6).

---

## 3. Database Persistence

Module 2 writes individual comparison rows to `public.consistency_checks`:
```sql
CREATE TABLE public.consistency_checks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    loan_id UUID NOT NULL REFERENCES public.loans(id) ON DELETE CASCADE,
    field_name TEXT NOT NULL,
    manual_value JSONB,
    tnc_value JSONB,
    kfs_value JSONB,
    match_status TEXT NOT NULL CHECK (match_status IN ('match', 'mismatch', 'missing')),
    checked_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);
```
Every invocation is logged to the append-only `public.audit_log` with action `CONSISTENCY_CHECK_PERFORMED`.

---

## 4. Benchmark Performance (`metrics.json`)

Evaluated against `data/test_cases/consistency_test_cases.json`:
- **Detection Accuracy on Injected Mismatches**: 100% (3/3 injected mismatches caught).
- **False Positive Rate**: 0.0%.
- **Human Review Flagging Precision**: 100% on contradictory clauses.
- **Average Latency**: ~2.5ms.
