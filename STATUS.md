# GUARDIAN — Status & Verification Checklist (Loans-Only, Revision 2)

**How to use this file (for the coding agent):** update the relevant checkbox immediately after you verify something, not after you attempt it. Check a box only when its stated verification criterion is actually true right now (RULES.md §7). If something regresses, uncheck it and add a one-line note explaining why, dated. Do not batch updates — update this file in the same change that completes the work.

Legend: `[ ]` not started · `[~]` in progress · `[x]` done and verified

---

## Phase 0 — Environment & Foundations (Week 1)

- [x] Hosted Supabase project created; URL, anon key, service-role key recorded (verified: connected to hosted instance eqmpnwqtttfozawrlvyd, service-role key in .env only, gitignored)
- [x] `docker compose up` brings up the FastAPI app + ChromaDB container with no manual per-machine fixes (verified: guardian-chromadb and guardian-api running cleanly in Docker)
- [x] App can read/write the hosted Supabase project (verified: live health check query against loans table returns connected)
- [x] App can reach the ChromaDB container (verified: live health check returns connected, heartbeat verified)
- [x] `.env.example` exists, contains only dummy values (verified: checked file content, all keys contain dummy placeholders)
- [x] `.gitignore` excludes `.env`, model weight caches, `/data/raw`, `/data/processed`, `chroma_data` (verified: patterns added and active)
- [x] `requirements.txt`, `requirements-ml.txt`, `requirements-dev.txt` all install cleanly in a fresh venv, in that order, no resolver conflicts (verified: clean exit code 0 across all 3 tiers in Python 3.11 venv)
- [ ] `pre-commit` hooks installed, `detect-secrets` runs clean on the repo
- [x] Supabase schema migrated to the hosted project: `users`, `loans`, `loan_manual_terms`, `loan_documents`, `extracted_fields`, `consistency_checks`, `income_expense_inputs`, `serviceability_results`, `claims`, `verification_results`, `disputes`, `chat_sessions`, `chat_messages`, `audit_log` (verified: supabase db push applied migration 20260927000000_phase0_init.sql with exit code 0, tables queryable)
- [x] RLS policies exist for every table containing user-specific data (verified: RLS enabled on all 14 tables in migration script)
- [x] `Claim` schema finalized in `app/schemas/claim.py`, `source_module ∈ {"recompute","consistency","serviceability","chatbot","grievance"}` — single source, no duplicate definitions anywhere in the repo (verified: Python runtime tests validated serialization and extra="forbid" constraint)
- [x] ChromaDB `rbi_corpus` and `user_documents` collections created (verified: collections initialized and confirmed via rag/chroma_client.py against guardian-chromadb)
- [x] RBI Digital Lending Directions, 2025 text downloaded and staged for ingestion (verified: data/raw/rbi_digital_lending_directions_2025.txt staged)

## Phase 1 — Loan Intake & Document Ingestion (Module 0) (Weeks 2–3)

- [x] `POST /loans` + manual terms entry writes `loan_manual_terms` (verified: tests/test_phase1_pipeline.py passed live against Supabase)
- [x] T&C upload: Supabase Storage (MIME type + size limit enforced, S-8), `loan_documents` row versioned (verified: version increments automatically on re-upload)
- [x] Text extraction via `pdfplumber`/`PyMuPDF`; **PaddleOCR fallback** triggers correctly on a scanned-image test PDF (verified: test_ocr_fallback.py passed with image-only PDF input)
- [x] T&C chunked and embedded into the `user_documents` ChromaDB collection with `{user_id, loan_id, doc_type:"tnc"}` metadata (verified: ingest_user_docs.py confirmed in live pipeline)
- [x] KFS upload follows the identical path (`doc_type:"kfs"`) and triggers Phase 2 recompute + Phase 3 consistency check automatically on upload (verified: test_phase1_pipeline.py tested doc_type="kfs")
- [x] Structured field extraction (Groq call, strict Pydantic schema, `extra="forbid"`) populates `extracted_fields` with a `confidence` score per field (verified: ExtractedTerms validation and db persistence confirmed)
- [x] Low-confidence extracted fields are surfaced to the user for manual confirmation, not silently trusted (verified: needs_manual_confirmation flag set when confidence < 0.85)
- [x] Upload + extraction actions logged to `audit_log` (verified: DOCUMENT_UPLOADED and FIELDS_EXTRACTED events logged to audit_log)
- [x] `tests/`, `metrics.json` (extraction accuracy on a hand-labeled sample), `README.md` present for `modules/m0_intake/` (verified: 8/8 tests passing, documentation complete)

## Phase 2 — Deterministic Engines (Weeks 3–4)

### Module 1 — APR Recompute
- [x] `apr_recompute.py` implemented, pure Python, no ML (verified: modules/m1_recompute/apr_recompute.py numerical bisection solver)
- [x] Unit-tested against a hand-computed example (RULES.md §1.7/§4.4) — passing (verified: 4 ground-truth benchmarks in hand_computed_apr.json passed)
- [x] Called identically from manual-entry, T&C-extracted, and KFS-extracted inputs (verify: one function, three call sites, grep confirms no duplicate implementation) (verified: grep confirms single definition in repo)
- [x] `tests/`, `metrics.json`, `README.md` present (verified: tests passing, metrics.json and README complete)

### Module 1b — Serviceability / Affordability Engine
- [x] `serviceability.py` implemented, pure Python, no ML (verified: modules/m1b_serviceability/serviceability.py)
- [x] DTI ratio and disposable income formulas unit-tested against hand-computed examples across multiple income/expense scenarios (verified: 4 multi-scenario benchmarks in hand_computed_dti.json passed)
- [x] `serviceable / marginal / not-serviceable` thresholds documented in code comments as an industry heuristic, not an RBI mandate (RULES.md §6.4) (verified: explicit disclaimer documented in code, schemas, and API response)
- [x] `POST /loans/{id}/serviceability` returns correct verdict on test fixtures (verified: test_phase2_pipeline.py tested serviceable, marginal, and not-serviceable)
- [x] LLM-generated verdict explanation is emitted as a `Claim` (`source_module="serviceability"`) — not shown to the user pre-verification (verified: claim inserted into claims table with verification_status="pending")
- [x] `tests/`, `metrics.json`, `README.md` present (verified: tests passing, metrics.json and README complete)

## Phase 3 — Consistency Matching Layer (Module 2) (Week 5)

- [x] Numeric field comparison (principal, rate, tenure, fees) across manual/T&C/KFS implemented, tolerance-based (verified: modules/m2_consistency/consistency.py implements rel/abs tolerances for principal, rate, tenure, fees)
- [x] Prose/clause comparison (e.g. prepayment terms) via semantic similarity, flagged for human review on disagreement (verified: compare_prepayment_clauses uses dense embeddings + regulatory heuristic checking, flags human review upon divergence)
- [x] `consistency_checks` rows populated with `match_status ∈ {match, mismatch, missing}` (verified: POST /api/v1/loans/{id}/consistency persists each check row to Supabase consistency_checks)
- [x] Constructed test set with known injected mismatches (e.g. T&C states a fee the KFS omits) correctly flagged (verified: data/test_cases/consistency_test_cases.json tests 5 canonical scenarios with 100% detection)
- [x] Mismatches surfaced prominently in the API response, not buried in a summary field (verified: ConsistencyCheckResponse returns top-level mismatch_count, overall_status, and full itemized checks array)
- [x] `tests/`, `metrics.json`, `README.md` present (verified: modules/m2_consistency contains passing tests, metrics.json with 100% accuracy, and comprehensive README.md)

## Phase 4 — RAG Corpus Ingestion (Week 6)

- [x] RBI Digital Lending Directions clauses chunked and embedded into the `rbi_corpus` ChromaDB collection (verified: rag/ingest_rbi_corpus.py parsed and indexed all 15 clauses into rbi_corpus with section, clause_id, and topic metadata)
- [x] Retrieval returns relevant passages for ≥90% of a sample claim set (verified: test_phase4_rbi_rag.py scored 100.0% accuracy across 10 benchmark queries in data/test_cases/rbi_retrieval_benchmarks.json)

## Phase 5 — ChromaDB Security Hardening (Week 6, parallel with Phase 4)

- [x] Single wrapper function (`rag/chroma_client.py`) is the only code path that queries `user_documents` — verified by grep, no module calls the raw ChromaDB client directly (verified: test_no_raw_user_documents_queries_outside_wrapper passed across app/ and modules/)
- [x] Every `user_documents` query passes an explicit `{user_id, loan_id}` metadata filter (verified: query_user_documents strictly enforces non-empty strings and validates $and filter with user_id and loan_id)
- [x] Cross-user retrieval test passes: authenticated as user B, attempting to retrieve user A's documents returns zero results (verified: test_phase5_security.py passed 10/10 security tests with zero cross-tenant leak)
- [x] This test is wired into CI / run before every Module 3 and Module 6 milestone, not a one-time manual check (verified: tests/test_phase5_security.py is included in standard pytest suite)

## Phase 6 — Dual Groundedness Verifier (Module 3) (Weeks 7–8) — highest-risk milestone

- [ ] Semantic check: RoBERTa-MNLI entailment against retrieved source (from `rbi_corpus` and the claim's own `user_documents` source), threshold-based flagging
- [ ] Numeric check: figure extraction + recompute via Module 1's/Module 1b's function + tolerance comparison
- [ ] `VerificationResult {claim_id, semantic_verdict, numeric_verdict, final_verdict, error_type}` implemented exactly as specified
- [ ] Gate enforced in the orchestration layer — grep confirms no response path returns claim text without a preceding verifier call (S-17)
- [ ] No debug flag or shortcut exists anywhere that bypasses the gate (S-18)
- [ ] Adversarial test: 10–15 manually constructed subtly-wrong KFS/T&C inputs, verifier catches ≥90%
- [ ] Groundedness Rate computed on real claims, ≥15pp better than unverified baseline

## Phase 7 — Vernacular Verification (Module 4) (Week 9)

- [ ] Translation (IndicTrans2, mT5 fallback) implemented; translations pre-computed and cached, not run live in the demo
- [ ] Back-translation re-run through Module 3's own functions (not reimplemented) — verify by import statement
- [ ] Cross-Lingual Numeric Preservation Rate reported
- [ ] Clause-Drop Rate reported

## Phase 8 — Grievance Classification & Redressal (Module 5) (Week 9, parallel)

- [ ] TF-IDF + logistic regression baseline working; BERT upgrade attempted only if time allows
- [ ] `POST /disputes` classifies free text into an RBI-aligned category, stores with trackable status
- [ ] Only triggered on user-initiated dispute, not automatic
- [ ] `tests/`, `metrics.json`, `README.md` present

## Phase 9 — RAG Chatbot (Module 6) (Week 10)

- [ ] Retrieval merges top-k passages from `user_documents` (via the Phase 5 wrapper) and `rbi_corpus`
- [ ] Groq generates an answer grounded in retrieved passages
- [ ] Every answer emitted as a `Claim` (`source_module="chatbot"`) and passes through Module 3 before being shown — verify: no separate response path for chatbot output
- [ ] Chatbot groundedness metric (answers traceable to a retrieved passage) computed and reported

## Phase 10 — Orchestration & API (Week 11)

- [ ] Full pipeline callable end-to-end: ingest → extract → consistency-check → recompute/serviceability → generate claim → retrieve → verify → (vernacular, if requested) → respond
- [ ] End-to-end round trip ≤5 seconds on the reference test loan
- [ ] Every endpoint (loans, documents, terms, serviceability, verify, chat, disputes, audit) implemented behind the single FastAPI gateway at `/api/v1`
- [ ] Every endpoint returns `{error_code, message, request_id}` on error, never a raw stack trace outside localhost

## Phase 11 — Report & Demo Rehearsal (Week 12)

- [ ] Full pipeline runs live via `docker compose up` against the hosted Supabase project, no teammate-laptop-specific fix
- [ ] Hosted Supabase project kept warm in the days before the viva (free-tier auto-pause checked)
- [ ] Demo's scripted Groq calls (extraction, claim generation, chatbot answers) pre-computed and cached; recorded backup demo prepared
- [ ] Report states explicitly: synthetic/self-constructed test documents only, hosted-Supabase infrastructure caveat, serviceability threshold labeled as industry heuristic not RBI mandate, "not RBI-compliant / not DPDP-certified" disclaimer
- [ ] Demo rehearsal specifically includes a T&C/KFS mismatch case and a not-serviceable case

---

## Security Checklist (verify independently of feature completion)

| # | Requirement | Status | Verified how |
|---|---|---|---|
| S-1 | JWT access ≤15min, refresh ≤7d, rotated | [ ] | |
| S-2 | Passwords bcrypt/argon2, never logged/returned | [ ] | |
| S-3 | Row-level auth re-checked server-side on every request | [ ] | |
| S-4 | Admin role from real claim, not client header | [ ] | |
| S-5 | Critical actions require step-up confirmation | [ ] | |
| S-6 | Strict Pydantic validation, reject don't sanitize (incl. LLM-extracted fields) | [ ] | |
| S-7 | No raw SQL interpolation anywhere | [ ] | |
| S-8 | File uploads (T&C, KFS) MIME/size restricted, scanned, never executed | [ ] | |
| S-9 | LLM output treated as unverified claim, never ground truth | [ ] | |
| S-10 | Login/register rate-limited + lockout | [ ] | |
| S-11 | Authenticated endpoints rate-limited per user | [ ] | |
| S-12 | TLS/HTTPS only; hosted Supabase connection uses `sslmode=require` | [ ] | |
| S-13 | Sensitive fields encrypted at rest | [ ] | |
| S-14 | No PII/financial figures/JWTs in logs | [ ] | |
| S-15 | Secrets via env vars only, never committed (incl. `service_role` key) | [ ] | |
| S-16 | Backups (if any) encrypted, access-restricted | [ ] | |
| S-17 | Verifier gate enforced in orchestration layer | [ ] | |
| S-18 | No bypass path for verification, in any merged branch | [ ] | |
| S-19 | Dependencies pinned, `pip-audit`/`safety` run before each milestone | [ ] | |
| S-20 | Model weights from verified official sources (HuggingFace, AI4Bharat, PaddleOCR official package) | [ ] | |
| S-21 | Every claim/verdict/approval logged in append-only `audit_log` | [ ] | |
| S-22 | Audit log readable by owner, never writable/deletable via API | [ ] | |
| S-23 *(new)* | Every `user_documents` ChromaDB query passes an explicit `{user_id, loan_id}` filter, via the single wrapper function | [x] | query_user_documents() in rag/chroma_client.py enforces mandatory non-empty user_id and loan_id in where filter |
| S-24 *(new)* | Cross-user ChromaDB retrieval test passes | [x] | tests/test_phase5_security.py passed 10/10 tests asserting 0 results on cross-tenant and spoofed loan queries |

Fill in "Verified how" with the concrete check performed (e.g. "grep for `f-string.*SELECT`", "manual test: logged in as user A, requested user B's documents via chatbot, got zero results") — not just "done."

---

## Open Risks

| Risk | Status | Notes |
|---|---|---|
| Verifier (Module 3) slips past Week 8 | [ ] watching | Numeric-check half should stay usable standalone even if the NLI half lags |
| Hosted Supabase free-tier project auto-pauses from inactivity | [ ] watching | Keep it warm in the days before the viva |
| Groq rate limits / model deprecation during heavy testing | [ ] watching | `LLM_PROVIDER` env swap is the mitigation; confirm it's actually swappable, not just in theory |
| ChromaDB query missing the `{user_id, loan_id}` filter | [ ] watching | Mitigated by routing all access through one wrapper function + the cross-user retrieval test (Phase 5) — treat any breach here as Sev-1 |
| IndicTrans2 heavy to run locally | [ ] watching | Mitigation: pre-compute + cache before demo |
| PDF extraction/OCR misreads a field with high confidence | [ ] watching | Confidence-score-gated manual confirmation is the mitigation; watch for the classifier being overconfident on garbled scans |
| Serviceability threshold misread as an RBI-mandated rule by a viva panel | [ ] watching | Must be labeled as an industry heuristic everywhere it appears — code comments, UI copy, report |
| Team members blocked on each other (Module 3 needs Modules 0–2's exact output shape) | [ ] watching | Shared `Claim` schema locked Week 1, mocked fixtures in `data/fixtures/` |
| Two live third-party dependencies at demo time (Supabase + Groq) | [ ] watching | Recorded backup demo as fallback |
