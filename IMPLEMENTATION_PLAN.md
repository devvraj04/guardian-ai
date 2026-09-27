# GUARDIAN — Implementation Plan (Loans-Only, Revision 2)

Companion to `GUARDIAN_LOANS_ONLY_SPEC.md` (the idea/stack/architecture) and `RULES.md` (the non-negotiable rules — read that first, nothing here overrides it). This plan reflects the final architecture: hosted Supabase, ChromaDB in Docker, PaddleOCR fallback, and the added Loan Serviceability module.

---

## 0. Repo Skeleton

```
guardian/
├── app/
│   ├── main.py                       # FastAPI entrypoint, single gateway at /api/v1
│   ├── schemas/
│   │   └── claim.py                    # THE Claim schema — single source of truth
│   ├── deps/
│   │   └── auth.py                      # get_current_user dependency (server-side row-level check)
│   ├── routers/                         # one file per endpoint group (loans, documents, serviceability, chat, disputes)
│   ├── orchestration/
│   │   └── pipeline.py                  # state machine — the verifier choke point
│   └── core/
│       ├── config.py                     # env var loading (hosted Supabase creds, Groq key, Chroma host)
│       └── logging.py                     # request-ID-only logging
├── modules/
│   ├── m0_intake/                        # manual entry + T&C/KFS upload + extraction
│   │   ├── extraction.py                  # Groq-assisted structured field extraction, Pydantic-validated
│   │   └── ocr_fallback.py                 # PaddleOCR path for scanned documents
│   ├── m1_recompute/
│   │   └── apr_recompute.py                # THE numeric-truth function — imported, never copied
│   ├── m1b_serviceability/
│   │   └── serviceability.py                # DTI / affordability engine — deterministic, imported everywhere it's needed
│   ├── m2_consistency/                     # manual vs T&C vs KFS field matching
│   ├── m3_verifier/                        # semantic (RoBERTa-MNLI) + numeric check
│   ├── m4_vernacular/                      # imports m3's functions, does not fork them
│   ├── m5_grievance/                       # TF-IDF/logistic regression classifier
│   └── m6_chatbot/                         # RAG retrieval (ChromaDB) + Groq generation, routes through m3
├── rag/
│   ├── chroma_client.py                    # single place ChromaDB connections are made
│   ├── ingest_rbi_corpus.py                 # one-time/periodic ingestion of RBI Digital Lending Directions
│   └── ingest_user_docs.py                  # per-upload chunking + embedding of a user's T&C/KFS
├── supabase/
│   └── migrations/                         # SQL migrations incl. RLS policies, applied against the hosted project
├── data/
│   ├── fixtures/                           # mocked Claim objects so downstream modules can start early
│   ├── test_cases/                          # hand-computed APR/EMI/DTI examples, adversarial KFS inputs
├── tests/                                   # or per-module tests/ folders
├── docker-compose.yml                        # app + chromadb only (Supabase is hosted, not a container)
├── .env.example
├── requirements.txt
├── requirements-ml.txt
├── requirements-dev.txt
├── RULES.md
├── GUARDIAN_LOANS_ONLY_SPEC.md
└── STATUS.md
```

Each `modules/m*/` folder gets its own `tests/`, `metrics.json`, `README.md` — non-negotiable per module (RULES.md §3.3).

---

## Phase 0 — Environment & Foundations (Week 1)

**Goal:** every teammate can run `docker compose up` and hit a live, empty API backed by the hosted Supabase project and a local ChromaDB.

1. Create the **hosted Supabase project** (one shared project for the team, not per-teammate). Record the project's URL, anon key, and service-role key.
2. Install Docker + Docker Compose, Python 3.11+, Git with branch protection on `main`.
3. Write `docker-compose.yml` with two services: the FastAPI app, and a `chromadb/chroma` container with a persistent named volume.
4. Write `.env.example` with dummy values for: `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `DATABASE_URL` (hosted connection string), `JWT_JWKS_URL`, `JWT_AUDIENCE`, `GROQ_API_KEY`, `GROQ_MODEL`, `LLM_PROVIDER`, `CHROMA_HOST`, `CHROMA_PORT`, `HF_HOME`, `RATE_LIMIT_*`. Real `.env` is gitignored from the first commit.
5. `.gitignore`: `.env`, model weight caches, `/data/raw`, `/data/processed`, Chroma's local persistence directory if not using the container volume.
6. Write and pin the three requirements files. `requirements-ml.txt` now includes `transformers`, `scikit-learn`, `pdfplumber`/`PyMuPDF`, `paddleocr` + `paddlepaddle`, `chromadb`. Confirm all three install cleanly, in order, on every teammate's machine.
7. Install `pre-commit` with `detect-secrets`; confirm clean on the repo.
8. Write Supabase SQL migrations (applied against the **hosted** project via `supabase db push` or the CLI's remote migration flow) for: `users` (Auth-backed), `loans`, `loan_manual_terms`, `loan_documents`, `extracted_fields`, `consistency_checks`, `income_expense_inputs`, `serviceability_results`, `claims`, `verification_results`, `disputes`, `chat_sessions`, `chat_messages`, `audit_log`.
9. Write an RLS policy for every table above except purely reference tables. Confirm the policy list matches the table list.
10. Finalize the `Claim` Pydantic schema in `app/schemas/claim.py` with `source_module ∈ {"recompute", "consistency", "serviceability", "chatbot", "grievance"}` — this is the one and only definition in the repo.
11. Confirm the ChromaDB container is reachable from the FastAPI container over the Docker network; create two collections: `rbi_corpus` and `user_documents` (the latter using per-record metadata for `user_id`/`loan_id` scoping — see Phase 3).
12. Download the RBI Digital Lending Directions, 2025 text (for the RAG corpus).

**Gate to move on:** `docker compose up` brings up the app + ChromaDB with no manual per-machine fixes; the app can read/write the hosted Supabase project; a health-check endpoint confirms both connections are live.

---

## Phase 1 — Loan Intake & Document Ingestion (Module 0) (Weeks 2–3)

1. **Manual entry:** `POST /loans` + `POST /loans/{id}/terms` → writes `loan_manual_terms`.
2. **T&C upload:**
   - File goes to Supabase Storage (S-8: MIME type + size limit enforced, scanned before processing).
   - `loan_documents` row created, versioned.
   - Text extraction: `pdfplumber` primary, `PyMuPDF` fallback for tricky layouts. If the extracted text is empty/garbage (scanned image), fall back to **PaddleOCR**.
   - Clause-level chunking, embedded and upserted into the `user_documents` ChromaDB collection with `metadata={"user_id":..., "loan_id":..., "doc_type":"tnc"}`.
3. **KFS upload:** same storage/versioning/extraction/OCR-fallback/chunking path, `doc_type="kfs"`. This upload is the explicit trigger for Phase 4 (recompute) and Phase 5 (consistency check) — wire this as an event, not something the user has to separately request.
4. **Structured field extraction:** a Groq LLM call, constrained to a strict Pydantic schema (`extra="forbid"`) pulling `{principal, disclosed_rate, tenure, fees}` out of the raw extracted text — one call for T&C, one for KFS. Each field gets a `confidence` score in `extracted_fields`. **A low-confidence field is surfaced to the user for manual confirmation, not silently trusted** — write this check before anything downstream consumes `extracted_fields`.
5. Consent/audit: log the upload and extraction actions to `audit_log`.

**Gate to move on:** a user can create a loan, enter terms manually, upload a T&C and a KFS, and see extracted fields (with confidence scores) stored and queryable — with `tests/`, `metrics.json` (extraction accuracy on a hand-labeled sample), and `README.md`.

---

## Phase 2 — Deterministic Engines: APR Recompute + Serviceability (Weeks 3–4)

### Module 1 — `apr_recompute.py`
- Pure Python, no ML. Given principal, tenure, EMI, disclosed fees → computes the true effective APR (reducing-balance method).
- **Unit-test against a hand-computed example before anything else is allowed to call it** (RULES.md §3.4) — this is the highest-leverage correctness task in the project.
- Same function is called for manual-entry input, T&C-extracted fields, and KFS-extracted fields. One function, three callers.

### Module 1b — `serviceability.py`
- Pure Python, no ML. Inputs: the EMI just computed by Module 1, plus `monthly_income`, `existing_emis`, `monthly_expenses` from `income_expense_inputs`.
- Computes: `dti_ratio = (existing_emis + new_emi) / monthly_income`, `disposable_income = monthly_income − monthly_expenses − existing_emis − new_emi`.
- Classifies into `serviceable / marginal / not-serviceable` against a documented, stated threshold — **label this explicitly as an industry heuristic, not an RBI mandate**, in both the code comments and the report.
- Unit-test against hand-computed examples across a few income/expense scenarios, same rigor as Module 1.
- The verdict's natural-language explanation (LLM-generated) is a `Claim` with `source_module="serviceability"` — it goes through Module 3 (Phase 6) before the user sees it. The DTI arithmetic itself does not need re-verification (it's deterministic by construction); only the sentence describing it does.

**Gate to move on:** both functions pass their hand-computed unit tests; `POST /kfs/verify` and a new `POST /loans/{id}/serviceability` endpoint both return correct numbers on test fixtures; each module has `tests/`, `metrics.json`, `README.md`.

---

## Phase 3 — Consistency Matching Layer (Module 2) (Week 5)

1. For a given loan, compare the same logical field (principal, rate, tenure, fees) across `loan_manual_terms`, T&C `extracted_fields`, and KFS `extracted_fields`.
2. Numeric fields: tolerance-based comparison → `consistency_checks` row, `match_status ∈ {match, mismatch, missing}`.
3. Prose/clause fields that don't reduce to a number (e.g. prepayment terms): semantic-similarity comparison between the T&C clause and the KFS's corresponding statement; a disagreement is flagged for human review, not auto-resolved.
4. Surface mismatches prominently in the API response and UI — this is the system's single most useful output, not a footnote.

**Gate to move on:** a constructed test set with known injected mismatches (e.g. T&C says 2% prepayment fee, KFS omits it) is correctly flagged; `tests/`, `metrics.json`, `README.md` present.

---

## Phase 4 — RAG Layer: RBI Corpus Ingestion (Week 6)

1. Chunk and embed the RBI Digital Lending Directions, 2025 into the `rbi_corpus` ChromaDB collection.
2. Confirm retrieval returns relevant passages for ≥90% of a sample claim set (same acceptance bar as the original architecture's roadmap gate).
3. This is a prerequisite for Module 3's semantic check (Phase 6) — do not start Phase 6 before this gate passes.

---

## Phase 5 — Vector Store Security Hardening (Week 6, parallel with Phase 4)

Because ChromaDB has no built-in row-level security (unlike Supabase Postgres RLS), this gets its own explicit build step rather than being folded silently into Phase 1:

1. Every query against `user_documents` **must** pass an explicit `where={"user_id": ..., "loan_id": ...}` metadata filter. Write a single wrapper function in `rag/chroma_client.py` that all retrieval code is forced to go through — never call the raw ChromaDB client directly from module code.
2. Write a test that attempts to retrieve user A's documents while authenticated as user B and asserts zero results.
3. Treat a missing or bypassable filter here with the same severity as "an endpoint returning another user's data" (RULES.md §2.1) — a Sev-1-class bug, fixed before any other work continues.

**Gate to move on:** the cross-user retrieval test passes; the wrapper function is the only code path that touches ChromaDB for user documents (verified by grep, same discipline as the verifier-gate check).

---

## Phase 6 — Dual Groundedness Verifier (Module 3) (Weeks 7–8) — highest-risk module

1. **Semantic check:** `(retrieved_source_passage, claim_text)` → RoBERTa-MNLI (`roberta-large-mnli`) entailment score; below threshold → flagged. Retrieval pulls from both `rbi_corpus` and the claim's own source document in `user_documents` (via the Phase 5 wrapper).
2. **Numeric check:** extract figures from `claim_text` (regex + ₹/%/date parser); recompute via **Module 1's or Module 1b's function**, imported not reimplemented; compare with tolerance.
3. Output exactly: `VerificationResult {claim_id, semantic_verdict, numeric_verdict, final_verdict, error_type}`.
4. Wire into the orchestration layer as the hard gate: grep-confirm no response path returns `claim_text` without a preceding verifier call. No debug flag or shortcut skips this, anywhere (RULES.md §1).
5. **Adversarial test:** 10–15 manually constructed subtly-wrong KFS/T&C inputs; verifier must catch ≥90%.
6. Compute Groundedness Rate on real claims; target ≥15pp improvement over an unverified baseline.

**Risk mitigation if this slips:** keep the numeric-check half fully working standalone even if the NLI half lags.

---

## Phase 7 — Vernacular Verification (Module 4) (Week 9) — cheap once Module 3 exists

1. Translate a verified claim/explanation to Hindi or Marathi (IndicTrans2, mT5 fallback), back-translate to English.
2. Re-run **Module 3's own functions** (imported, not reimplemented) on the back-translated text against the original.
3. Report Cross-Lingual Numeric Preservation Rate, Semantic Drift Score, Clause-Drop Rate.
4. **Pre-compute and cache all translations used in the demo path — never run live translation during the demo.**

---

## Phase 8 — Grievance Classification & Redressal (Module 5) (Week 9, parallel with Phase 7)

1. TF-IDF + logistic regression baseline on National Consumer Helpline data + synthetic RBI-category augmentation; BERT upgrade only if time allows.
2. Only triggered on user-initiated dispute — a support path, not part of the main verification loop.
3. `POST /disputes` → classify → store in `disputes`, status trackable.

---

## Phase 9 — RAG Chatbot (Module 6) (Week 10)

1. Retrieval: query `user_documents` (scoped via the Phase 5 wrapper) and `rbi_corpus`, merge top-k passages.
2. Groq generates an answer grounded in the retrieved passages.
3. Every answer is emitted as a `Claim` (`source_module="chatbot"`) and **passes through Module 3 before being shown** — no separate, lighter-weight path for chatbot output.
4. Report chatbot groundedness (answers traceable to a retrieved passage) as its own metric.

---

## Phase 10 — Orchestration & API (Week 11)

1. Build the state machine (LangGraph or plain `enum`) coordinating: ingest → extract → consistency-check → recompute/serviceability → generate claim → retrieve → verify → (vernacular, if requested) → respond.
2. Implement every endpoint (loans, documents, terms, serviceability, verify, chat, disputes, audit) behind the single FastAPI gateway at `/api/v1`, each with the JWT + server-side self-only check.
3. Every endpoint returns `{error_code, message, request_id}` on error, never a raw stack trace outside localhost.
4. Confirm end-to-end round trip ≤5 seconds on the reference test loan.

---

## Phase 11 — Report & Demo Rehearsal (Week 12)

1. Confirm the full pipeline runs live via `docker compose up` (app + ChromaDB) against the hosted Supabase project, with no teammate-laptop-specific fix.
2. Keep the hosted Supabase project warm in the days before the viva (free-tier auto-pause risk).
3. Confirm the demo's scripted Groq calls (extraction, claim generation, chatbot answers) are pre-computed and cached; keep a recorded backup demo given two live third-party dependencies (Supabase + Groq).
4. Report explicitly states: synthetic/self-constructed test documents, the hosted-Supabase infrastructure caveat, the industry-heuristic (not RBI-mandated) nature of the serviceability threshold, and the "not RBI-compliant / not DPDP-certified" disclaimer.
5. Rehearse against the actual reference loan + documents, not a happy-path-only script — specifically rehearse a mismatch case (T&C vs KFS disagreement) and a not-serviceable case, since those are the system's most persuasive outputs in a viva.

---

## Milestone Gate Table (quick reference)

| Week | Deliverable | Gate to move on |
|---|---|---|
| 1 | Hosted Supabase project + ChromaDB container + schema/RLS + `Claim` schema locked | `docker compose up` works for every teammate against the hosted project |
| 2–3 | Module 0: manual entry + T&C/KFS upload + extraction + OCR fallback | User can create a loan and see extracted fields with confidence scores |
| 3–4 | Module 1 (APR recompute) + Module 1b (serviceability) | Both unit-tested against hand-computed examples |
| 5 | Module 2 (consistency matching) | Injected-mismatch test set correctly flagged |
| 6 | RAG corpus ingestion + ChromaDB security hardening | ≥90% relevant-passage retrieval; cross-user retrieval test passes |
| 7–8 | Module 3 (dual verifier) | Groundedness Rate computed; adversarial test ≥90% catch rate |
| 9 | Module 4 (vernacular) + Module 5 (grievance) | Cross-Lingual metrics computed; grievance F1 ≥0.80 |
| 10 | Module 6 (chatbot) | Chatbot answers verified end-to-end, groundedness metric reported |
| 11 | Orchestration + full API | End-to-end call from API to verdict works, ≤5s |
| 12 | Report, demo rehearsal | Full pipeline runs live, no laptop-specific fix |

---

## If Time Runs Short — Priority Order (do not reorder this)

1. Never compromise the verifier gate (Phase 6) or the ChromaDB scoping check (Phase 5) — one is the project's thesis, the other is a straightforward Sev-1 bug waiting to happen.
2. Protect Weeks 7–9 (verifier + vernacular + adversarial test) — the graded core.
3. Cut the BERT grievance upgrade before the TF-IDF baseline.
4. Cut the chatbot's polish (multi-turn memory, follow-up questions) before its verification path — a chatbot with a rough UX but a verified answer is fine; a slick chatbot that skips verification is not.
5. Never cut: unit tests on `apr_recompute.py` and `serviceability.py`, the adversarial stress test, the ChromaDB cross-user retrieval test, or the honest scope statement in the report.
