# GUARDIAN — Coding Agent Rules (Loans-Only, Revision 2)
**Binding contract for any agent (human or AI) writing code on this repo.**
Source documents: `GUARDIAN_LOANS_ONLY_SPEC.md` (idea/stack/architecture), `IMPLEMENTATION_PLAN.md` (build sequence), `STATUS.md` (live checklist).
If any instruction elsewhere conflicts with this file, this file wins. If this file conflicts with the spec, stop and ask — don't silently resolve it either way.

---

## §1. The Verification Gate Is Sacred (highest-priority rule in the project)

This is the entire reason the project exists — everything else is in service of it.

1.1. **No `Claim` object may reach a user-facing response without a corresponding row in `verification_results`.** This is enforced structurally in the orchestration layer — a single choke-point function every response path is forced through — not by convention.

1.2. **There is no debug flag, feature flag, env var, admin override, or "trusted source" shortcut that skips verification.** If you find yourself writing one — even temporarily, even commented out — delete it before committing. Search the diff for `bypass`, `skip_verif`, `TRUSTED`, `debug_mode` before every PR touching the orchestration layer.

1.3. This applies to **all five claim sources** — `recompute`, `consistency`, `serviceability`, `chatbot`, `grievance` — with no exceptions for any of them. In particular: **the RAG chatbot's answers go through the exact same verifier as everything else.** A chatbot that skips verification undermines the entire project's thesis, so don't treat it as a lighter-weight or "just conversational" path.

1.4. A claim failing semantic OR numeric verification is `flagged`, never silently dropped and never shown as fact. The specific failure reason (`semantic mismatch` / `numeric mismatch` / `both`) is stored, not just a boolean.

1.5. Before merging any PR that touches Modules 0–6 or the orchestration layer, grep the entire response-path code for any route that returns `claim_text` without a preceding verifier call. Required manual review step, not optional.

1.6. Module 4 (vernacular) **imports and calls** Module 3's verifier functions. It does not fork, copy, or reimplement any part of the semantic or numeric check.

1.7. `apr_recompute.py` (Module 1) and `serviceability.py` (Module 1b) are each a single function, imported everywhere their number is needed — Module 3's numeric check, Module 2's consistency comparisons, wherever else. If you ever find a second copy of APR/EMI or DTI math anywhere in the repo, that's a bug, even if it "does the same thing" — it can silently drift and invalidate the verifier's numeric guarantee.

1.8. Note the one deliberate exception to "everything gets verified": the DTI/serviceability *arithmetic* itself does not need re-verification — it's deterministic by construction, same as APR. Only the LLM-generated *sentence describing* the DTI result is a `Claim` that must pass through Module 3. Don't confuse "the number is trustworthy" with "the sentence about the number is trustworthy" — they are checked differently and only the second needs the verifier.

---

## §2. ChromaDB Scoping Is a Security-Critical Path, Not a Convenience Filter

This is new in this revision and gets its own section because it's easy to underrate.

2.1. ChromaDB has **no built-in row-level security.** Supabase Postgres RLS does not protect it. Every query against the `user_documents` collection **must** pass an explicit `where={"user_id": ..., "loan_id": ...}` metadata filter.

2.2. All ChromaDB access goes through one wrapper function (`rag/chroma_client.py`). **No module or route calls the raw ChromaDB client directly.** This is the only way to guarantee the filter is never accidentally omitted.

2.3. A missing or bypassable filter here is treated with the exact same severity as §3's "any endpoint returning another user's data" — fixed before any other work continues on that branch, full stop.

2.4. A cross-user retrieval test (authenticate as user B, attempt to retrieve user A's documents, assert zero results) is required before Module 6 (chatbot) or Module 3's retrieval step is considered done — not an optional nice-to-have test.

---

## §3. Security — every item below is a blocking requirement, not a nice-to-have

| # | Rule | Enforcement |
|---|---|---|
| S-1 | Access JWT ≤15 min TTL, refresh ≤7 days, refresh rotated on use | Supabase Auth (hosted) handles this — do not hand-roll a parallel token scheme |
| S-2 | Passwords never touch app code in plaintext | Supabase Auth hashes internally |
| S-3 | Row-level auth re-checked **server-side on every request** | A FastAPI dependency compares JWT `sub` against the requested `user_id`/`loan_id` on every route — Supabase RLS is defense-in-depth, not a substitute for this code |
| S-4 | Admin role comes from a real, server-set claim | Never trust a client-supplied header |
| S-5 | Critical actions require step-up confirmation | No "auto-approve after N seconds" — applies to dispute submission and any action with real-world consequence |
| S-6 | Strict Pydantic v2 validation, `extra="forbid"` | Reject malformed/extra-field requests outright — including LLM-extracted field payloads (§4.2) |
| S-7 | No raw SQL string interpolation, anywhere | ORM parameterized queries only, no exceptions |
| S-8 | File uploads (T&C PDF, KFS PDF) restricted + scanned | MIME type + size limit checked before processing; never `eval()`'d or executed |
| S-9 | LLM output is a claim, never ground truth | Every LLM-generated string — including extracted fields, claim explanations, and chatbot answers — is untrusted until verified |
| S-10 | Login/register rate-limited + lockout | Per IP and per account |
| S-11 | Authenticated endpoints rate-limited per user | Prevents one account from exhausting ML/LLM inference resources |
| S-12 | TLS everywhere, including local dev | Hosted Supabase enforces TLS on its own endpoints — confirm the connection string uses `sslmode=require`, don't assume it |
| S-13 | Sensitive fields encrypted at rest | `pgcrypto` for account numbers etc. |
| S-14 | No PII, financial figures, or JWTs in logs | Log request IDs and non-sensitive metadata only |
| S-15 | Secrets via env vars only, never committed | `.env`/`.env.example`; `service_role` key never shipped to client-facing code |
| S-16 | Backups (if any) encrypted, access-restricted | |
| S-17/S-18 | Verifier gate can't be bypassed | See §1 |
| S-19 | Pinned deps, `pip-audit` before every milestone | Three-file requirements split |
| S-20 | Model weights from verified official sources only | Official HuggingFace orgs / AI4Bharat official release; PaddleOCR from its official PyPI package, not a third-party mirror |
| S-21/S-22 | Append-only `audit_log` | Insert-only at the app layer — **no `UPDATE` or `DELETE` route is ever defined against this table** |

3.1. **Any endpoint that returns another user's data is a Sev-1 bug**, fixed before any other work continues on that branch — this now explicitly includes ChromaDB retrieval results, per §2.

---

## §4. Process Rules

4.1. Feature branches only. `main` is always demo-able. No direct commits to `main` after Week 2.

4.2. Every PR requires one teammate review, even in a 3-person team.

4.3. A module is not "done" without: a `tests/` folder with a passing `pytest` run, a `metrics.json` output, and a `README.md`. All three, every module — `m0_intake`, `m1_recompute`, `m1b_serviceability`, `m2_consistency`, `m3_verifier`, `m4_vernacular`, `m5_grievance`, `m6_chatbot` alike.

4.4. **Every deterministic financial calculation — APR, EMI, and now DTI/serviceability — is unit-tested against a hand-computed example** before any downstream module is allowed to trust it. A wrong `serviceability.py` is just as damaging to the project's credibility as a wrong `apr_recompute.py` — treat both with equal seriousness, don't let the newer module get less rigor because it was added later.

4.5. No raw API keys, DB passwords, model tokens, or the Supabase `service_role` key in code — ever, including in notebooks, including in commit history. Pre-commit `detect-secrets` installed before Week 3.

4.6. Every module exposes its functionality behind a Python function or FastAPI route — never a standalone notebook.

4.7. Every module's output consumed by Module 3 conforms to the shared `Claim` Pydantic schema (`app/schemas/claim.py`, `source_module ∈ {"recompute","consistency","serviceability","chatbot","grievance"}`) — exactly one definition in the repo.

---

## §5. Stack Discipline

5.1. The stack is **hosted Supabase (Postgres 15, Auth, Storage) + ChromaDB (self-hosted in Docker) + Groq API**, per `GUARDIAN_LOANS_ONLY_SPEC.md` Revision 2. If a teammate proposes reverting to local Supabase or a different vector store, that's a scope change — record it explicitly, don't drift into it silently.

5.2. **Supabase is a hosted, live third-party dependency at demo time** — this was a deliberate, stated trade-off (see §7), not an oversight. Mitigate it by keeping the project warm before the viva (free-tier auto-pause) and by keeping ChromaDB and cached Groq calls fully local so a Supabase hiccup is the only failure mode that depends on the network.

5.3. Three-file dependency split, installed in order into the same venv: `requirements.txt` (API/orchestration/DB/LLM-client), `requirements-ml.txt` (transformers, scikit-learn, `pdfplumber`/`PyMuPDF`, `paddleocr`+`paddlepaddle`, `chromadb`), `requirements-dev.txt` (test/lint/security tooling).

5.4. `LLM_PROVIDER` env var is the only thing that should need to change to swap Groq for a different provider later. Confirm this is actually true by a call-site test, not just in theory.

5.5. Pre-compute and cache the demo's scripted Groq calls (field extraction, claim generation, chatbot answers) and all vernacular translations — **never run either live during the demo.**

5.6. Before relying on pinned versions at the Week 1 setup session, confirm on `pypi.org` and `console.groq.com/docs/models` that the pinned `groq`, `chromadb`, and other fast-moving packages still exist and are mutually compatible, and that the named Groq model is still active.

---

## §6. Data & Scope Honesty

6.1. **Synthetic and self-constructed test data/documents only.** Real T&C or KFS PDFs used only if genuinely the user's own, for their own demo purposes — never a third party's real financial document without consent.

6.2. This project must never be presented, marketed, or deployed as RBI-compliant or DPDP-certified. It demonstrates verification techniques relevant to that regulatory context — nothing more.

6.3. Guardian never executes an irreversible action autonomously — critical actions (submitting a dispute, sharing data) require an explicit human confirmation step, no auto-approve pattern, ever.

6.4. **The serviceability threshold (§9 of the spec, Module 1b) is a commonly used lending-industry heuristic, not an RBI-mandated rule.** State this explicitly in code comments, in the UI copy shown to the user, and in the report. Do not let the verdict be presented in a way that implies regulatory backing it doesn't have.

6.5. **Hosted Supabase is a managed third-party infrastructure provider**, even though it's the project's own access-controlled database. State this plainly in the report's data-residency section rather than reusing the original "our own PostgreSQL instance, no third party" language unmodified.

6.6. Scope decisions (synthetic data, hosted-infra trade-off, ChromaDB over pgvector, PaddleOCR over Tesseract, dropped cashflow/anomaly/insurance scope) are stated explicitly and honestly in the report as deliberate decisions — never allowed to look like oversights discovered by the panel.

---

## §7. STATUS.md Discipline

7.1. Update the relevant checkbox in `STATUS.md` **in the same change that completes the work** — not batched later.

7.2. Check a box only when its stated verification criterion is *actually true right now*, verified by the concrete method described — not "I wrote the code so I'll check it."

7.3. If something regresses, uncheck it immediately and add a one-line dated note explaining why.

7.4. The Security Checklist's "Verified how" column gets a concrete check performed — never just "done."

---

## §8. Order of Operations (do not build out of dependency order)

Environment/hosted-Supabase/ChromaDB setup → Module 0 (intake/upload/extraction) → Module 1 & Module 1b (parallel, both deterministic) → Module 2 (consistency) → RAG corpus ingestion + ChromaDB security hardening (§2) → Module 3 (verifier) → Module 4 (vernacular) & Module 5 (grievance) (parallel) → Module 6 (chatbot) → orchestration → report/demo rehearsal.

Do not start Module 3 before the shared `Claim` schema is locked, Modules 0–2 emit valid `Claim`/consistency objects, and the ChromaDB cross-user retrieval test (§2.4) passes. Do not start Module 6 before Module 3 is fully working and tested.

---

## §9. When Rules Conflict With Speed

If a deadline pressures cutting a corner, the corner to cut is **scope** — trim chatbot polish, skip the BERT grievance upgrade, ship the numeric-check half of the verifier standalone if NLI lags — never §1 (verifier gate), never §2 (ChromaDB scoping), never §3 (security), never §6 (data/scope honesty). A partially-working, honestly-scoped Guardian is a good project. A fully-featured one with a bypassable verifier, an unscoped ChromaDB query, or a fabricated compliance/regulatory claim is not — it undermines the entire thesis.
