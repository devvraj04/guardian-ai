"use client";

import { useState, useEffect, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { api } from "@/lib/api";
import {
  Scale,
  ShieldAlert,
  Clock,
  CheckCircle2,
  AlertTriangle,
  Send,
  Loader2,
  FileText,
  ArrowLeft,
  Info,
  Search,
} from "lucide-react";
import Link from "next/link";

function DisputesContent() {
  const searchParams = useSearchParams();
  const initialLoanId = searchParams.get("loan_id") || "";

  const [loanId, setLoanId] = useState(initialLoanId);
  const [disputes, setDisputes] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Form State
  const [freeText, setFreeText] = useState("");
  const [categoryOverride, setCategoryOverride] = useState("");
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  const fetchDisputes = async (targetLoanId: string) => {
    if (!targetLoanId.trim()) return;
    try {
      setLoading(true);
      setError(null);
      const res = await api.getDisputes(targetLoanId);
      const list = Array.isArray(res)
        ? res
        : res?.disputes || res?.items || [];
      setDisputes(Array.isArray(list) ? list : []);
    } catch (e: any) {
      setError(e.message || "Failed to load disputes.");
      setDisputes([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (initialLoanId) {
      fetchDisputes(initialLoanId);
    }
  }, [initialLoanId]);

  const handleSubmitDispute = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!loanId.trim()) {
      setError("Please specify a Loan ID.");
      return;
    }
    if (freeText.trim().length < 10) {
      setError("Description must be at least 10 characters.");
      return;
    }

    try {
      setSubmitting(true);
      setError(null);
      setSuccessMsg(null);

      const payload: { free_text: string; category_override?: string } = {
        free_text: freeText.trim(),
      };
      if (categoryOverride) {
        payload.category_override = categoryOverride;
      }

      await api.createDispute(loanId, payload);
      setSuccessMsg(
        "Dispute successfully classified and registered under RBI Master Directions."
      );
      setFreeText("");
      setCategoryOverride("");
      fetchDisputes(loanId);
    } catch (err: any) {
      setError(err.message || "Failed to submit dispute.");
    } finally {
      setSubmitting(false);
    }
  };

  const categoryLabels: Record<string, string> = {
    excessive_charges_and_hidden_fees: "Excessive Charges & Hidden Fees",
    recovery_harassment_and_privacy: "Recovery Harassment & Privacy",
    unauthorized_disbursal_or_credit_limit: "Unauthorized Disbursal",
    transparency_and_kfs_violation: "Transparency & KFS Violation",
    repayment_and_noc_delay: "Repayment & NOC Delay",
    general_service_deficiency: "General Service Deficiency",
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6 animate-fade-in">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2 mb-1">
          <span className="section-label">Grievance Redressal</span>
        </div>
        <h1 className="text-xl font-bold text-[#1a1d23]">
          RBI Dispute & Complaint Filing
        </h1>
        <p className="text-[13px] text-[#6b7280] mt-0.5">
          AI-powered classification of complaints into RBI Digital Lending categories with mandated resolution tracking
        </p>
      </div>

      {/* Loan Selector */}
      <div className="card p-4 flex flex-col md:flex-row gap-3 items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="h-9 w-9 rounded-lg bg-[#fffbeb] flex items-center justify-center">
            <Search className="h-4 w-4 text-[#d97706]" />
          </div>
          <div>
            <p className="text-[13px] font-semibold text-[#1a1d23]">
              Target Loan Session
            </p>
            <p className="text-[11px] text-[#9ca3af]">
              View or file disputes for a specific loan
            </p>
          </div>
        </div>
        <div className="flex gap-2 w-full md:w-auto">
          <input
            type="text"
            placeholder="Loan session ID..."
            value={loanId}
            onChange={(e) => setLoanId(e.target.value)}
            className="input-field flex-1 md:w-72 font-mono text-[13px]"
          />
          <button
            onClick={() => fetchDisputes(loanId)}
            disabled={!loanId.trim() || loading}
            className="btn-secondary text-[13px]"
          >
            {loading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              "Load"
            )}
          </button>
        </div>
      </div>

      {/* Alerts */}
      {error && (
        <div className="flex items-center gap-2 p-3.5 rounded-xl bg-[#fef2f2] border border-[#fecaca] text-[12px] text-[#991b1b] animate-fade-in">
          <ShieldAlert className="h-4 w-4 shrink-0" />
          {error}
        </div>
      )}

      {successMsg && (
        <div className="flex items-center gap-2 p-3.5 rounded-xl bg-[#ecfdf5] border border-[#a7f3d0] text-[12px] text-[#065f46] animate-fade-in">
          <CheckCircle2 className="h-4 w-4 shrink-0" />
          {successMsg}
        </div>
      )}

      {/* File Complaint Form */}
      <form onSubmit={handleSubmitDispute} className="card p-6 space-y-5">
        <div>
          <h3 className="text-[14px] font-semibold text-[#1a1d23]">
            File a Formal Complaint
          </h3>
          <p className="text-[12px] text-[#6b7280] mt-0.5">
            Describe the lender infraction. Our classifier will categorize it per
            RBI Digital Lending Guidelines and assign a resolution timeline.
          </p>
        </div>

        <div>
          <label className="block text-[13px] font-medium text-[#374151] mb-2">
            Complaint Description
          </label>
          <textarea
            required
            rows={4}
            value={freeText}
            onChange={(e) => setFreeText(e.target.value)}
            placeholder="e.g. The lender debited an undisclosed upfront processing fee of ₹4,500 that was completely absent from the signed Key Fact Statement..."
            className="input-field resize-none leading-relaxed"
          />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-[13px] font-medium text-[#374151] mb-2">
              Category (Optional Override)
            </label>
            <select
              value={categoryOverride}
              onChange={(e) => setCategoryOverride(e.target.value)}
              className="input-field text-[13px]"
            >
              <option value="">Auto-Detect (Recommended)</option>
              <option value="excessive_charges_and_hidden_fees">
                Excessive Charges & Hidden Fees
              </option>
              <option value="recovery_harassment_and_privacy">
                Recovery Harassment & Privacy
              </option>
              <option value="unauthorized_disbursal_or_credit_limit">
                Unauthorized Disbursal / Limit Increase
              </option>
              <option value="transparency_and_kfs_violation">
                Transparency & KFS Violation
              </option>
              <option value="repayment_and_noc_delay">
                Repayment & NOC Delay
              </option>
              <option value="general_service_deficiency">
                General Service Deficiency
              </option>
            </select>
          </div>

          <div className="flex items-end">
            <button
              type="submit"
              disabled={submitting || !freeText.trim() || !loanId.trim()}
              className="btn-primary w-full md:w-auto justify-center"
            >
              {submitting ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Classifying...
                </>
              ) : (
                <>
                  <Send className="h-4 w-4" />
                  Submit Complaint
                </>
              )}
            </button>
          </div>
        </div>

        {/* Disclaimer */}
        <div className="flex items-start gap-2 p-3 rounded-lg bg-[#f9fafb] border border-[#e5e7eb] text-[11px] text-[#6b7280]">
          <Info className="h-3.5 w-3.5 shrink-0 mt-0.5 text-[#9ca3af]" />
          <span>
            Disputes are user-initiated only (RULES.md §6.3). They are never auto-generated.
            Each dispute is assigned a 30-day Turn Around Time per RBI guidelines.
          </span>
        </div>
      </form>

      {/* Disputes List */}
      <div className="card overflow-hidden">
        <div className="px-5 py-4 border-b border-[#e5e7eb] bg-[#f9fafb] flex items-center justify-between">
          <h3 className="text-[14px] font-semibold text-[#1a1d23]">
            Registered Disputes
          </h3>
          <span className="badge-neutral text-[11px]">
            {disputes.length} {disputes.length === 1 ? "Dispute" : "Disputes"}
          </span>
        </div>

        {!Array.isArray(disputes) || disputes.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-14 text-center">
            <div className="h-12 w-12 rounded-2xl bg-[#f3f4f6] flex items-center justify-center mb-3">
              <Scale className="h-6 w-6 text-[#9ca3af]" />
            </div>
            <p className="text-[13px] font-medium text-[#6b7280]">
              {loanId
                ? "No disputes recorded for this loan"
                : "Load a loan session to view disputes"}
            </p>
            <p className="text-[12px] text-[#9ca3af] mt-0.5">
              Filed disputes will appear here with tracking status
            </p>
          </div>
        ) : (
          <div className="divide-y divide-[#f0f0f0]">
            {disputes.map((d: any) => (
              <div
                key={d.id}
                className="px-5 py-4 space-y-3 hover:bg-[#f9fafb] transition-colors"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="text-[13px] font-semibold text-[#1a1d23]">
                      {categoryLabels[d.category] ||
                        d.category_label ||
                        d.category}
                    </span>
                    <span className="badge-info text-[10px]">
                      Confidence:{" "}
                      {d.confidence
                        ? (d.confidence * 100).toFixed(0) + "%"
                        : "—"}
                    </span>
                  </div>
                  <div className="badge-warning text-[11px] flex items-center gap-1">
                    <Clock className="h-3 w-3" />
                    TAT: {d.redressal_tat_days || 30} Days
                  </div>
                </div>

                <p className="text-[13px] text-[#374151] bg-[#f9fafb] p-3 rounded-lg border border-[#f0f0f0] leading-relaxed italic">
                  &ldquo;{d.free_text}&rdquo;
                </p>

                <div className="flex items-center justify-between text-[11px] text-[#9ca3af]">
                  <div className="flex items-center gap-1.5">
                    <FileText className="h-3.5 w-3.5" />
                    <span>
                      Citation:{" "}
                      <strong className="text-[#6b7280]">
                        {d.rbi_clause_reference ||
                          "RBI Digital Lending Guidelines §4"}
                      </strong>
                    </span>
                  </div>
                  <span className="font-mono text-[10px]">
                    ID: {d.id?.slice(0, 8)}...
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default function DisputesPage() {
  return (
    <Suspense
      fallback={
        <div className="flex items-center justify-center p-12">
          <Loader2 className="h-5 w-5 animate-spin text-[#0052cc]" />
        </div>
      }
    >
      <DisputesContent />
    </Suspense>
  );
}
