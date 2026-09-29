"use client";

import { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { api } from "@/lib/api";
import {
  Loader2,
  ArrowLeft,
  FileText,
  Building2,
  Clock,
  CheckCircle2,
  AlertTriangle,
  MessageCircle,
  Scale,
  TrendingUp,
  Banknote,
  Calendar,
  Percent,
  ShieldCheck,
  BarChart3,
  Zap,
  RefreshCw,
} from "lucide-react";

export default function LoanDetailPage() {
  const params = useParams();
  const loanId = params?.id as string;

  const [loan, setLoan] = useState<any>(null);
  const [terms, setTerms] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [pipelineResult, setPipelineResult] = useState<any>(null);
  const [analyzing, setAnalyzing] = useState(false);

  useEffect(() => {
    if (!loanId) return;
    const fetchData = async () => {
      try {
        setLoading(true);
        const [loanData, termsData] = await Promise.all([
          api.getLoan(loanId),
          api.getLoanTerms(loanId).catch(() => null),
        ]);
        setLoan(loanData);
        setTerms(termsData);
      } catch (e: any) {
        setError(e.message || "Failed to load loan details");
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [loanId]);

  const handleRunPipeline = async () => {
    try {
      setAnalyzing(true);
      setError(null);
      const result = await api.runPipeline(loanId);
      setPipelineResult(result);
    } catch (e: any) {
      setError(e.message || "Pipeline execution failed");
    } finally {
      setAnalyzing(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24">
        <Loader2 className="h-6 w-6 animate-spin text-[#0052cc]" />
        <span className="ml-3 text-[14px] text-[#6b7280]">Loading loan details...</span>
      </div>
    );
  }

  if (error && !loan) {
    return (
      <div className="max-w-4xl mx-auto space-y-4 animate-fade-in">
        <div className="flex items-center gap-2 p-4 rounded-xl bg-[#fef2f2] border border-[#fecaca] text-[13px] text-[#991b1b]">
          <AlertTriangle className="h-5 w-5 shrink-0" />
          {error}
        </div>
        <Link href="/" className="btn-ghost">
          <ArrowLeft className="h-4 w-4" /> Back to Dashboard
        </Link>
      </div>
    );
  }

  const apr = pipelineResult?.apr_result;
  const svc = pipelineResult?.serviceability_result;
  const cons = pipelineResult?.consistency_result;

  return (
    <div className="max-w-4xl mx-auto space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <Link href="/" className="text-[12px] text-[#6b7280] hover:text-[#0052cc] flex items-center gap-1 mb-2 transition-colors">
            <ArrowLeft className="h-3 w-3" /> Back to Dashboard
          </Link>
          <h1 className="text-xl font-bold text-[#1a1d23]">
            {loan?.loan_name || "Loan Detail"}
          </h1>
          <p className="text-[13px] text-[#6b7280] mt-0.5 flex items-center gap-2">
            <Building2 className="h-3.5 w-3.5" />
            {loan?.lender_name}
            <span className="text-[#d1d5db]">·</span>
            <span className="font-mono text-[11px] text-[#9ca3af]">{loanId?.slice(0, 12)}...</span>
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="badge-success text-[11px]">
            <span className="status-dot status-dot-success mr-1" />
            {loan?.status || "Active"}
          </span>
        </div>
      </div>

      {/* Loan & Terms Overview */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        <div className="card p-5 space-y-4">
          <h3 className="text-[14px] font-semibold text-[#1a1d23] flex items-center gap-2">
            <FileText className="h-4 w-4 text-[#0052cc]" />
            Loan Profile
          </h3>
          <div className="space-y-3">
            <div className="flex justify-between text-[13px]">
              <span className="text-[#6b7280]">Loan Name</span>
              <span className="font-medium text-[#1a1d23]">{loan?.loan_name}</span>
            </div>
            <div className="flex justify-between text-[13px]">
              <span className="text-[#6b7280]">Lender</span>
              <span className="font-medium text-[#1a1d23]">{loan?.lender_name}</span>
            </div>
            <div className="flex justify-between text-[13px]">
              <span className="text-[#6b7280]">Created</span>
              <span className="font-medium text-[#1a1d23]">
                {loan?.created_at
                  ? new Date(loan.created_at).toLocaleDateString("en-IN", {
                      day: "2-digit",
                      month: "short",
                      year: "numeric",
                    })
                  : "—"}
              </span>
            </div>
          </div>
        </div>

        <div className="card p-5 space-y-4">
          <h3 className="text-[14px] font-semibold text-[#1a1d23] flex items-center gap-2">
            <Banknote className="h-4 w-4 text-[#0d9f6e]" />
            Manual Terms
          </h3>
          {terms ? (
            <div className="space-y-3">
              <div className="flex justify-between text-[13px]">
                <span className="text-[#6b7280]">Principal</span>
                <span className="font-medium text-[#1a1d23]">₹{terms.principal?.toLocaleString("en-IN")}</span>
              </div>
              <div className="flex justify-between text-[13px]">
                <span className="text-[#6b7280]">Disclosed Rate</span>
                <span className="font-medium text-[#1a1d23]">{terms.disclosed_rate}% p.a.</span>
              </div>
              <div className="flex justify-between text-[13px]">
                <span className="text-[#6b7280]">Tenure</span>
                <span className="font-medium text-[#1a1d23]">{terms.tenure_months} months</span>
              </div>
              <div className="flex justify-between text-[13px]">
                <span className="text-[#6b7280]">Fees</span>
                <span className="font-medium text-[#1a1d23]">₹{terms.fees?.toLocaleString("en-IN")}</span>
              </div>
            </div>
          ) : (
            <p className="text-[13px] text-[#9ca3af] italic">No manual terms recorded.</p>
          )}
        </div>
      </div>

      {/* Actions */}
      <div className="card p-5">
        <h3 className="text-[14px] font-semibold text-[#1a1d23] mb-4">Quick Actions</h3>
        <div className="flex flex-wrap gap-3">
          <button onClick={handleRunPipeline} disabled={analyzing} className="btn-primary text-[13px]">
            {analyzing ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Running Pipeline...
              </>
            ) : (
              <>
                <RefreshCw className="h-4 w-4" />
                Run Full Analysis
              </>
            )}
          </button>
          <Link href={`/chat?loan_id=${loanId}`} className="btn-secondary text-[13px]">
            <MessageCircle className="h-4 w-4" />
            AI Advisor Chat
          </Link>
          <Link href={`/disputes?loan_id=${loanId}`} className="btn-secondary text-[13px]">
            <Scale className="h-4 w-4" />
            File Dispute
          </Link>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="flex items-center gap-2 p-3.5 rounded-xl bg-[#fef2f2] border border-[#fecaca] text-[12px] text-[#991b1b]">
          <AlertTriangle className="h-4 w-4 shrink-0" />
          {error}
        </div>
      )}

      {/* Pipeline Results (if available) */}
      {pipelineResult && (
        <div className="space-y-5">
          {/* Compliance Banner */}
          <div
            className={`card-elevated p-5 flex items-start gap-3 ${
              pipelineResult.is_fully_compliant
                ? "border-[#a7f3d0] bg-gradient-to-r from-[#ecfdf5] to-white"
                : "border-[#fecaca] bg-gradient-to-r from-[#fef2f2] to-white"
            }`}
          >
            {pipelineResult.is_fully_compliant ? (
              <CheckCircle2 className="h-6 w-6 text-[#0d9f6e] shrink-0" />
            ) : (
              <AlertTriangle className="h-6 w-6 text-[#dc2626] shrink-0" />
            )}
            <div>
              <h3
                className={`text-[15px] font-bold ${
                  pipelineResult.is_fully_compliant ? "text-[#065f46]" : "text-[#991b1b]"
                }`}
              >
                {pipelineResult.is_fully_compliant
                  ? "Audit Passed — Fully Compliant"
                  : "Regulatory Violations Detected"}
              </h3>
              <p className="text-[12px] text-[#6b7280] mt-1">{pipelineResult.summary}</p>
              <span className="badge-neutral text-[10px] mt-2 inline-flex items-center gap-1">
                <Clock className="h-3 w-3" />
                {pipelineResult.total_duration_ms?.toFixed(0)}ms
              </span>
            </div>
          </div>

          {/* APR Result */}
          {apr && (
            <div className="card p-5">
              <h4 className="text-[13px] font-semibold text-[#1a1d23] mb-3 flex items-center gap-2">
                <TrendingUp className="h-4 w-4 text-[#0052cc]" />
                APR Recomputation
              </h4>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <div className="bg-[#f9fafb] p-3 rounded-xl border border-[#f0f0f0] text-center">
                  <p className="text-[10px] text-[#9ca3af]">Disclosed</p>
                  <p className="text-[16px] font-bold text-[#1a1d23]">{apr.disclosed_rate}%</p>
                </div>
                <div className="bg-[#f9fafb] p-3 rounded-xl border border-[#f0f0f0] text-center">
                  <p className="text-[10px] text-[#9ca3af]">True APR</p>
                  <p className="text-[16px] font-bold text-[#0052cc]">{apr.recomputed_apr?.toFixed(2)}%</p>
                </div>
                <div className="bg-[#f9fafb] p-3 rounded-xl border border-[#f0f0f0] text-center">
                  <p className="text-[10px] text-[#9ca3af]">EMI</p>
                  <p className="text-[16px] font-bold text-[#1a1d23]">₹{apr.monthly_emi?.toLocaleString("en-IN")}</p>
                </div>
                <div className="bg-[#f9fafb] p-3 rounded-xl border border-[#f0f0f0] text-center">
                  <p className="text-[10px] text-[#9ca3af]">Fee Impact</p>
                  <p className={`text-[16px] font-bold ${apr.fee_impact_apr > 0.05 ? "text-[#dc2626]" : "text-[#0d9f6e]"}`}>
                    +{apr.fee_impact_apr?.toFixed(2)}%
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Verified Claims */}
          {pipelineResult.verified_claims?.length > 0 && (
            <div className="card overflow-hidden">
              <div className="px-5 py-3 border-b border-[#e5e7eb] bg-[#f9fafb] flex items-center justify-between">
                <h4 className="text-[13px] font-semibold text-[#1a1d23]">Verified Claims</h4>
                <span className="badge-info text-[10px]">{pipelineResult.verified_claims.length} Claims</span>
              </div>
              <div className="divide-y divide-[#f0f0f0]">
                {pipelineResult.verified_claims.map((c: any, i: number) => (
                  <div key={c.claim_id || i} className="px-5 py-3 flex items-start gap-3">
                    {c.verification_status === "grounded" ? (
                      <CheckCircle2 className="h-4 w-4 text-[#0d9f6e] shrink-0 mt-0.5" />
                    ) : (
                      <AlertTriangle className="h-4 w-4 text-[#dc2626] shrink-0 mt-0.5" />
                    )}
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="badge-neutral text-[9px] uppercase font-mono">{c.source_module}</span>
                        <span className={`text-[9px] font-semibold uppercase px-1.5 py-0.5 rounded-full ${
                          c.verification_status === "grounded" ? "badge-success" : "badge-danger"
                        }`}>
                          {c.verification_status}
                        </span>
                      </div>
                      <p className="text-[12px] text-[#374151] leading-relaxed">{c.claim_text}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
