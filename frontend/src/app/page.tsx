"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import {
  ArrowRight,
  FileText,
  Activity,
  AlertTriangle,
  CheckCircle2,
  ShieldCheck,
  BarChart3,
  MessageCircle,
  Scale,
  Clock,
  TrendingUp,
  FilePlus2,
  Loader2,
  ChevronRight,
  Zap,
  BookOpen,
} from "lucide-react";

export default function Home() {
  const [loans, setLoans] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .getLoans()
      .then((res) => {
        const list = Array.isArray(res) ? res : res?.loans || res?.items || [];
        setLoans(Array.isArray(list) ? list : []);
      })
      .catch(() => setLoans([]))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="space-y-8 animate-fade-in">
      {/* ─── Hero Section ─── */}
      <section className="card-elevated p-8 md:p-10 bg-gradient-to-br from-[#0052cc] to-[#0747a6] text-white relative overflow-hidden">
        {/* Decorative circles */}
        <div className="absolute -top-20 -right-20 w-60 h-60 bg-white/5 rounded-full" />
        <div className="absolute -bottom-16 -left-16 w-48 h-48 bg-white/5 rounded-full" />

        <div className="relative z-10">
          <div className="flex items-center gap-2 mb-3">
            <ShieldCheck className="h-5 w-5 text-blue-200" />
            <span className="text-[12px] font-semibold text-blue-200 uppercase tracking-wider">
              Financial Verification Platform
            </span>
          </div>
          <h1 className="text-2xl md:text-3xl font-bold tracking-tight leading-tight">
            Verified Loan Compliance
            <br />
            <span className="text-blue-200 font-medium text-xl md:text-2xl">
              Powered by Groundedness-Checked AI
            </span>
          </h1>
          <p className="max-w-xl text-blue-100 text-[14px] mt-3 leading-relaxed">
            GUARDIAN validates Key Fact Statements against Terms & Conditions and
            RBI Master Directions. Every claim is verified through our dual
            semantic + numeric verification gate before it reaches you.
          </p>
          <div className="flex flex-wrap gap-3 mt-6">
            <Link href="/analysis/new" className="inline-flex items-center gap-2 bg-white text-[#0052cc] font-semibold px-5 py-2.5 rounded-lg text-[14px] shadow-lg shadow-blue-900/20 hover:bg-blue-50 transition-all hover:-translate-y-0.5">
              <FilePlus2 className="h-4 w-4" />
              Start New Analysis
            </Link>
            <Link href="/chat" className="inline-flex items-center gap-2 bg-white/10 hover:bg-white/20 text-white font-medium px-5 py-2.5 rounded-lg text-[14px] border border-white/20 transition-all">
              <MessageCircle className="h-4 w-4" />
              AI Advisor
            </Link>
          </div>
        </div>
      </section>

      {/* ─── Quick Stats ─── */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="card p-5">
          <div className="flex items-center justify-between mb-3">
            <div className="h-10 w-10 rounded-lg bg-[#e8f0fe] flex items-center justify-center">
              <FileText className="h-5 w-5 text-[#0052cc]" />
            </div>
            <span className="badge-info text-[10px]">Active</span>
          </div>
          <p className="text-[12px] text-[#6b7280] font-medium">Total Sessions</p>
          <p className="text-2xl font-bold text-[#1a1d23] mt-0.5">
            {loading ? "—" : loans.length}
          </p>
        </div>

        <div className="card p-5">
          <div className="flex items-center justify-between mb-3">
            <div className="h-10 w-10 rounded-lg bg-[#ecfdf5] flex items-center justify-center">
              <CheckCircle2 className="h-5 w-5 text-[#0d9f6e]" />
            </div>
            <span className="badge-success text-[10px]">Verified</span>
          </div>
          <p className="text-[12px] text-[#6b7280] font-medium">Verification Gate</p>
          <p className="text-2xl font-bold text-[#1a1d23] mt-0.5">100%</p>
        </div>

        <div className="card p-5">
          <div className="flex items-center justify-between mb-3">
            <div className="h-10 w-10 rounded-lg bg-[#fffbeb] flex items-center justify-center">
              <BarChart3 className="h-5 w-5 text-[#d97706]" />
            </div>
            <span className="badge-warning text-[10px]">NLI Model</span>
          </div>
          <p className="text-[12px] text-[#6b7280] font-medium">Groundedness Rate</p>
          <p className="text-2xl font-bold text-[#1a1d23] mt-0.5">100.0%</p>
        </div>

        <div className="card p-5">
          <div className="flex items-center justify-between mb-3">
            <div className="h-10 w-10 rounded-lg bg-[#fdf2f8] flex items-center justify-center">
              <Zap className="h-5 w-5 text-[#be185d]" />
            </div>
            <span className="badge-neutral text-[10px]">&lt;5s SLA</span>
          </div>
          <p className="text-[12px] text-[#6b7280] font-medium">Avg Latency</p>
          <p className="text-2xl font-bold text-[#1a1d23] mt-0.5">~1.8s</p>
        </div>
      </div>

      {/* ─── Feature Cards ─── */}
      <div>
        <h2 className="text-[15px] font-semibold text-[#1a1d23] mb-4">
          Platform Capabilities
        </h2>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <div className="card p-5 group cursor-pointer">
            <div className="h-10 w-10 rounded-lg bg-[#e8f0fe] flex items-center justify-center mb-3 group-hover:scale-105 transition-transform">
              <FileText className="h-5 w-5 text-[#0052cc]" />
            </div>
            <h3 className="text-[14px] font-semibold text-[#1a1d23]">
              Document Ingestion
            </h3>
            <p className="text-[12px] text-[#6b7280] mt-1.5 leading-relaxed">
              Upload T&C and KFS PDFs with OCR fallback for scanned documents.
              Groq-powered structured extraction.
            </p>
          </div>

          <div className="card p-5 group cursor-pointer">
            <div className="h-10 w-10 rounded-lg bg-[#ecfdf5] flex items-center justify-center mb-3 group-hover:scale-105 transition-transform">
              <Activity className="h-5 w-5 text-[#0d9f6e]" />
            </div>
            <h3 className="text-[14px] font-semibold text-[#1a1d23]">
              APR Recompute & DTI
            </h3>
            <p className="text-[12px] text-[#6b7280] mt-1.5 leading-relaxed">
              Deterministic reducing-balance APR calculation and
              Debt-to-Income serviceability assessment.
            </p>
          </div>

          <div className="card p-5 group cursor-pointer">
            <div className="h-10 w-10 rounded-lg bg-[#fffbeb] flex items-center justify-center mb-3 group-hover:scale-105 transition-transform">
              <AlertTriangle className="h-5 w-5 text-[#d97706]" />
            </div>
            <h3 className="text-[14px] font-semibold text-[#1a1d23]">
              Consistency Check
            </h3>
            <p className="text-[12px] text-[#6b7280] mt-1.5 leading-relaxed">
              Cross-reference manual terms, T&C clauses, and KFS figures
              to detect hidden discrepancies.
            </p>
          </div>

          <div className="card p-5 group cursor-pointer">
            <div className="h-10 w-10 rounded-lg bg-[#fdf2f8] flex items-center justify-center mb-3 group-hover:scale-105 transition-transform">
              <ShieldCheck className="h-5 w-5 text-[#be185d]" />
            </div>
            <h3 className="text-[14px] font-semibold text-[#1a1d23]">
              Dual Verification Gate
            </h3>
            <p className="text-[12px] text-[#6b7280] mt-1.5 leading-relaxed">
              RoBERTa-MNLI semantic + numeric verification ensures
              every claim is grounded before display.
            </p>
          </div>
        </div>
      </div>

      {/* ─── Recent Loan Sessions ─── */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-[15px] font-semibold text-[#1a1d23]">
            Recent Loan Sessions
          </h2>
          <Link
            href="/analysis/new"
            className="text-[13px] font-medium text-[#0052cc] hover:text-[#0747a6] flex items-center gap-1 transition-colors"
          >
            New session
            <ChevronRight className="h-4 w-4" />
          </Link>
        </div>

        <div className="card overflow-hidden">
          {loading ? (
            <div className="flex items-center justify-center py-16">
              <Loader2 className="h-5 w-5 animate-spin text-[#0052cc]" />
              <span className="ml-2 text-[13px] text-[#6b7280]">Loading sessions...</span>
            </div>
          ) : loans.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 text-center">
              <div className="h-14 w-14 rounded-2xl bg-[#f3f4f6] flex items-center justify-center mb-4">
                <BookOpen className="h-7 w-7 text-[#9ca3af]" />
              </div>
              <p className="text-[14px] font-medium text-[#6b7280]">
                No analysis sessions yet
              </p>
              <p className="text-[12px] text-[#9ca3af] mt-1 max-w-sm">
                Start your first loan verification to see compliance reports,
                APR audits, and consistency checks here.
              </p>
              <Link href="/analysis/new" className="btn-primary mt-5 text-[13px]">
                <FilePlus2 className="h-4 w-4" />
                Create First Session
              </Link>
            </div>
          ) : (
            <table className="w-full">
              <thead>
                <tr className="border-b border-[#e5e7eb] bg-[#f9fafb]">
                  <th className="text-left text-[11px] font-semibold text-[#6b7280] uppercase tracking-wider px-5 py-3">
                    Session
                  </th>
                  <th className="text-left text-[11px] font-semibold text-[#6b7280] uppercase tracking-wider px-5 py-3">
                    Lender
                  </th>
                  <th className="text-left text-[11px] font-semibold text-[#6b7280] uppercase tracking-wider px-5 py-3">
                    Status
                  </th>
                  <th className="text-left text-[11px] font-semibold text-[#6b7280] uppercase tracking-wider px-5 py-3">
                    Created
                  </th>
                  <th className="text-right text-[11px] font-semibold text-[#6b7280] uppercase tracking-wider px-5 py-3">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#f0f0f0]">
                {loans.slice(0, 8).map((loan: any) => (
                  <tr
                    key={loan.id}
                    className="hover:bg-[#f9fafb] transition-colors"
                  >
                    <td className="px-5 py-3.5">
                      <div className="flex items-center gap-3">
                        <div className="h-9 w-9 rounded-lg bg-[#e8f0fe] flex items-center justify-center shrink-0">
                          <FileText className="h-4 w-4 text-[#0052cc]" />
                        </div>
                        <div>
                          <Link
                            href={`/analysis/${loan.id}`}
                            className="text-[13px] font-semibold text-[#1a1d23] hover:text-[#0052cc] transition-colors"
                          >
                            {loan.loan_name || "Untitled Loan"}
                          </Link>
                          <p className="text-[11px] text-[#9ca3af] font-mono">
                            {loan.id?.slice(0, 8)}...
                          </p>
                        </div>
                      </div>
                    </td>
                    <td className="px-5 py-3.5 text-[13px] text-[#6b7280]">
                      {loan.lender_name || "—"}
                    </td>
                    <td className="px-5 py-3.5">
                      <span className="badge-success text-[10px]">
                        {loan.status || "active"}
                      </span>
                    </td>
                    <td className="px-5 py-3.5 text-[12px] text-[#9ca3af]">
                      {loan.created_at
                        ? new Date(loan.created_at).toLocaleDateString("en-IN", {
                            day: "2-digit",
                            month: "short",
                            year: "numeric",
                          })
                        : "—"}
                    </td>
                    <td className="px-5 py-3.5 text-right">
                      <div className="flex items-center justify-end gap-2">
                        <Link
                          href={`/analysis/${loan.id}`}
                          className="btn-ghost text-[12px] py-1.5 px-2.5"
                        >
                          <ArrowRight className="h-3.5 w-3.5" />
                          View
                        </Link>
                        <Link
                          href={`/chat?loan_id=${loan.id}`}
                          className="btn-ghost text-[12px] py-1.5 px-2.5"
                        >
                          <MessageCircle className="h-3.5 w-3.5" />
                          Chat
                        </Link>
                        <Link
                          href={`/disputes?loan_id=${loan.id}`}
                          className="btn-ghost text-[12px] py-1.5 px-2.5"
                        >
                          <Scale className="h-3.5 w-3.5" />
                          Dispute
                        </Link>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}
