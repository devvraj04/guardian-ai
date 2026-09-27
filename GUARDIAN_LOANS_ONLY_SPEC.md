# GUARDIAN — Loans-Only Product & Technical Specification
### Groundedness-Verified Agentic Financial Advocate (Loan Vertical)
**Pivot note:** This supersedes the multi-module (cashflow forecasting + anomaly detection + KFS) design. Cashflow forecasting and transaction anomaly detection are dropped entirely. The project is now a single-domain, document-centric system: everything revolves around one loan, verified from three angles (what the user typed, what the T&C says, what the KFS says), then chattable.

---

## 1. The Idea

A borrower is handed a loan offer. They're told an interest rate, shown a Key Fact Statement (KFS), and given pages of Terms & Conditions (T&C) — and have no independent way to check that these three things actually agree with each other, or that the KFS's own headline number (the effective APR) is calculated correctly. Guardian is a consumer-side tool that closes that gap for one loan at a time:

1. **User enters the loan terms manually** — principal, disclosed interest rate, tenure, fees. Guardian independently recomputes the true effective APR/EMI on the spot, deterministically, with no ML involved in that specific number.
2. **User uploads the full Terms & Conditions document (PDF).** Guardian extracts every clause bearing on cost, tenure, penalties, and prepayment — not just the headline numbers — and keeps it as a structured, versioned record: a complete, searchable history of what this loan's contract actually says.
3. **User uploads the KFS (PDF).** This is the trigger for the full recheck: Guardian recomputes the KFS's own APR figure, and cross-checks the KFS against both the T&C and the user's manual entry. Any of the three disagreeing with either of the other two is surfaced explicitly, not smoothed over.
4. Every AI-generated explanation of the above passes through a **dual groundedness verifier** (semantic entailment against the source documents + independent numeric recomputation) before the user ever sees it as fact.
5. The same verified explanation can be **checked in Hindi or Marathi** (vernacular groundedness) — translate, back-translate, re-verify, so a translation error can't quietly introduce a wrong number or drop a mandated clause.
6. If the user disagrees with a verdict or wants to formally dispute something about the loan, a **grievance classifier** routes their free-text complaint into an RBI-aligned category and logs it for redressal tracking.
7. A **RAG-grounded chatbot**, scoped to that user's own uploaded documents (T&C + KFS) plus the RBI Digital Lending Directions corpus, lets the user just ask — "can they charge me a prepayment fee in month 3?" — instead of reading fine print.
8. **User enters income and expense details** (monthly income, existing EMIs/obligations, monthly expenses). Guardian deterministically computes a debt-to-income view and gives a plain **serviceable / marginal / not-serviceable** verdict for this specific loan — answering the question the borrower actually cares about most: "can I afford this," not just "is this loan's paperwork consistent."

The novel, defensible core is unchanged from the original proposal: **independently verifying both the meaning and the arithmetic of a financial claim**, now applied specifically to the three-way consistency problem (typed terms ↔ T&C ↔ KFS) that a real borrower actually faces.

### 1.1 Goals
- G1: Let a user fully describe one loan (manual entry + two optional document uploads) and get an independently-verified picture of it.
- G2: Detect and clearly surface disagreement between the KFS, the T&C, and the manually entered terms — this is the system's single most useful output.
- G3: Guarantee every AI-generated explanation shown to the user has passed a semantic + numeric dual verification gate.
- G4: Extend that guarantee across a language boundary (Hindi/Marathi) without duplicating verifier logic.
- G5: Let the user ask free-form questions about their own loan, answered only from their own verified documents + the regulatory corpus (never from the model's general knowledge).
- G6: Provide a lightweight grievance/dispute path when the user disagrees with something.
- G7: Given the user's income and expenses, tell them plainly whether they can actually service this loan — not just whether the loan's terms are compliant/consistent.

### 1.2 Non-Goals (explicit — state these honestly in any report)
- No cashflow forecasting, no transaction-level anomaly detection, no multi-loan portfolio view — this is one loan at a time.
- No insurance vertical (explicitly deferred; the architecture is designed so a second domain *could* reuse the same pipeline later, but it is not built now).
- No real bank/lender API integration — all input is user-supplied (typed or uploaded).
- No autonomous action on the user's behalf — Guardian never contacts the lender, disputes, or commits anything without explicit human approval.
- No claim to RBI compliance certification or DPDP certification — this remains an academic verification-technique demonstration, not a compliance product.

### 1.3 Complexity / Innovation Self-Assessment
- **Complexity: ~7/10.** The hard part moved from "train four ML models" to "reliably extract structured fields from unstandardized T&C prose and cross-check them against a standardized KFS and free-typed input" — that's a real NLP/extraction problem, not a rubber-stamp task.
- **Innovation: ~7/10.** The dual semantic+numeric verifier, applied to a three-way document-consistency problem and extended across a language boundary, is still a genuinely uncommon contribution — generic RAG-faithfulness tools (RAGAS, TruLens) don't do the numeric half at all. The chatbot is a UX convenience layer, not where the novelty lives — don't let it dominate the pitch.
- **Scope fit: appropriately sized** for a serious mini/major college project once narrowed to one domain — this is the version to actually build.

---

## 2. Tech Stack

Reuses the Supabase + Groq decisions already made for the original multi-module design; drops everything that was specific to the modules now removed (XGBoost/Prophet for forecasting, Isolation Forest for anomaly detection).

| Layer | Technology | Why |
|---|---|---|
| Language | Python 3.11+ | ML/NLP ecosystem, team baseline |
| API framework | FastAPI | Async, OpenAPI docs, Pydantic v2 validation baked in |
| Database | **Supabase (Postgres 15), hosted online** | ACID Postgres + Auth + Storage on Supabase's managed cloud — no local Postgres to run |
| Auth | **Supabase Auth** | Short-lived JWT + rotated refresh + hashed passwords out of the box |
| Vector store (RAG) | **ChromaDB, self-hosted in a Docker container** | Fully local, zero dependency on the hosted Supabase project for the RAG layer; own its own container in `docker-compose.yml` alongside the FastAPI app; backs both the regulatory-corpus RAG and the per-user document chatbot |
| File storage | **Supabase Storage** | T&C PDFs, KFS PDFs — same auth boundary as everything else |
| ORM | SQLAlchemy 2.0 (async, `asyncpg`) or SQLModel | Parameterized queries only, no raw SQL |
| Schema/migrations | Supabase CLI migrations (`supabase/migrations/*.sql`), applied against the hosted project | RLS policies live next to the schema they protect |
| PDF text extraction | `pdfplumber` (primary) or `PyMuPDF`/`fitz` (fallback for tricky layouts/scanned tables) | Both T&C and KFS are PDFs; need reliable text + table extraction, not just raw text dump |
| Structured field extraction from PDF text | Groq LLM call with a strict Pydantic output schema (`extra="forbid"`), **not free-form generation** | Extraction is itself a claim about the document and must be treated as such — see §3.4 |
| OCR fallback | **PaddleOCR** (only if a KFS/T&C is a scanned image, not machine-readable text) | Some lenders still issue scanned PDFs; PaddleOCR handles mixed English/Devanagari-script scans better than Tesseract for this use case |
| Deterministic recomputation | Pure Python, no ML (`apr_recompute.py`) | FR-level requirement: same inputs → same output, independently unit-testable |
| Serviceability / affordability engine | Pure Python, no ML (`serviceability.py`) — DTI-style ratio calculation | Same "deterministic, independently testable" bar as the APR engine — this number must be as trustworthy as the APR one |
| Semantic verifier (NLI) | RoBERTa-MNLI (`roberta-large-mnli`, official HuggingFace org) | Standard, benchmarked entailment model; CPU-runnable |
| LLM (claim generation + chatbot + extraction assist) | **Groq API** (`llama-3.3-70b-versatile` or `llama-3.1-8b-instant`) | Low latency, no local GPU pressure, swappable via `LLM_PROVIDER` env var |
| Translation (vernacular check) | IndicTrans2 (AI4Bharat), mT5 fallback | Hindi/Marathi, purpose-built for Indian languages |
| Grievance classifier | TF-IDF + logistic regression baseline; BERT upgrade only if time allows | National Consumer Helpline dataset + synthetic RBI-category augmentation |
| RAG chatbot | **ChromaDB** retrieval (per-user document scope + shared RBI corpus, as separate collections) + Groq LLM, answer generation always routed through the same dual verifier before being shown | Keeps the chatbot from being "just another unverified LLM wrapper" — this is what makes it consistent with the rest of the project's thesis |
| Orchestration | LangGraph, or a plain `enum` state machine if LangGraph adds overhead | ingest → extract → consistency-check → generate claim → verify → (vernacular, if requested) → respond |
| Frontend/demo UI | Next.js or Streamlit | Unchanged |
| Containerization | Docker Compose (FastAPI app + ChromaDB container) — Supabase itself is hosted, so it is not one of the containers | One command spins up everything that needs to run locally |
| Rate limiting | `slowapi` | |
| Secrets | `.env` + `python-dotenv`, never committed | |

**Dropped from the original stack** (no longer needed): XGBoost, Prophet, Isolation Forest/autoencoder, torchvision/dark-pattern CNN path, Ollama, Supabase `pgvector` (replaced by ChromaDB).

**Dependency isolation:** same three-file split as before (`requirements.txt` / `requirements-ml.txt` / `requirements-dev.txt`), though the ML file is now lighter — `transformers` (RoBERTa-MNLI, IndicTrans2), `scikit-learn` (grievance baseline), `pdfplumber`/`PyMuPDF`, `paddleocr` + `paddlepaddle`, `chromadb`.

**Demo-dependency posture — updated for hosted Supabase.** With Supabase hosted online, the DB/Auth/Storage layer is a live third-party dependency at demo time, not a local one — this is a knowing, honest trade-off, not an oversight, and it's stated as such in the report per the project's own "state scope honestly" guideline:
- Keep the hosted Supabase project warm in the days before the viva (free-tier projects auto-pause from inactivity).
- ChromaDB runs in a local Docker container, so the RAG/vector layer has **zero** internet dependency regardless of Supabase's status.
- Groq remains the only LLM call; pre-compute and cache the demo's scripted Groq calls (claim generation, field extraction, chatbot answers) exactly as before, so a flaky connection only threatens the Supabase leg, not the LLM leg.
- Keep a recorded backup demo as a fallback, since two live third-party dependencies (Supabase + Groq) is a step up in demo-day risk from the original local-Postgres plan.

---

## 3. Technical Architecture

### 3.1 System Flow

```
┌──────────────────────────────────────────────────────────────────────────┐
│                              CLIENT / DEMO UI                             │
│                     (Next.js or Streamlit front-end)                      │
└───────────────────────────────┬────────────────────────────────────────┘
                                 │ HTTPS + JWT
┌───────────────────────────────▼────────────────────────────────────────┐
│                    API GATEWAY (FastAPI, single entrypoint /api/v1)      │
│         AuthN/AuthZ · rate limiting · request validation · logging       │
└───────────────────────────────┬────────────────────────────────────────┘
                                 │
        ┌────────────────────────┼─────────────────────────┐
        ▼                        ▼                          ▼
┌───────────────┐      ┌──────────────────┐      ┌──────────────────────┐
│ Loan Intake &  │      │ Consistency      │      │  RAG Chatbot          │
│ Document       │─────▶│ Matching Layer   │      │  (per-user doc scope  │
│ Ingestion      │      │ (manual ↔ T&C ↔  │      │   + RBI corpus, via   │
│ (manual entry, │      │  KFS)            │      │   ChromaDB)           │
│  T&C/KFS       │      └────────┬─────────┘      └───────────┬──────────┘
│  upload +      │               │                             │
│  extraction)   │               ▼                             │
└───────┬────────┘      ┌──────────────────┐                   │
        │               │ Deterministic     │                   │
        │               │ Recompute Engine  │                   │
        │               │ (apr_recompute.py)│                   │
        │               └────────┬─────────┘                    │
        │                        │                               │
        ▼                        ▼                               │
┌───────────────┐      ┌─────────────────────────────────────────┐
│ Income/Expense │      │         Claim Generation (Groq LLM)      │
│ Input →        │─────▶│                                           │
│ Serviceability │      └───────────────────┬───────────────────────┘
│ Engine         │                          │                        │
│(serviceability │                          ▼                        │
│    .py)        │      ┌─────────────────────────────────────────┐ │
└───────┬────────┘      │   Dual Groundedness Verifier (Module 3)   │◀┘
        │               │   RoBERTa-MNLI entailment + numeric      │   (chatbot answers route
        └──────────────▶│   recompute                              │    through here too)
                         └───────────────────┬───────────────────────┘
                     ▼
┌─────────────────────────────────────────────┐
│  Vernacular Verification (Hindi/Marathi)       │
│  translate → back-translate → re-verify        │
└───────────────────┬───────────────────────────┘
                     ▼
┌─────────────────────────────────────────────┐
│  Grievance Classification & Redressal          │
│  (only on user-initiated dispute)              │
└───────────────────┬───────────────────────────┘
                     ▼
              Verdict / Answer → User
```

**Design principle (unchanged from the original architecture):** nothing generated by the LLM — whether a KFS verdict, a consistency-mismatch explanation, or a chatbot answer — reaches the user without passing through the verifier first.

### 3.2 Data Model

```
users               — Supabase Auth-backed (hosted project)
loans               — one row per loan the user is tracking
loan_manual_terms    — {loan_id, principal, disclosed_rate, tenure, fees, entered_at}
loan_documents       — {doc_id, loan_id, doc_type: "tnc"|"kfs", storage_path, version, uploaded_at}
extracted_fields     — {doc_id, field_name, extracted_value, confidence, extraction_method}
consistency_checks   — {loan_id, field_name, manual_value, tnc_value, kfs_value, match_status, checked_at}
income_expense_inputs — {loan_id, monthly_income, existing_emis, monthly_expenses, entered_at}
serviceability_results — {loan_id, dti_ratio, disposable_income, verdict: "serviceable"|"marginal"|"not-serviceable", computed_at}
claims               — same shared Claim schema as before, source_module now one of
                        "recompute" | "consistency" | "chatbot" | "serviceability" | "grievance"
verification_results — {claim_id, semantic_verdict, numeric_verdict, final_verdict, error_type}
disputes             — grievance records, {loan_id, category, free_text, status}
chat_sessions / chat_messages — per-user chatbot history, scoped to their own loans
audit_log            — append-only, unchanged from the original design
```

**Embeddings live outside Postgres now:** ChromaDB (its own Docker container, its own persistent volume) holds two kinds of collections — one shared collection for the RBI Digital Lending Directions corpus, and one per-user collection (or one collection with a `user_id`/`loan_id` metadata filter) for each user's own T&C/KFS document chunks. Retrieval queries always pass the requesting user's ID as a metadata filter, mirroring the RLS scoping used on the Postgres side — ChromaDB itself has no built-in row-level security, so this filter is not optional, it's the only thing standing between one user's documents and another's.

Postgres tables (all still hosted on Supabase) get RLS policies for every table above except purely reference tables (mirrors the original security posture — see §3.5).

### 3.3 The Shared Claim Schema (unchanged in shape, updated `source_module` values)

```python
class Claim(BaseModel):
    claim_id: str
    source_module: str            # "recompute" | "consistency" | "chatbot" | "serviceability" | "grievance"
    user_id: str
    loan_id: str
    claim_text: str
    supporting_figures: dict        # {"apr_disclosed": 24.5, "apr_recomputed": None}
    source_record_id: str           # which loan_documents row or manual-entry row this is about
    generated_at: datetime
    verification_status: str        # "pending" | "grounded" | "flagged"
```

### 3.4 Module-by-Module Build Guide

**Module 0 — Loan Intake & Document Ingestion**
- Manual entry form → `loan_manual_terms` row.
- T&C upload → Supabase Storage → `loan_documents` (versioned) → `pdfplumber`/`PyMuPDF` text extraction (**PaddleOCR fallback** if scanned) → clause-level chunking, embedded into ChromaDB for later RAG use.
- KFS upload → same storage/versioning path, plus triggers Module 2 (consistency check) and Module 1 (recompute) immediately on upload.
- **Structured field extraction is itself an unverified LLM output** — the Groq call that pulls `{principal, rate, tenure, fees}` out of raw PDF text is a claim about the document, and gets a confidence score per field (`extracted_fields.confidence`). A low-confidence field is surfaced to the user for confirmation rather than silently trusted — this keeps garbage-in from silently poisoning the numeric verifier downstream.

**Module 1 — Deterministic Recompute Engine**
- `apr_recompute.py`: pure Python, no ML, given principal/tenure/EMI/fees computes the true effective APR via the RBI-mandated reducing-balance method.
- Unit-tested against a hand-computed example before anything else is allowed to call it — this is the single highest-leverage correctness task in the whole codebase, unchanged from the original design's emphasis.
- Called identically whether the input came from manual entry, T&C-extracted fields, or KFS-extracted fields — **one function, three callers, never three implementations.**

**Module 1b — Loan Serviceability / Affordability Engine**
- `serviceability.py`: pure Python, no ML, given the just-computed EMI (from Module 1) plus user-entered `monthly_income`, `existing_emis`, and `monthly_expenses`, computes a debt-to-income (DTI) ratio and disposable income after all obligations.
- Classifies into `serviceable / marginal / not-serviceable` bands against a stated, documented threshold (e.g. total-EMI-to-net-income ratio) — **this threshold is a commonly used lending-industry heuristic, not an RBI-mandated rule, and must be labeled as such in the report** to avoid overstating the system's regulatory grounding (consistent with the project's own honesty requirement).
- Unit-tested against hand-computed examples exactly like `apr_recompute.py` — this number carries as much weight for the user's actual decision as the APR figure does, so it gets the same rigor.
- The natural-language explanation of the verdict ("you can comfortably service this loan" / "this would leave you with ₹X disposable income") is LLM-generated and therefore a `Claim` like any other — it goes through Module 3 before the user sees it, same as everything else. The DTI number itself is deterministic; the sentence describing it is not, and only the sentence needs verifying, not the arithmetic behind it (the arithmetic is already ground truth by construction).

**Module 2 — Consistency Matching Layer**
- For a given loan, compares the same logical field (principal, rate, tenure, fees) across `loan_manual_terms`, T&C-extracted fields, and KFS-extracted fields.
- Numeric fields: direct tolerance-based comparison.
- Prose/clause fields (e.g. prepayment terms) that don't reduce to a single number: semantic-similarity comparison, flagged for human review rather than auto-resolved if the systems disagree on meaning, not just a figure.
- Output: a `consistency_checks` row per field, `match_status ∈ {match, mismatch, missing}`. A mismatch is itself the single most valuable output of the whole system — it's the thing a borrower actually can't detect on their own — so it's surfaced prominently, not buried in a verdict summary.

**Module 3 — Dual Groundedness Verifier** *(the load-bearing module, same design as the original)*
- Semantic check: `(retrieved_source_passage, claim_text)` → RoBERTa-MNLI entailment score.
- Numeric check: extract figures from `claim_text`, recompute via Module 1's function, compare with tolerance.
- Output: `VerificationResult {claim_id, semantic_verdict, numeric_verdict, final_verdict, error_type}`.
- **Every claim from Modules 0/1b/2 and every chatbot answer routes through here** — there is no separate, lighter-weight verification path for chatbot or serviceability output. This is the rule most worth protecting if time runs short.

**Module 4 — Vernacular Verification**
- Translate a verified claim/explanation to Hindi or Marathi (IndicTrans2, mT5 fallback), back-translate, re-run **Module 3's own functions** (imported, never forked) against the original.
- Report Cross-Lingual Numeric Preservation Rate, Semantic Drift Score, Clause-Drop Rate.
- Pre-compute and cache demo-path translations — never run live during the demo.

**Module 5 — Grievance Classification & Redressal**
- TF-IDF + logistic regression baseline on free-text disputes → RBI-aligned category.
- Only triggered on user-initiated dispute (not automatic) — this is a support path, not part of the main verification loop.

**Module 6 — RAG Chatbot**
- Retrieval via ChromaDB, scoped to: (a) that user's own `loan_documents` chunks (metadata-filtered by `user_id`/`loan_id`), (b) the RBI Digital Lending Directions corpus collection. Never retrieves another user's documents — since ChromaDB has no built-in RLS, this scoping is enforced entirely in application code, so it is treated as a security-critical code path, not a convenience filter.
- Every answer is generated as a `Claim` (`source_module="chatbot"`) and passes through Module 3 before being shown — a chatbot that skips the verifier undermines the entire project's thesis, so this is treated with the same seriousness as any other claim path.

### 3.5 Security (carried over unchanged from the original design)

The full S-1 through S-22 requirement set from the original PRD still applies without modification — JWT rotation, server-side row-level auth re-check, strict Pydantic validation, no raw SQL, file-upload MIME/size/scan restrictions (now covering both T&C and KFS uploads), rate limiting, encryption at rest for sensitive fields, no PII/financial figures/JWTs in logs, pinned dependencies, verified-source model weights, and an append-only audit log. The verifier-gate-cannot-be-bypassed rule (S-17/S-18) now covers four claim sources (`recompute`, `consistency`, `serviceability`, `chatbot`, `grievance`) — same enforcement mechanism, same zero-exceptions policy.

**Two additions specific to this revision:**
- **S-12 (TLS)** now matters for a genuinely external hop: hosted Supabase enforces TLS on its own endpoints, so the app's Supabase client connections are covered automatically — but confirm the connection string is `https`/`sslmode=require`, not assumed.
- **New scoping requirement:** because ChromaDB has no built-in row-level security (unlike Supabase's Postgres RLS), every ChromaDB query in the RAG chatbot and retrieval layer **must** pass an explicit `user_id`/`loan_id` metadata filter. Treat a missing filter here with the same severity as S-3's "any endpoint returning another user's data is a Sev-1 bug" — a filter-less ChromaDB query is the vector-store equivalent of that bug.

### 3.6 Data Classification & Privacy

Unchanged in spirit from the original PRD: synthetic/self-constructed test data only for development (real T&C/KFS PDFs used only if genuinely the user's own, for the user's own demo purposes — never a third party's real financial document without consent); bank account numbers masked; loan documents versioned and source-cited in every claim referencing them; audit log append-only.

**One honest caveat introduced by hosting Supabase:** the original PRD's data-residency language ("stays in the project's own PostgreSQL instance") now means "the project's own database on Supabase's managed cloud infrastructure," not a self-hosted server. It's still an access-controlled, project-owned instance — not a third-party analytics SDK or external logging service — but the report should state plainly that the underlying infrastructure is a managed third-party host, consistent with the project's own "state scope honestly" guideline.

### 3.7 Success Metrics

| Metric | Target |
|---|---|
| Consistency-check accuracy (manual vs T&C vs KFS mismatches correctly flagged) | Reported on a constructed test set with known injected mismatches |
| Serviceability verdict accuracy (DTI-band classification) | Reported against hand-computed test cases across income/expense scenarios |
| Groundedness Rate (verified vs. unverified baseline) | ≥15pp improvement |
| Adversarial stress test (subtly-wrong KFS/T&C inputs) | Verifier flags ≥90% |
| Cross-Lingual Numeric Preservation Rate + Clause-Drop Rate | Reported |
| Chatbot groundedness (answers traceable to a retrieved passage) | Reported — this is the chatbot's own credibility metric, don't skip it |
| Grievance classifier F1 | ≥0.80 |
| End-to-end demo | Single command, live, no manual per-machine fixes |

---

## 4. What Changed From the Original Multi-Module Design

| Kept | Dropped | Added |
|---|---|---|
| Dual groundedness verifier (semantic + numeric) | Cashflow & liquidity forecasting (Module 1, old) | Manual-entry-vs-T&C-vs-KFS consistency matching layer |
| Vernacular (Hindi/Marathi) verification | Transaction anomaly detection (Module 3, old) | Full T&C document ingestion + clause-level storage (not just KFS) |
| Grievance classification | Dark-pattern UI detector (Module 7, old — was already stretch/gated) | RAG chatbot scoped to the user's own documents |
| Supabase + Groq stack, security posture, audit logging | Mock UPI/AA transaction-adapter dependency for the core loop | PDF text extraction + OCR fallback pipeline |
| Shared `Claim` schema pattern, verifier-gate-cannot-be-bypassed rule | Multi-domain (insurance) scope | — |

This is a **lateral resizing**, not a shrink: the ML-heavy modules (forecasting, anomaly detection) are gone, but the document-extraction and consistency-matching work that replaces them is comparable in effort, and the chatbot is new surface area. Total build effort is roughly comparable to the original plan; what's different is that it's now concentrated entirely around one coherent user story (one loan, three sources of truth, one verified answer) instead of four independent evidentiary modules feeding a shared verifier.

---

## 5. Revision 2 — Infra Swaps + Serviceability Addition

Three changes on top of §1–4 above:

1. **Supabase is hosted online**, not run locally via `supabase start`. Auth, Storage, and the relational schema now live on Supabase's managed cloud. This trades the original "zero third-party dependency at demo time" NFR for convenience — accepted knowingly, mitigated by keeping the project warm before the viva and by keeping everything else (ChromaDB, cached Groq calls) local (§2 demo-dependency posture).
2. **ChromaDB (self-hosted in Docker) replaces Supabase `pgvector`** as the vector store for both the RBI-corpus RAG and the per-user document chatbot. This keeps the RAG layer fully local regardless of Supabase's status, at the cost of one more container to run and — since ChromaDB has no built-in RLS — an application-level scoping filter that is now a security-critical code path (§3.5).
3. **PaddleOCR replaces `pytesseract`** as the OCR fallback for scanned T&C/KFS PDFs.
4. **New capability: Loan Serviceability / Affordability Assessment (Module 1b).** Given the EMI computed by Module 1 plus user-entered income/expenses/existing obligations, a deterministic function (`serviceability.py`) produces a DTI ratio and a `serviceable / marginal / not-serviceable` verdict. This directly answers G7 and is arguably as useful to a real borrower as the compliance/consistency checks — it's the "should I even take this loan" question, not just "is this loan's paperwork honest."
