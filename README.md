# GUARDIAN: Groundedness-Verified Agentic Financial Advocate (Loans Vertical)

[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/release/python-3110/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111.0-009688.svg)](https://fastapi.tiangolo.com)
[![Next.js 16](https://img.shields.io/badge/Next.js-16.0-black.svg)](https://nextjs.org/)
[![React 19](https://img.shields.io/badge/React-19.0-61dafb.svg)](https://react.dev/)
[![ChromaDB](https://img.shields.io/badge/ChromaDB-0.5.23-orange.svg)](https://www.trychroma.com/)
[![Supabase](https://img.shields.io/badge/Supabase-PostgreSQL%2015-green.svg)](https://supabase.com)
[![RBI Compliance](https://img.shields.io/badge/RBI%20Compliance-Master%20Directions%202024%2F25-emerald.svg)](https://www.rbi.org.in)

**GUARDIAN** is an audit-grade, autonomous regulatory compliance platform designed to protect retail borrowers against predatory lending terms, hidden charges, understated Annual Percentage Rates (APR), and regulatory violations under the **Reserve Bank of India (RBI) Digital Lending Directions (2022/2025)** and **Master Directions on Key Fact Statement (KFS, RBI/2024-25/18)**.

Unlike traditional financial applications that rely on unverified, hallucination-prone Large Language Models, GUARDIAN enforces a **Sacred Verification Gate**: every financial claim, explanation, or verdict is deterministically recomputed via pure Python mathematics and semantically verified against authoritative regulatory mandates before reaching the borrower.

---

## 🏛️ System Architecture

GUARDIAN operates as a modular, end-to-end pipeline structured around deterministic computational engines, dual-gated verification, and an interactive financial analytics suite:

```
[Borrower / UI Intake] 
          │
          ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│  MODULE 0: DUAL-PATH INGESTION & OCR FALLBACK                                │
│  - Native Digital PDF Parsing (pdfplumber / PyMuPDF)                         │
│  - Scanned Document OCR Fallback (PaddleOCR / Vision)                        │
│  - Statutory Field Extraction (Principal, Rate, Tenor, Fees, KFS Clauses)    │
│  - Automated Faulty / Blank KFS Detection Engine                             │
└──────────────────────────────────────┬───────────────────────────────────────┘
                                       │
         ┌─────────────────────────────┴─────────────────────────────┐
         ▼                                                           ▼
┌──────────────────────────────────────┐    ┌──────────────────────────────────┐
│  MODULE 1: DETERMINISTIC APR ENGINE  │    │  MODULE 2: 3-WAY CONSISTENCY     │
│  - Reducing-Balance Monthly EMI      │    │  - Cross-Match: Manual vs T&C vs │
│  - Net Disbursed Deduction           │    │    Key Fact Statement (KFS)      │
│  - Bisection IRR True APR Solver     │    │  - Tolerance-Based Numeric Match │
│  - Zero ML / 100% Deterministic Math │    │  - Semantic Clause Discrepancy   │
└──────────────────┬───────────────────┘    └────────────────┬─────────────────┘
                   │                                         │
                   ▼                                         │
┌──────────────────────────────────────┐                     │
│  MODULE 1b: SERVICEABILITY ENGINE    │                     │
│  - FOIR / Debt-to-Income (DTI) Ratio │                     │
│  - Net Disposable Living Buffer      │                     │
│  - Industry Heuristic Verdict        │                     │
└──────────────────┬───────────────────┘                     │
                   │                                         │
                   └────────────────────┬────────────────────┘
                                        │
                                        ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│  RAG REGULATORY KNOWLEDGE LAYER (ChromaDB 0.5.23)                            │
│  - RBI Digital Lending Directions 2025 (All 15 Clauses Ingested)             │
│  - Single Choke-Point Scoping: Strict {user_id, loan_id} Tenant Isolation   │
│  - 100% Benchmark Retrieval Accuracy on Canonical Regulatory Queries         │
└──────────────────────────────────────┬───────────────────────────────────────┘
                                       │
                                       ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│  MODULE 3: THE SACRED VERIFICATION GATE                                      │
│  - Numeric Verifier: Zero-tolerance regex entity extraction & DB comparison  │
│  - Semantic Verifier: RoBERTa-MNLI Cross-Encoder Entailment Verification     │
│  - Gated Output: Only verified 'grounded' claims reach the borrower          │
└──────────────────────────────────────┬───────────────────────────────────────┘
                                       │
         ┌─────────────────────────────┼─────────────────────────────┐
         ▼                             ▼                             ▼
┌──────────────────┐          ┌──────────────────┐          ┌──────────────────┐
│  MODULE 4:       │          │  MODULE 5:       │          │  MODULE 6:       │
│  VERNACULAR      │          │  GRIEVANCE & CMS │          │  GATED AI        │
│  TRANSLATION     │          │  DISPUTE ENGINE  │          │  ADVISORY CHAT   │
│  - 12+ Languages │          │  - PNO Notices   │          │  - RAG Retrieval │
│  - Back-Check    │          │  - RBI CMS Legal │          │  - Verification- │
│  - Zero Drift    │          │    Dossiers      │          │    Gated Output  │
└──────────────────┘          └──────────────────┘          └──────────────────┘
                                       │
                                       ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│  FRONTEND SUITE: VERIFICATION REPORT & PREPAYMENT SIMULATOR                  │
│  - Full Compliance Audit & KFS Mandatory Disclosures Schedule                │
│  - Step-by-Step Mathematical Calculation Breakdown (EMI, APR, Net Disbursed) │
│  - Dual-Curve Interactive Payoff Graph (Baseline vs Fast-Track Prepayment)   │
│  - Full Year-by-Year Amortization Schedule (Every Year till Loan Term)       │
│  - Prepayment Simulator (1 Extra EMI, Step-Up %, Custom Monthly, Lump Sum)   │
│  - Economic Reality Check: Loan ROI vs Current India CPI Inflation (~5.5%)   │
│  - Certified Audit Report Export (PDF Print Layout + JSON Audit Certificate) │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## 📦 Module-by-Module Technical Architecture

### Module 0: Loan Intake, Document Ingestion & Faulty KFS Detection
- **Directory**: `modules/m0_intake/`
- **Purpose**: Ingests, normalizes, and extracts structured financial disclosures from loan agreements, sanction letters, and Key Fact Statements (KFS).
- **How It Works**:
  1. **Dual-Path Text Extraction**: Automatically inspects uploaded PDF documents. Native text-layer PDFs are parsed via `pdfplumber` and `PyMuPDF`. If text density drops below 50 characters per page (indicating scanned, photographed, or rasterized documents), the pipeline automatically triggers optical character recognition (OCR) fallback (`PaddleOCR`).
  2. **Statutory Structured Field Extraction**: Uses high-capacity LLMs (`llama-3.3-70b-versatile` via Groq) with an exhaustive system prompt to extract standardized RBI parameters across up to 25,000 characters without truncation. If the API is unavailable, deterministic regex fallbacks extract canonical terms.
  3. **Standardized RBI Parameters Extracted**:
     - `principal`, `disclosed_rate`, `tenure_months`, `processing_fee`, `net_disbursed_amount`
     - `monthly_emi` (EPI), `total_interest_amount`, `total_repayment_amount`, `apr`
     - `interest_type` (Floating/Fixed), `benchmark_rate`, `spread`, `reset_periodicity`
     - `prepayment_clause`, `penal_charges`, `bounce_charges`, `cooling_off_period`
     - `grievance_email`, `grievance_phone` (Principal Nodal Officer contact)
  4. **Automated Faulty / Incomplete KFS Detection**: Evaluates whether the submitted KFS document contains unpopulated placeholders, is blank, or omits mandatory statutory disclosures under RBI/2024-25/18. If critical parameters (Principal, Rate, or Tenor) are absent or zero, the system flags the document as **"Faulty or Incomplete — RBI Non-Compliant"** with an itemized deficiency list.

---

### Module 1: Deterministic APR Recomputation Engine
- **Directory**: `modules/m1_recompute/`
- **Purpose**: Serves as the single source of numeric financial truth across the entire platform. Implements 100% deterministic pure Python financial mathematics with zero machine learning to eliminate hallucination.
- **How It Works**:
  1. **Reducing-Balance Monthly EMI Calculation**:
     $$\text{EMI} = P \cdot r \cdot \frac{(1+r)^N}{(1+r)^N - 1}$$
     Where:
     - $P$ = Sanctioned Loan Principal
     - $R$ = Annual Disclosed Interest Rate (% p.a.)
     - $r = \frac{R}{12 \times 100}$ = Monthly Interest Rate
     - $N$ = Tenor in Months
  2. **Net Disbursed Amount Derivation**:
     $$\text{Net Disbursed} = \text{Sanctioned Principal} - \text{Total Upfront Fees \& Charges}$$
     Captures the regulatory requirement that while borrowers only receive net disbursed funds in their bank account, lenders charge interest on the gross sanctioned principal.
  3. **True Annual Percentage Rate (APR) via Numerical IRR Solver**:
     Solves for the monthly discount rate $r_{\text{irr}}$ satisfying the net cash flow equation:
     $$\text{Net Disbursed} = \sum_{t=1}^N \frac{\text{EMI}}{(1 + r_{\text{irr}})^t}$$
     Implemented using a high-precision numerical bisection solver ($< 10^{-7}$ tolerance, guaranteed convergence $\le 100$ iterations).
  4. **Annualized APR & Fee Impact**:
     $$\text{True APR} = r_{\text{irr}} \times 12 \times 100$$
     $$\text{Fee Drag} = \text{True APR} - \text{Disclosed Rate}$$
     If Fee Drag exceeds $+0.05\%$, an understated APR warning is emitted into the audit report.

---

### Module 1b: Serviceability & Debt-to-Income (DTI) Assessment
- **Directory**: `modules/m1b_serviceability/`
- **Purpose**: Evaluates borrower repayment capacity and cash flow resilience under standard underwriting principles.
- **How It Works**:
  1. **Fixed Obligation to Income Ratio (FOIR / DTI)**:
     $$\text{DTI} = \frac{\text{Existing Monthly Obligations} + \text{New Loan EMI}}{\text{Net Monthly Take-Home Income}}$$
  2. **Net Disposable Cash Flow Buffer**:
     $$\text{Disposable Buffer} = \text{Monthly Income} - \text{Total EMIs} - \text{Living Expenses}$$
  3. **Classification Bands**:
     - `serviceable`: $\text{DTI} \le 0.40$ and $\text{Disposable} > 0$ (Comfortable buffer).
     - `marginal`: $0.40 < \text{DTI} \le 0.50$ and $\text{Disposable} \ge 0$ (Vulnerable to income disruption).
     - `not-serviceable`: $\text{DTI} > 0.50$ or $\text{Disposable} < 0$ (High default risk).
  4. **Regulatory Honesty Invariant**: Explicitly marked in schemas, API outputs, and UI banners as an **industry underwriting heuristic, NOT an RBI regulatory mandate** (RULES.md §6.4).

---

### Module 2: 3-Way Consistency Checking & Discrepancy Matching
- **Directory**: `modules/m2_consistency/`
- **Purpose**: Detects contractual discrepancies, deceptive modifications, and bait-and-switch tactics by cross-verifying terms across three distinct sources: **Borrower Manual Terms**, **Terms & Conditions (T&C)**, and **Key Fact Statement (KFS)**.
- **How It Works**:
  1. **Tolerance-Based Numeric Matchers**:
     - Principal: Relative diff $\le 0.1\%$ or absolute diff $\le ₹10$.
     - Disclosed Rate: Absolute diff $\le 0.05\%$.
     - Tenor: Exact integer match ($0$ months tolerance).
     - Upfront Fees: Relative diff $\le 0.5\%$ or absolute diff $\le ₹10$.
  2. **Prose Clause Disagreement Detection**:
     - Evaluates legal clauses (e.g., prepayment penalties) using dense embeddings (`all-MiniLM-L6-v2`) and deterministic rule matching.
     - Automatically verifies compliance with RBI Master Directions (e.g., floating-rate term loans to individual borrowers cannot levy prepayment or foreclosure charges).
  3. **Non-Blocking Standalone Evaluation**: If only a KFS document is submitted without T&C, the engine evaluates internal statutory consistency rather than generating false missing errors.

---

### Module 3: Sacred Verification Gate & Dual Groundedness Verifier
- **Directory**: `modules/m3_verifier/`
- **Purpose**: The architectural cornerstone of GUARDIAN. Enforces that no factual claim, legal verdict, or financial explanation reaches user-facing presentation without passing dual verification.
- **How It Works**:
  1. **Numeric Verifier (`numeric_verifier.py`)**:
     - Extracts all numeric tokens, currency amounts, percentages, and time durations from claim text using strict regex parsers.
     - Cross-references each number against database ground truth (sanctioned principal, recomputed APR, monthly EMI, extracted KFS figures).
     - If any number deviates beyond configured tolerances, the claim is rejected as ungrounded.
  2. **Semantic Verifier (`semantic_verifier.py`)**:
     - Uses a pre-warmed cross-encoder Natural Language Inference (NLI) model (`cross-encoder/nli-deberta-v3-small` / `roberta-large-mnli`).
     - Evaluates the premise (retrieved evidence chunk from loan documents or RBI corpus) against the hypothesis (claim text).
     - Computes probabilities for `entailment`, `neutral`, and `contradiction`. A claim is verified only when entailment meets confidence thresholds and contradiction probability remains negligible.
  3. **Verification Verdicts**:
     - `grounded`: Safe to present to the borrower.
     - `contradiction` / `unverified_evidence`: Blocked or rendered with a high-priority warning disclaimer.

---

### Module 4: Vernacular Translation & Bidirectional Fidelity Verification
- **Directory**: `modules/m4_vernacular/`
- **Purpose**: Implements statutory protections under **RBI Annexure D (Vernacular Declaration)**, translating complex credit agreements and audit reports into regional Indian languages while preventing semantic distortion.
- **How It Works**:
  1. **Supported Languages**: Hindi (`hi`), Bengali (`bn`), Marathi (`mr`), Gujarati (`gu`), Kannada (`kn`), Telugu (`te`), Tamil (`ta`), Odia (`or`), Punjabi (`pa`), Malayalam (`ml`), Assamese (`as`), and Urdu (`ur`).
  2. **Bidirectional Translation & Back-Verification**:
     - Translates text from English into the target vernacular language.
     - Automatically translates the vernacular output back into English.
  3. **Fidelity Verification Metrics**:
     - **Numeric Preservation Rate**: Verifies that 100% of numerical values (rupee figures, tenors, percentages) remain unaltered.
     - **Semantic Drift Score**: Measures embedding distance between the original English and back-translated text.
     - **Clause Drop Rate**: Detects if critical legal caveats, statutory rights, or penalties were omitted during translation.

---

### Module 5: Evidence-Backed Grievance Redressal & CMS Dispute Generation
- **Directory**: `modules/m5_grievance/`
- **Purpose**: Empowers borrowers to formally contest illegal lending practices by generating legally binding dispute notices and complaints.
- **How It Works**:
  1. **Violation Classifier**: Automatically categorizes detected contractual defects under specific RBI regulatory violations:
     - Unlawful Prepayment Penalties on floating-rate loans.
     - Understated APR and undisclosed upfront fees.
     - Capitalization of penal charges (compounding penal interest).
     - Absence of mandatory look-up / cooling-off window.
     - Non-disclosure of Nodal Grievance Redressal Officer contact.
  2. **Formal Legal Notice Generator**:
     - Drafts a formal grievance letter addressed to the lender's Principal Nodal Officer (PNO).
     - Cites specific clause numbers and circular dates from RBI Master Directions.
     - Synthesizes exact evidence: original contract excerpts, recomputed APR proofs, and calculated excess interest.
  3. **RBI CMS Complaint Dossier**: Generates formatted submission packets for direct filing on the **RBI Complaint Management System (CMS)** under the Reserve Bank - Integrated Ombudsman Scheme.

---

### Module 6: Gated AI Advisory Chatbot
- **Directory**: `modules/m6_chatbot/`
- **Purpose**: Interactive, conversational financial advocate assisting borrowers with loan queries, legal rights, and financial decisions.
- **How It Works**:
  1. **RAG Context Retrieval**: Retrieves relevant clauses from the borrower's uploaded loan contract and the RBI regulatory corpus.
  2. **Strict Verification Routing**: Generated chatbot responses pass through the **Sacred Verification Gate (Module 3)** before rendering. If an answer contains ungrounded statements, the system flags the response with cautionary disclosures.
  3. **Contextual Awareness**: Incorporates real-time loan parameters (sanctioned principal, recomputed APR, amortization timeline) to provide personalized guidance.

---

### RAG Regulatory Knowledge Layer & Vector Store Security
- **Directory**: `rag/`
- **Purpose**: Maintains an authoritative semantic index of RBI lending guidelines.
- **How It Works**:
  1. **Regulatory Ingestion**: Ingests all 15 clauses from the *Reserve Bank of India Digital Lending Directions, 2025* into ChromaDB (`rbi_corpus` collection).
  2. **100% Retrieval Benchmark**: Validated against canonical regulatory benchmark queries with 100% precision.
  3. **Single Choke-Point Security Wrapper (`rag/chroma_client.py`)**: ChromaDB lacks native row-level security. A centralized client wrapper enforces mandatory, non-empty `{user_id, loan_id}` metadata filtering on all document queries. Cross-tenant leakage tests verify that User B cannot retrieve User A's confidential financial terms.

---

### Pipeline State Machine Orchestration
- **Directory**: `app/orchestration/pipeline.py`
- **Purpose**: Coordinates all modules into an atomic, observable, multi-stage state machine.
- **How It Works**:
  Executes the canonical pipeline flow with microsecond latency tracking:
  $$\text{INGESTING} \rightarrow \text{EXTRACTING} \rightarrow \text{CONSISTENCY\_CHECKING} \rightarrow \text{RECOMPUTING\_SERVICEABILITY} \rightarrow \text{GENERATING\_CLAIMS} \rightarrow \text{RETRIEVING\_EVIDENCE} \rightarrow \text{VERIFYING\_CLAIMS} \rightarrow \text{TRANSLATING} \rightarrow \text{RESPONDING}$$

---

### Frontend Web Application & Interactive Analytics Suite
- **Directory**: `frontend/`
- **Built With**: Next.js 16 (App Router), React 19, TailwindCSS v4, Lucide React.
- **Key Capabilities**:
  1. **Workflow Structure**:
     - **Step 1: Loan Details**: Baseline manual terms registration.
     - **Step 2: Document Upload**: Upload KFS PDF and optional T&C PDF, with optional Annexure D vernacular language selection. Serviceability inputs are excluded here so the full verification report is shown first.
     - **Step 3: Full Verification Report**: Displays the compliance verdict, KFS Mandatory Disclosure Schedule, 3-Way Consistency Check, Vernacular Verification, Claim Verification Gate, and Step-by-Step Mathematical Calculation Breakdown.
     - **Step 4: Financial Serviceability & Prepayment Simulator**: Interactive financial suite with the live dual-curve payoff graph and full year-by-year amortization schedule.
  2. **Full Year-by-Year Amortization Schedule**:
     - Displays every single year of the loan from Year 1 to the final maturity year.
     - Columns: Year, Opening Principal, Total Annual Payment, Principal Repaid, Interest Paid, Closing Balance, % Repaid Progress Bar.
     - Summary footer aggregating lifetime repayment totals.
  3. **Interactive Prepayment Simulator**:
     - Simulates scenarios: **1 Extra EMI / Year (13th EMI)**, **Annual Step-Up (5%–15%)**, **Custom Extra Monthly Amount**, and **Lump Sum Prepayment**.
     - Calculates Fast-Track Tenure (months/years saved) and Total Interest Saved (₹).
  4. **Updated Dual-Curve Payoff Graph**:
     - Responsive SVG chart overlaying the Baseline Principal Curve with the Simulated Accelerated Prepayment Curve.
     - Visual marker indicating the exact year the loan balance reaches ₹0.
     - Provides three table views: Simulated Fast-Track Schedule, Original Baseline Schedule, and Side-by-Side Annual Comparison.
  5. **Economic Reality Check: Loan ROI vs. Current Inflation (~5.5%)**:
     - Evaluates the Real Cost of Debt: $\text{Nominal Rate} - \text{CPI Inflation (5.5\%)}$.
     - Housing Loans ($\le 9.25\%$): Demonstrates that with tax relief and inflation, real debt cost is ~1.5%–3.0%. Illustrates opportunity cost: systematically investing surplus cash into equity index funds (Nifty 50 historical 12%–14% CAGR) often creates greater long-term net wealth than aggressive prepayment.
     - High-Interest Loans ($> 11.5\%$): Personal and digital credit. Recommends aggressive prepayment to capture a guaranteed, risk-free return matching the loan rate.
  6. **Certified Report Export**:
     - Print-ready PDF report layout (`window.print()`).
     - Structured JSON audit certificate download.

---

## 📐 Mathematical Specifications & Formulas

| Metric | Formula | Method / Algorithm |
|---|---|---|
| **Reducing-Balance EMI** | $\text{EMI} = P \cdot r \cdot \frac{(1+r)^N}{(1+r)^N - 1}$ | Pure deterministic arithmetic |
| **Net Disbursed Cash** | $\text{Principal} - \text{Total Upfront Fees}$ | Upfront deduction model |
| **True Effective APR** | $\text{Net Disbursed} = \sum_{t=1}^N \frac{\text{EMI}}{(1+r_{\text{irr}})^t}$ | Numerical Bisection IRR Solver ($< 10^{-7}$ tolerance) |
| **Fee Drag on APR** | $\text{True APR} - \text{Disclosed Interest Rate}$ | Direct percentage delta |
| **FOIR / DTI Ratio** | $\frac{\text{Existing EMIs} + \text{New EMI}}{\text{Net Monthly Income}}$ | Debt-to-income heuristic |
| **Real Cost of Debt** | $\text{Nominal Interest Rate} - \text{CPI Inflation (5.5\%)}$ | Fisher equation approximation |

---

## 🗂️ Repository Structure

```
guardian/
├── app/                              # FastAPI Application Core
│   ├── core/                         # Config, Logging, Security
│   ├── models/                       # Database ORM / Table Definitions
│   ├── orchestration/                # Pipeline State Machine (pipeline.py)
│   ├── routers/                      # REST Endpoints (health, loans, docs, audit, etc.)
│   └── schemas/                      # Pydantic v2 Contracts & Canonical Claim
├── data/
│   ├── raw/                          # RBI Master Directions, Test PDFs
│   └── test_cases/                   # Benchmark Truth Datasets
├── frontend/                         # Next.js 16 Web Application
│   ├── src/app/                      # App Router Pages (dashboard, analysis, disputes, chat)
│   ├── src/components/               # UI Components (LoanAnalytics.tsx, Navbar, etc.)
│   └── src/lib/                      # API Client & Supabase SDK
├── modules/                          # Domain Engine Modules
│   ├── m0_intake/                    # Intake, OCR Fallback & Extraction
│   ├── m1_recompute/                 # Deterministic APR & EMI Recompute
│   ├── m1b_serviceability/           # DTI & Disposable Income Assessment
│   ├── m2_consistency/               # 3-Way Consistency Checking
│   ├── m3_verifier/                  # Dual Groundedness Verification Gate
│   ├── m4_vernacular/                # Vernacular Translation & Verification
│   ├── m5_grievance/                 # Grievance Notice & RBI CMS Dossiers
│   └── m6_chatbot/                   # Verification-Gated Advisory Chatbot
├── rag/                              # Vector Retrieval & Regulatory Knowledge
│   ├── chroma_client.py              # Scoped ChromaDB Security Wrapper
│   └── ingest_rbi_corpus.py          # RBI Corpus Ingestion Script
├── tests/                            # Automated Pytest Test Suite
├── docker-compose.yml                # ChromaDB Container Definition
├── requirements.txt                  # Python Core Dependencies
├── requirements-ml.txt               # ML / Vector / NLP Dependencies
├── requirements-dev.txt              # Test & Linting Dependencies
└── README.md                         # Project Documentation
```

---

## 🚀 Getting Started & Execution Guide

### 1. Prerequisites
- **Operating System**: Windows, Linux, or macOS.
- **Python**: Python 3.11.x (configured in virtual environment `venv/`).
- **Node.js**: Node.js v18 or newer.
- **Docker**: Docker Desktop (for local ChromaDB).

### 2. Environment Configuration

#### Backend API (`.env` in root)
```ini
ENVIRONMENT=development
DATABASE_URL=postgresql://postgres:[PASSWORD]@[HOST]:6543/postgres?sslmode=require
SUPABASE_URL=https://[YOUR_INSTANCE].supabase.co
SUPABASE_ANON_KEY=eyJ...
SUPABASE_SERVICE_ROLE_KEY=eyJ...
CHROMA_HOST=localhost
CHROMA_PORT=8000
GROQ_API_KEY=gsk_...
GROQ_MODEL=llama-3.3-70b-versatile
```

#### Frontend UI (`frontend/.env.local`)
```ini
NEXT_PUBLIC_API_URL="http://localhost:8080/api/v1"
NEXT_PUBLIC_SUPABASE_URL="https://[YOUR_INSTANCE].supabase.co"
NEXT_PUBLIC_SUPABASE_ANON_KEY="eyJ..."
```

### 3. Starting ChromaDB
```powershell
docker compose up -d
```

### 4. Ingesting the RBI Regulatory Corpus
```powershell
.\venv\Scripts\python.exe -m rag.ingest_rbi_corpus
```

### 5. Running the Backend Server
```powershell
.\venv\Scripts\uvicorn app.main:app --host 127.0.0.1 --port 8080 --reload
```
Interactive API documentation:
- **Swagger UI**: [http://127.0.0.1:8080/docs](http://127.0.0.1:8080/docs)
- **Health Check**: [http://127.0.0.1:8080/api/v1/health](http://127.0.0.1:8080/api/v1/health)

### 6. Starting the Frontend UI
```powershell
cd frontend
npm install
npm run dev
```
Web application interface: [http://localhost:3000](http://localhost:3000).

---

## 🔍 API Endpoints Reference

| Method | Endpoint | Description | Module |
|---|---|---|---|
| `GET` | `/api/v1/health` | Service health, Supabase DB check, ChromaDB status | Core |
| `POST` | `/api/v1/loans` | Register a new loan profile | Module 0 |
| `GET` | `/api/v1/loans` | List loans for the authenticated user | Module 0 |
| `POST` | `/api/v1/loans/{id}/terms` | Save manual borrower loan terms | Module 0 |
| `POST` | `/api/v1/loans/{id}/documents/upload` | Upload PDF (T&C or KFS) with dual-path OCR extraction | Module 0 |
| `POST` | `/api/v1/loans/{id}/recompute` | Execute reducing-balance EMI and true APR IRR solver | Module 1 |
| `POST` | `/api/v1/loans/{id}/serviceability` | Calculate DTI ratio and disposable income | Module 1b |
| `POST` | `/api/v1/loans/{id}/consistency` | Execute 3-way consistency check and detect mismatches | Module 2 |
| `POST` | `/api/v1/loans/{id}/verify` | Run dual numeric & RoBERTa-MNLI groundedness check | Module 3 |
| `POST` | `/api/v1/loans/{id}/vernacular` | Translate text with bidirectional back-verification | Module 4 |
| `POST` | `/api/v1/loans/{id}/disputes` | Generate legal dispute notice for Principal Nodal Officer | Module 5 |
| `POST` | `/api/v1/chat` | Chat with RAG-grounded, verification-gated advisor | Module 6 |
| `POST` | `/api/v1/loans/{id}/pipeline` | Run complete end-to-end verification pipeline | Orchestration |

---

## 🛡️ Binding System Invariants (RULES.md)

1. **Sacred Verification Gate (RULES.md §1)**: No claim reaches user-facing presentation without a verification verdict from Module 3. Unverified statements must be blocked or prominently flagged with warning disclaimers.
2. **Single Source of Math (RULES.md §1.7)**: Exactly one implementation of financial math (`apr_recompute.py`) exists across the entire repository.
3. **Cross-Tenant Vector Isolation (RULES.md §2)**: ChromaDB access must pass through `rag/chroma_client.py` with mandatory `{user_id, loan_id}` metadata scoping.
4. **Append-Only Audit Trail (RULES.md §3 S-21)**: All audit records and compliance checks are written to an immutable `audit_log` table.
5. **Regulatory Honesty (RULES.md §6.4)**: Underwriting rules such as DTI thresholds are always labeled as industry heuristics, never as RBI mandates.

---

## 📄 License
This project is licensed for academic, research, and regulatory technology evaluation purposes.
