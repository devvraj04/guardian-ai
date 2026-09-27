-- ==============================================================================
-- GUARDIAN Database Schema Migration (Phase 0)
-- 14 Tables with PostgreSQL 15, Supabase Auth integration, and Strict RLS
-- Security Rules: S-3 (Row-level auth), S-7 (No raw SQL), S-13 (pgcrypto),
-- S-21/S-22 (Append-only audit_log, no UPDATE/DELETE permitted)
-- ==============================================================================

-- Enable pgcrypto for encryption at rest / UUID generation (S-13)
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- 1. User Profiles (Mirrors Supabase auth.users)
CREATE TABLE IF NOT EXISTS public.users (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT UNIQUE,
    full_name TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now()),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

-- 2. Loans
CREATE TABLE IF NOT EXISTS public.loans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    loan_name TEXT NOT NULL,
    lender_name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

-- 3. Loan Manual Terms (Entered by user)
CREATE TABLE IF NOT EXISTS public.loan_manual_terms (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    loan_id UUID NOT NULL REFERENCES public.loans(id) ON DELETE CASCADE,
    principal NUMERIC(15, 2) NOT NULL,
    disclosed_rate NUMERIC(6, 3) NOT NULL,
    tenure_months INTEGER NOT NULL,
    fees NUMERIC(12, 2) NOT NULL DEFAULT 0.0,
    entered_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

-- 4. Loan Documents (T&C and KFS storage references)
CREATE TABLE IF NOT EXISTS public.loan_documents (
    doc_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    loan_id UUID NOT NULL REFERENCES public.loans(id) ON DELETE CASCADE,
    doc_type TEXT NOT NULL CHECK (doc_type IN ('tnc', 'kfs')),
    storage_path TEXT NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    uploaded_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

-- 5. Extracted Fields (Extracted from T&C / KFS via OCR/LLM)
CREATE TABLE IF NOT EXISTS public.extracted_fields (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    doc_id UUID NOT NULL REFERENCES public.loan_documents(doc_id) ON DELETE CASCADE,
    field_name TEXT NOT NULL,
    extracted_value JSONB NOT NULL,
    confidence NUMERIC(4, 3) NOT NULL,
    extraction_method TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

-- 6. Consistency Checks (Cross-source comparison)
CREATE TABLE IF NOT EXISTS public.consistency_checks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    loan_id UUID NOT NULL REFERENCES public.loans(id) ON DELETE CASCADE,
    field_name TEXT NOT NULL,
    manual_value JSONB,
    tnc_value JSONB,
    kfs_value JSONB,
    match_status TEXT NOT NULL CHECK (match_status IN ('match', 'mismatch', 'missing')),
    checked_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

-- 7. Income & Expense Inputs (Serviceability inputs)
CREATE TABLE IF NOT EXISTS public.income_expense_inputs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    loan_id UUID NOT NULL REFERENCES public.loans(id) ON DELETE CASCADE,
    monthly_income NUMERIC(15, 2) NOT NULL,
    existing_emis NUMERIC(15, 2) NOT NULL DEFAULT 0.0,
    monthly_expenses NUMERIC(15, 2) NOT NULL DEFAULT 0.0,
    entered_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

-- 8. Serviceability Results (Module 1b deterministic outputs)
CREATE TABLE IF NOT EXISTS public.serviceability_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    loan_id UUID NOT NULL REFERENCES public.loans(id) ON DELETE CASCADE,
    dti_ratio NUMERIC(6, 4) NOT NULL,
    disposable_income NUMERIC(15, 2) NOT NULL,
    verdict TEXT NOT NULL CHECK (verdict IN ('serviceable', 'marginal', 'not-serviceable')),
    computed_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

-- 9. Claims (The single canonical Claim store)
CREATE TABLE IF NOT EXISTS public.claims (
    claim_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_module TEXT NOT NULL CHECK (source_module IN ('recompute', 'consistency', 'serviceability', 'chatbot', 'grievance')),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    loan_id UUID NOT NULL REFERENCES public.loans(id) ON DELETE CASCADE,
    claim_text TEXT NOT NULL,
    supporting_figures JSONB NOT NULL DEFAULT '{}'::jsonb,
    source_record_id TEXT NOT NULL,
    generated_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now()),
    verification_status TEXT NOT NULL DEFAULT 'pending' CHECK (verification_status IN ('pending', 'grounded', 'flagged'))
);

-- 10. Verification Results (The Module 3 Sacred Verification Gate)
CREATE TABLE IF NOT EXISTS public.verification_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    claim_id UUID NOT NULL REFERENCES public.claims(claim_id) ON DELETE CASCADE,
    semantic_verdict TEXT NOT NULL,
    numeric_verdict TEXT NOT NULL,
    final_verdict TEXT NOT NULL CHECK (final_verdict IN ('grounded', 'flagged')),
    error_type TEXT,
    verified_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

-- 11. Disputes (Grievances)
CREATE TABLE IF NOT EXISTS public.disputes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    loan_id UUID NOT NULL REFERENCES public.loans(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    category TEXT NOT NULL,
    free_text TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'submitted',
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

-- 12. Chat Sessions
CREATE TABLE IF NOT EXISTS public.chat_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    loan_id UUID NOT NULL REFERENCES public.loans(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

-- 13. Chat Messages
CREATE TABLE IF NOT EXISTS public.chat_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES public.chat_sessions(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    claim_id UUID REFERENCES public.claims(claim_id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

-- 14. Append-Only Audit Log (RULES.md §3 S-21, S-22)
CREATE TABLE IF NOT EXISTS public.audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    action TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

-- Strictly prevent any UPDATE or DELETE on audit_log
CREATE OR REPLACE RULE audit_log_no_update AS ON UPDATE TO public.audit_log DO INSTEAD NOTHING;
CREATE OR REPLACE RULE audit_log_no_delete AS ON DELETE TO public.audit_log DO INSTEAD NOTHING;

-- ==============================================================================
-- ROW-LEVEL SECURITY (RLS) POLICIES (RULES.md §3 S-3)
-- ==============================================================================

ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.loans ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.loan_manual_terms ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.loan_documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.extracted_fields ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.consistency_checks ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.income_expense_inputs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.serviceability_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.claims ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.verification_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.disputes ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.chat_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.chat_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.audit_log ENABLE ROW LEVEL SECURITY;

-- users policies
CREATE POLICY "users_select_own" ON public.users FOR SELECT USING (auth.uid() = id);
CREATE POLICY "users_update_own" ON public.users FOR UPDATE USING (auth.uid() = id);

-- loans policies
CREATE POLICY "loans_all_own" ON public.loans FOR ALL USING (auth.uid() = user_id);

-- loan_manual_terms policies
CREATE POLICY "loan_manual_terms_all_own" ON public.loan_manual_terms FOR ALL USING (
    EXISTS (SELECT 1 FROM public.loans WHERE loans.id = loan_manual_terms.loan_id AND loans.user_id = auth.uid())
);

-- loan_documents policies
CREATE POLICY "loan_documents_all_own" ON public.loan_documents FOR ALL USING (
    EXISTS (SELECT 1 FROM public.loans WHERE loans.id = loan_documents.loan_id AND loans.user_id = auth.uid())
);

-- extracted_fields policies
CREATE POLICY "extracted_fields_all_own" ON public.extracted_fields FOR ALL USING (
    EXISTS (
        SELECT 1 FROM public.loan_documents
        JOIN public.loans ON loans.id = loan_documents.loan_id
        WHERE loan_documents.doc_id = extracted_fields.doc_id AND loans.user_id = auth.uid()
    )
);

-- consistency_checks policies
CREATE POLICY "consistency_checks_all_own" ON public.consistency_checks FOR ALL USING (
    EXISTS (SELECT 1 FROM public.loans WHERE loans.id = consistency_checks.loan_id AND loans.user_id = auth.uid())
);

-- income_expense_inputs policies
CREATE POLICY "income_expense_inputs_all_own" ON public.income_expense_inputs FOR ALL USING (
    EXISTS (SELECT 1 FROM public.loans WHERE loans.id = income_expense_inputs.loan_id AND loans.user_id = auth.uid())
);

-- serviceability_results policies
CREATE POLICY "serviceability_results_all_own" ON public.serviceability_results FOR ALL USING (
    EXISTS (SELECT 1 FROM public.loans WHERE loans.id = serviceability_results.loan_id AND loans.user_id = auth.uid())
);

-- claims policies
CREATE POLICY "claims_all_own" ON public.claims FOR ALL USING (auth.uid() = user_id);

-- verification_results policies
CREATE POLICY "verification_results_select_own" ON public.verification_results FOR SELECT USING (
    EXISTS (SELECT 1 FROM public.claims WHERE claims.claim_id = verification_results.claim_id AND claims.user_id = auth.uid())
);
CREATE POLICY "verification_results_insert_service" ON public.verification_results FOR INSERT WITH CHECK (
    EXISTS (SELECT 1 FROM public.claims WHERE claims.claim_id = verification_results.claim_id AND claims.user_id = auth.uid())
);

-- disputes policies
CREATE POLICY "disputes_all_own" ON public.disputes FOR ALL USING (auth.uid() = user_id);

-- chat_sessions policies
CREATE POLICY "chat_sessions_all_own" ON public.chat_sessions FOR ALL USING (auth.uid() = user_id);

-- chat_messages policies
CREATE POLICY "chat_messages_all_own" ON public.chat_messages FOR ALL USING (
    EXISTS (SELECT 1 FROM public.chat_sessions WHERE chat_sessions.id = chat_messages.session_id AND chat_sessions.user_id = auth.uid())
);

-- audit_log policies: S-22 Readable by owner, insert-only, no update/delete
CREATE POLICY "audit_log_select_own" ON public.audit_log FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "audit_log_insert_user" ON public.audit_log FOR INSERT WITH CHECK (auth.uid() = user_id OR user_id IS NULL);
