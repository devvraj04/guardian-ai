# GUARDIAN: Groundedness-Verified Agentic Financial Advocate (Loans Vertical)

[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/release/python-3110/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111.0-009688.svg)](https://fastapi.tiangolo.com)
[![ChromaDB](https://img.shields.io/badge/ChromaDB-0.5.23-orange.svg)](https://www.trychroma.com/)
[![Supabase](https://img.shields.io/badge/Supabase-PostgreSQL%2015-green.svg)](https://supabase.com)
[![License: Academic/Research](https://img.shields.io/badge/License-Academic%2FResearch-lightgrey.svg)](LICENSE)

**GUARDIAN** is an audit-grade financial advocate designed to protect digital retail borrowers against predatory lending terms, undisclosed charges, miscalculated interest rates, and regulatory violations. 

Unlike traditional financial applications that rely on opaque language model responses, GUARDIAN enforces a **Sacred Verification Gate**: every financial claim, explanation, or verdict is deterministically recomputed or semantically grounded against regulatory mandates before reaching the borrower.

---

## 🏛️ System Architecture Built to Date (Phases 0 – 5)

The platform is engineered as a multi-tier modular pipeline operating on a shared, tamper-proof database and scoped vector store:

```
[Borrower Intake] ──> [Module 0: Dual-Path Ingestion & OCR Fallback]
                             │
                             ├──> Manual Terms (loan_manual_terms)
                             ├──> Document Chunks (ChromaDB: user_documents)
                             └──> Extracted Fields (extracted_fields)
                                         │
        ┌────────────────────────────────┴────────────────────────────────┐
        ▼                                                                 ▼
[Module 1: APR Recompute]                                    [Module 2: Consistency Matching]
  - Bisection IRR Solver                                       - 3-Way Cross Check: Manual vs T&C vs KFS
  - Reducing-Balance EMI                                       - Tolerance-based Numeric Match
  - Zero ML / Pure Math                                        - Semantic Clause Discrepancy Detection
        │                                                                 │
        ▼                                                                 ▼
[Module 1b: Serviceability]                                  [ChromaDB Security Hardened Layer]
  - DTI & Disposable Income                                    - Scoped {user_id, loan_id} Wrapper
  - Industry Heuristic Verdict                                 - Cross-Tenant Isolation Verified
        │                                                                 │
        └────────────────────────────────┬────────────────────────────────┘
                                         ▼
                   [Phase 4: Shared RBI Regulatory Corpus]
                     - RBI Digital Lending Directions, 2025
                     - 100% Benchmark Retrieval Accuracy
                                         │
                                         ▼
                   [The Sacred Verification Gate (Pending)]
                     - Claims Table (verification_status="pending")
                     - Append-Only Audit Log (audit_log)
```

---

## 📦 Implemented Modules & Capabilities

### Phase 0 — Environment & Data Foundations
- **Three-Tier Dependency Split**: Segregated dependencies into `requirements.txt` (core API/DB), `requirements-ml.txt` (ML/OCR/vector), and `requirements-dev.txt` (lint/test security tooling).
- **Postgres Database with Supabase**: Hosted instance with 14 relational tables, Row-Level Security (RLS) policies, and an append-only, tamper-proof `audit_log`.
- **Vector Infrastructure**: Dockerized ChromaDB (`chromadb/chroma:0.5.23`) with dedicated `rbi_corpus` and scoped `user_documents` collections.
- **Canonical Claim Schema**: Strict Pydantic v2 `Claim` schema with `extra="forbid"` and 5 allowed source modules (`recompute`, `consistency`, `serviceability`, `chatbot`, `grievance`).

### Phase 1 — Module 0: Loan Intake & Document Ingestion (`modules/m0_intake`)
- **Manual Terms Registration**: `POST /api/v1/loans` and `POST /api/v1/loans/{id}/terms`.
- **Document Upload & Versioning**: `POST /api/v1/loans/{id}/documents/upload` storing versioned contracts in Supabase Storage (`loan-documents` bucket).
- **Dual-Path Text Extraction**: Digital PDF extraction via `pdfplumber`/`PyMuPDF` with automatic fallback to `PaddleOCR` when text density drops below 50 characters/page.
- **Structured Field Extraction**: Groq LLM parsing of `{principal, disclosed_rate, tenure_months, processing_fee, prepayment_clause}` with regex fallback.
- **Confidence Scoring**: Fields with confidence $< 0.85$ are flagged with `needs_manual_confirmation: true`.

### Phase 2 — Deterministic Engines: Modules 1 & 1b
- **Module 1 (`modules/m1_recompute/apr_recompute.py`)**:
  - Pure Python reducing-balance EMI arithmetic and numerical bisection solver for Internal Rate of Return (IRR) cash flows to derive true effective APR.
  - Zero ML. Unit-tested against hand-computed benchmarks (`data/test_cases/hand_computed_apr.json`).
  - **Single Source Invariant**: Only one implementation of APR/EMI math exists in the repository (RULES.md §1.7).
- **Module 1b (`modules/m1b_serviceability/serviceability.py`)**:
  - Deterministic Debt-To-Income (DTI) and disposable income calculator.
  - Heuristic classification into `serviceable`, `marginal`, and `not-serviceable`.
  - **Regulatory Honesty**: Explicitly documented in code, API responses, and schemas as an industry lending heuristic, NOT an RBI mandate (RULES.md §6.4).
- **Verification Gate**: Emits natural-language explanations as `Claim` objects with `verification_status="pending"` into `public.claims`.

### Phase 3 — Module 2: Consistency Matching Layer (`modules/m2_consistency`)
- **Three-Way Cross Comparison**: Compares corresponding fields across `loan_manual_terms`, T&C `extracted_fields`, and KFS `extracted_fields`.
- **Tolerance-Based Numeric Match**:
  - `principal`: Relative diff $\le 0.1\%$ or absolute diff $\le ₹10$.
  - `disclosed_rate`: Absolute diff $\le 0.05\%$.
  - `tenure_months`: Strict integer match (0 months tolerance).
  - `fees`: Relative diff $\le 0.5\%$ or absolute diff $\le ₹10$.
- **Prose Clause Disagreement Detection**:
  - Compares `prepayment_clause` across documents using dense embeddings (`all-MiniLM-L6-v2`) and regulatory clause analysis (e.g. nil fees vs. positive penalty fees).
  - Contradictions trigger `match_status = "mismatch"` and `requires_human_review = True`. Disagreements are never auto-resolved.
- **Injected Mismatch Ground Truth**: 100% detection rate on canonical injected-mismatch test suite (`data/test_cases/consistency_test_cases.json`).
- **Endpoint**: `POST /api/v1/loans/{id}/consistency`, persisting records into `consistency_checks`.

### Phase 4 — RAG Layer: RBI Regulatory Corpus Ingestion (`rag/ingest_rbi_corpus.py`)
- Ingested all 15 clauses from the *Reserve Bank of India - Digital Lending Directions, 2025* (`data/raw/rbi_digital_lending_directions_2025.txt`) into `rbi_corpus`.
- Structured metadata tracks section number, section title, clause ID, and regulatory topic.
- **Retrieval Benchmark Gate**: Achieved **100.0% retrieval accuracy** across 10 canonical regulatory queries in `data/test_cases/rbi_retrieval_benchmarks.json` (exceeding the $\ge 90\%$ gate requirement).

### Phase 5 — Vector Store Security Hardening (`rag/chroma_client.py`)
- **Single Choke-Point Scoping**: ChromaDB does not possess native row-level security. A central wrapper function enforces mandatory non-empty `{user_id, loan_id}` metadata filtering.
- **Cross-Tenant Vector Isolation**: Verified through adversarial security tests (`tests/test_phase5_security.py`):
  - User B attempting to query User A's `loan_id` returns 0 results.
  - User B searching for User A's confidential financial terms leaks 0 documents.
  - Malformed or blank `user_id` / `loan_id` arguments raise immediate `ValueError`.
  - Zero raw `user_documents` collection queries exist outside `rag/chroma_client.py` (verified by AST/grep).

---

## 🚀 Getting Started & Execution Guide

### 1. Prerequisites
- **Operating System**: Windows, Linux, or macOS.
- **Python**: Python 3.11.x (installed in `venv/`).
- **Docker**: Docker Desktop running for local ChromaDB.

### 2. Environment Configuration
Verify your `.env` file exists in the repository root. Ensure the following variables are configured:
```ini
ENVIRONMENT=development
DATABASE_URL=postgresql://postgres.eqmpnwqtttfozawrlvyd:[PASSWORD]@aws-0-ap-south-1.pooler.supabase.com:6543/postgres?sslmode=require
SUPABASE_URL=https://eqmpnwqtttfozawrlvyd.supabase.co
SUPABASE_ANON_KEY=...
SUPABASE_SERVICE_ROLE_KEY=...
CHROMA_HOST=localhost
CHROMA_PORT=8000
GROQ_API_KEY=...
GROQ_MODEL=llama-3.3-70b-versatile
```

### 3. Launching ChromaDB Container
Start the official ChromaDB vector store container (pinned to `0.5.23`):
```powershell
docker compose up -d
```
Verify the container is healthy:
```powershell
docker ps
```

### 4. Ingesting the RBI Regulatory Corpus (Phase 4)
Ingest the *RBI Digital Lending Directions, 2025* into ChromaDB:
```powershell
.\venv\Scripts\python.exe -m rag.ingest_rbi_corpus
```
*Expected Output: `Successfully ingested 15 RBI clauses into rbi_corpus.`*

### 5. Running the Complete Verification Test Suite
Execute the comprehensive test suite spanning all modules and security invariants:
```powershell
.\venv\Scripts\pytest -v
```
*Current test suite status: **34/34 tests passing**.*

To run individual phase test suites:
- **Phase 0 & 1 (Intake & OCR)**: `pytest -v modules/m0_intake/tests tests/test_phase1_pipeline.py`
- **Phase 2 (APR & Serviceability)**: `pytest -v modules/m1_recompute/tests modules/m1b_serviceability/tests tests/test_phase2_pipeline.py`
- **Phase 3 (Consistency Matching)**: `pytest -v modules/m2_consistency/tests tests/test_phase3_consistency.py`
- **Phase 4 (RBI RAG Benchmark)**: `pytest -v tests/test_phase4_rbi_rag.py`
- **Phase 5 (Vector Security Hardening)**: `pytest -v tests/test_phase5_security.py`

### 6. Starting the API Server
Start the local FastAPI development server:
```powershell
.\venv\Scripts\uvicorn app.main:app --host 127.0.0.1 --port 8080 --reload
```
Interactive API documentation will be accessible at:
- **Swagger UI**: [http://127.0.0.1:8080/docs](http://127.0.0.1:8080/docs)
- **Health Check**: [http://127.0.0.1:8080/api/v1/health](http://127.0.0.1:8080/api/v1/health)

---

## 🔍 API Endpoints Reference (Implemented to Date)

| Method | Endpoint | Description | Phase |
|---|---|---|---|
| `GET` | `/api/v1/health` | Service health, Supabase DB check, ChromaDB status | Phase 0 |
| `POST` | `/api/v1/loans` | Register a new loan offer | Phase 1 |
| `GET` | `/api/v1/loans` | List loans owned by authenticated user | Phase 1 |
| `POST` | `/api/v1/loans/{id}/terms` | Submit manual borrower loan terms | Phase 1 |
| `POST` | `/api/v1/loans/{id}/documents/upload` | Upload T&C / KFS PDF, extract text & structured fields | Phase 1 |
| `POST` | `/api/v1/loans/{id}/recompute` | Compute reducing-balance EMI and effective APR | Phase 2 |
| `POST` | `/api/v1/loans/{id}/serviceability` | Calculate DTI ratio, disposable income & heuristic verdict | Phase 2 |
| `POST` | `/api/v1/loans/{id}/consistency` | Execute 3-way consistency matching & flag discrepancies | Phase 3 |

---

## 🛡️ Binding Security Invariants (RULES.md)

1. **Sacred Verification Gate (RULES.md §1)**: No `Claim` reaches user-facing presentation without a corresponding verdict from Module 3. All preliminary explanations are persisted with `verification_status="pending"`.
2. **Server-Side Authorization (RULES.md §3 S-3)**: Row-level authentication is re-verified server-side on every request (`sub == loan.user_id`).
3. **ChromaDB Scoping (RULES.md §2)**: ChromaDB access to user document chunks is strictly isolated per `{user_id, loan_id}` via `rag/chroma_client.py`.
4. **Append-Only Audit Trail (RULES.md §3 S-21)**: Every critical action (loan creation, document upload, APR calculation, consistency check) writes an immutable record to `audit_log`. No `UPDATE` or `DELETE` route exists.
5. **Single Math Source (RULES.md §1.7)**: Exactly one implementation of financial math (`apr_recompute.py` and `serviceability.py`) exists across the entire codebase.

---

## 📊 Project Progress & Status

Track real-time implementation status in [STATUS.md](file:///c:/Users/Devraj/Desktop/miniProject/guardian/STATUS.md).
- **Phase 0 — Foundations**: ✅ Complete
- **Phase 1 — Ingestion & OCR**: ✅ Complete
- **Phase 2 — Deterministic Engines**: ✅ Complete
- **Phase 3 — Consistency Matching**: ✅ Complete
- **Phase 4 — RAG Ingestion**: ✅ Complete (100% retrieval accuracy)
- **Phase 5 — Vector Store Security**: ✅ Complete (Cross-user isolation verified)
- **Phase 6 — Dual Groundedness Verifier (Module 3)**: ⏳ Next Up
