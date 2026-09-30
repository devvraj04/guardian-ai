"use client";

import { useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import {
  Upload,
  ArrowRight,
  ArrowLeft,
  Loader2,
  CheckCircle2,
  ShieldAlert,
  AlertTriangle,
  FileText,
  Building2,
  Banknote,
  Percent,
  Calendar,
  Languages,
  MessageCircle,
  Scale,
  ShieldCheck,
  Info,
  Download,
  Zap,
  Clock,
  TrendingUp,
  XCircle,
  DollarSign,
  BarChart3,
  Globe,
} from "lucide-react";
import LoanAnalytics from "@/components/LoanAnalytics";

export default function NewAnalysis() {
  const [loanId, setLoanId] = useState<string | null>(null);
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Step 1: Loan Profile & Terms
  const [loanName, setLoanName] = useState("Housing Finance Loan");
  const [lenderName, setLenderName] = useState("Bandhan Bank");
  const [principal, setPrincipal] = useState("2500000");
  const [disclosedRate, setDisclosedRate] = useState("8.75");
  const [tenureMonths, setTenureMonths] = useState("240");
  const [fees, setFees] = useState("9250");

  // Step 2: Documents & Settings
  const [tncFile, setTncFile] = useState<File | null>(null);
  const [kfsFile, setKfsFile] = useState<File | null>(null);
  const [targetLanguage, setTargetLanguage] = useState<string>("");
  const [monthlyIncome, setMonthlyIncome] = useState("85000");
  const [existingObligations, setExistingObligations] = useState("10000");

  // Step 3: Results
  const [pipelineResult, setPipelineResult] = useState<any>(null);

  const applyBandhanBankPreset = () => {
    setLoanName("Housing Finance Loan");
    setLenderName("Bandhan Bank");
    setPrincipal("2500000");
    setDisclosedRate("8.75");
    setTenureMonths("240");
    setFees("9250");
    setMonthlyIncome("85000");
    setExistingObligations("10000");
  };

  const handleCreateLoan = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setLoading(true);
      setError(null);
      const res = await api.createLoan({
        loan_name: loanName.trim(),
        lender_name: lenderName.trim(),
      });
      const newLoanId = res.id;
      setLoanId(newLoanId);

      if (principal && disclosedRate && tenureMonths) {
        await api.saveTerms(newLoanId, {
          principal: parseFloat(principal),
          disclosed_rate: parseFloat(disclosedRate),
          tenure_months: parseInt(tenureMonths, 10),
          fees: parseFloat(fees || "0"),
        });
      }

      setStep(2);
    } catch (err: any) {
      setError(err.message || "Failed to initialize loan profile");
    } finally {
      setLoading(false);
    }
  };

  const handleUploadAndAnalyze = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!loanId || (!tncFile && !kfsFile)) {
      setError("Please upload at least the Key Fact Statement (KFS) document to proceed.");
      return;
    }

    try {
      setLoading(true);
      setError(null);
      if (tncFile) {
        await api.uploadDocument(loanId, "tnc", tncFile);
      }
      if (kfsFile) {
        await api.uploadDocument(loanId, "kfs", kfsFile);
      }
      const result = await api.runPipeline(loanId, {
        target_language: targetLanguage || undefined,
      });
      setPipelineResult(result);
      setStep(3);
    } catch (err: any) {
      setError(err.message || "Pipeline execution failed.");
    } finally {
      setLoading(false);
    }
  };

  const loadSamplePdfs = async () => {
    try {
      setLoading(true);
      setError(null);
      const [tncRes, kfsRes] = await Promise.all([
        fetch("/sample_tnc.pdf"),
        fetch("/sample_kfs.pdf"),
      ]);
      const tncBlob = await tncRes.blob();
      const kfsBlob = await kfsRes.blob();
      setTncFile(new File([tncBlob], "sample_tnc.pdf", { type: "application/pdf" }));
      setKfsFile(new File([kfsBlob], "sample_kfs.pdf", { type: "application/pdf" }));
    } catch (e: any) {
      setError("Failed to load sample PDFs: " + e.message);
    } finally {
      setLoading(false);
    }
  };

  const steps = [
    { num: 1, label: "Loan Details" },
    { num: 2, label: "Documents" },
    { num: 3, label: "Verification Report" },
    { num: 4, label: "Serviceability & Simulator" },
  ];

  // Helper to get APR result (correct API field name)
  const apr = pipelineResult?.apr_result;
  const svc = pipelineResult?.serviceability_result;
  const cons = pipelineResult?.consistency_result;
  const vern = pipelineResult?.vernacular_translations;
  const kfs = pipelineResult?.extracted_kfs || {};

  return (
    <div className="max-w-4xl mx-auto space-y-6 animate-fade-in">
      {/* ─── Page Header ─── */}
      <div>
        <div className="flex items-center gap-2 mb-1">
          <span className="section-label">New Verification</span>
        </div>
        <h1 className="text-xl font-bold text-[#1a1d23]">
          Loan Compliance Analysis
        </h1>
        <p className="text-[13px] text-[#6b7280] mt-1">
          End-to-end verification of loan terms against RBI Master Directions
        </p>
      </div>

      {/* ─── Stepper ─── */}
      <div className="card p-4">
        <div className="flex items-center justify-between">
          {steps.map((s, i) => {
            const isClickable = (pipelineResult && s.num >= 3) || (loanId && s.num === 2) || s.num === 1;
            return (
              <div key={s.num} className="flex items-center flex-1">
                <button
                  type="button"
                  disabled={!isClickable}
                  onClick={() => isClickable && setStep(s.num)}
                  className={`flex items-center gap-2.5 text-left transition-opacity ${
                    isClickable ? "cursor-pointer hover:opacity-85" : "cursor-default opacity-80"
                  }`}
                >
                  <div
                    className={`h-8 w-8 rounded-full flex items-center justify-center text-[13px] font-bold transition-all ${
                      step >= s.num
                        ? "bg-[#0052cc] text-white shadow-sm shadow-blue-200"
                        : "bg-[#f3f4f6] text-[#9ca3af]"
                    }`}
                  >
                    {step > s.num ? (
                      <CheckCircle2 className="h-4 w-4" />
                    ) : (
                      s.num
                    )}
                  </div>
                  <span
                    className={`text-[12px] font-medium hidden sm:inline ${
                      step === s.num ? "text-[#0052cc] font-bold" : step > s.num ? "text-[#1a1d23]" : "text-[#9ca3af]"
                    }`}
                  >
                    {s.label}
                  </span>
                </button>
                {i < steps.length - 1 && (
                  <div className="flex-1 mx-3">
                    <div
                      className={`h-[2px] rounded-full transition-colors ${
                        step > s.num ? "bg-[#0052cc]" : "bg-[#e5e7eb]"
                      }`}
                    />
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* ─── Error Alert ─── */}
      {error && (
        <div className="flex items-start gap-3 p-4 rounded-xl bg-[#fef2f2] border border-[#fecaca] animate-fade-in">
          <ShieldAlert className="h-5 w-5 text-[#dc2626] shrink-0 mt-0.5" />
          <div>
            <h4 className="text-[13px] font-semibold text-[#991b1b]">Error</h4>
            <p className="text-[12px] text-[#b91c1c] mt-0.5">{error}</p>
          </div>
        </div>
      )}

      {/* ═══════ STEP 1: LOAN DETAILS ═══════ */}
      {step === 1 && (
        <form onSubmit={handleCreateLoan} className="card p-6 space-y-6 animate-slide-up">
          <div>
            <h2 className="text-[15px] font-semibold text-[#1a1d23]">
              Loan Product & Manual Terms
            </h2>
            <p className="text-[12px] text-[#6b7280] mt-0.5">
              Enter baseline loan details. These will be cross-verified against
              document-extracted data.
            </p>
          </div>

          {/* Universal RBI KFS Presets */}
          <div className="p-4 rounded-xl bg-gradient-to-r from-[#eff6ff] to-[#f8fafc] border border-[#bfdbfe] space-y-2.5">
            <div className="flex items-center justify-between flex-wrap gap-2">
              <div className="flex items-center gap-2">
                <Scale className="h-4 w-4 text-[#0052cc]" />
                <span className="text-[12px] font-bold text-[#1e40af]">
                  Standard RBI Loan Presets:
                </span>
                <span className="text-[11px] text-[#6b7280]">
                  Pre-load standard terms to test against any bank's Key Fact Statement
                </span>
              </div>
            </div>
            <div className="flex items-center flex-wrap gap-2">
              <button
                type="button"
                onClick={() => {
                  setLoanName("Housing Finance Loan");
                  setLenderName("Housing Finance / Commercial Bank");
                  setPrincipal("2500000");
                  setDisclosedRate("8.75");
                  setTenureMonths("240");
                  setFees("9250");
                  setMonthlyIncome("85000");
                  setExistingObligations("10000");
                }}
                className="text-[11px] font-semibold bg-white text-[#1e40af] border border-[#bfdbfe] px-3 py-1.5 rounded-lg hover:bg-[#eff6ff] transition-all shadow-xs"
              >
                🏠 Housing Loan (₹25L @ 8.75%, 20Y)
              </button>
              <button
                type="button"
                onClick={() => {
                  setLoanName("Personal Loan");
                  setLenderName("Scheduled Commercial Bank");
                  setPrincipal("500000");
                  setDisclosedRate("13.5");
                  setTenureMonths("36");
                  setFees("2500");
                  setMonthlyIncome("60000");
                  setExistingObligations("5000");
                }}
                className="text-[11px] font-semibold bg-white text-[#1e40af] border border-[#bfdbfe] px-3 py-1.5 rounded-lg hover:bg-[#eff6ff] transition-all shadow-xs"
              >
                💼 Personal Loan (₹5L @ 13.5%, 3Y)
              </button>
              <button
                type="button"
                onClick={() => {
                  setLoanName("Digital Instant Loan");
                  setLenderName("Digital Lending NBFC");
                  setPrincipal("100000");
                  setDisclosedRate("18.0");
                  setTenureMonths("12");
                  setFees("1500");
                  setMonthlyIncome("45000");
                  setExistingObligations("2000");
                }}
                className="text-[11px] font-semibold bg-white text-[#1e40af] border border-[#bfdbfe] px-3 py-1.5 rounded-lg hover:bg-[#eff6ff] transition-all shadow-xs"
              >
                📱 Digital Loan (₹1L @ 18.0%, 1Y)
              </button>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            <div>
              <label className="flex items-center gap-1.5 text-[13px] font-medium text-[#374151] mb-2">
                <FileText className="h-3.5 w-3.5 text-[#6b7280]" />
                Loan Offer Title
              </label>
              <input
                type="text"
                required
                value={loanName}
                onChange={(e) => setLoanName(e.target.value)}
                placeholder="e.g. HDFC Express Loan"
                className="input-field"
              />
            </div>
            <div>
              <label className="flex items-center gap-1.5 text-[13px] font-medium text-[#374151] mb-2">
                <Building2 className="h-3.5 w-3.5 text-[#6b7280]" />
                Lender / Bank
              </label>
              <input
                type="text"
                required
                value={lenderName}
                onChange={(e) => setLenderName(e.target.value)}
                placeholder="e.g. HDFC Bank Ltd."
                className="input-field"
              />
            </div>
            <div>
              <label className="flex items-center gap-1.5 text-[13px] font-medium text-[#374151] mb-2">
                <Banknote className="h-3.5 w-3.5 text-[#6b7280]" />
                Principal Amount (₹)
              </label>
              <input
                type="number"
                required
                min="1000"
                step="500"
                value={principal}
                onChange={(e) => setPrincipal(e.target.value)}
                className="input-field"
              />
            </div>
            <div>
              <label className="flex items-center gap-1.5 text-[13px] font-medium text-[#374151] mb-2">
                <Percent className="h-3.5 w-3.5 text-[#6b7280]" />
                Disclosed Interest Rate (% p.a.)
              </label>
              <input
                type="number"
                required
                step="0.01"
                min="0.1"
                max="100"
                value={disclosedRate}
                onChange={(e) => setDisclosedRate(e.target.value)}
                className="input-field"
              />
            </div>
            <div>
              <label className="flex items-center gap-1.5 text-[13px] font-medium text-[#374151] mb-2">
                <Calendar className="h-3.5 w-3.5 text-[#6b7280]" />
                Tenure (Months)
              </label>
              <input
                type="number"
                required
                min="1"
                max="360"
                value={tenureMonths}
                onChange={(e) => setTenureMonths(e.target.value)}
                className="input-field"
              />
            </div>
            <div>
              <label className="flex items-center gap-1.5 text-[13px] font-medium text-[#374151] mb-2">
                <Banknote className="h-3.5 w-3.5 text-[#6b7280]" />
                Upfront Fees & Charges (₹)
              </label>
              <input
                type="number"
                min="0"
                step="100"
                value={fees}
                onChange={(e) => setFees(e.target.value)}
                className="input-field"
              />
            </div>
          </div>

          <div className="pt-4 border-t border-[#e5e7eb] flex justify-end">
            <button type="submit" disabled={loading} className="btn-primary">
              {loading ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Creating Session...
                </>
              ) : (
                <>
                  Initialize Session
                  <ArrowRight className="h-4 w-4" />
                </>
              )}
            </button>
          </div>
        </form>
      )}

      {/* ═══════ STEP 2: DOCUMENT UPLOAD ═══════ */}
      {step === 2 && (
        <form onSubmit={handleUploadAndAnalyze} className="space-y-5 animate-slide-up">
          {/* Session Info Bar */}
          <div className="card p-4 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="h-9 w-9 rounded-lg bg-[#ecfdf5] flex items-center justify-center">
                <CheckCircle2 className="h-4.5 w-4.5 text-[#0d9f6e]" />
              </div>
              <div>
                <p className="text-[13px] font-semibold text-[#1a1d23]">
                  Session Created Successfully
                </p>
                <p className="text-[11px] text-[#9ca3af] font-mono">
                  ID: {loanId}
                </p>
              </div>
            </div>
            <span className="badge-success text-[11px]">Active</span>
          </div>

          {/* Sample PDF Bar */}
          <div className="flex items-center justify-between gap-4 p-4 rounded-xl bg-[#e8f0fe] border border-[#bfdbfe]">
            <div className="flex items-center gap-2.5">
              <Info className="h-4 w-4 text-[#0052cc] shrink-0" />
              <div>
                <p className="text-[12px] font-semibold text-[#1e40af]">
                  Quick Test with Sample RBI Documents
                </p>
                <p className="text-[11px] text-[#3b82f6]">
                  Auto-load pre-built T&C and KFS PDFs for immediate pipeline testing.
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2 shrink-0">
              <a
                href="/sample_tnc.pdf"
                download="sample_tnc.pdf"
                className="btn-ghost text-[11px] py-1.5 px-3 border border-[#bfdbfe]"
              >
                <Download className="h-3.5 w-3.5" />
                T&C
              </a>
              <a
                href="/sample_kfs.pdf"
                download="sample_kfs.pdf"
                className="btn-ghost text-[11px] py-1.5 px-3 border border-[#bfdbfe]"
              >
                <Download className="h-3.5 w-3.5" />
                KFS
              </a>
              <button
                type="button"
                onClick={loadSamplePdfs}
                className="inline-flex items-center gap-1.5 bg-[#0052cc] text-white font-semibold px-3 py-1.5 rounded-lg text-[11px] hover:bg-[#0747a6] transition-colors"
              >
                <Zap className="h-3.5 w-3.5" />
                Auto-Load Both
              </button>
            </div>
          </div>

          {/* Upload Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            {/* KFS Upload - PRIMARY */}
            <div className="card p-5 space-y-3 border-2 border-[#0d9f6e]/30 bg-[#f0fdf4]/30">
              <div className="flex items-center gap-2">
                <div className="h-8 w-8 rounded-lg bg-[#ecfdf5] flex items-center justify-center">
                  <FileText className="h-4 w-4 text-[#0d9f6e]" />
                </div>
                <div className="flex-1">
                  <div className="flex items-center justify-between">
                    <h3 className="text-[13px] font-semibold text-[#1a1d23]">
                      Key Fact Statement (KFS)
                    </h3>
                    <span className="badge-success text-[10px]">Required</span>
                  </div>
                  <p className="text-[11px] text-[#047857]">
                    Bandhan Bank / RBI Annexure A & B
                  </p>
                </div>
              </div>
              <div className="border-2 border-dashed border-[#a7f3d0] hover:border-[#0d9f6e] rounded-xl p-5 flex flex-col items-center justify-center text-center cursor-pointer transition-colors bg-white">
                <Upload className="h-6 w-6 text-[#0d9f6e] mb-2" />
                <input
                  type="file"
                  accept="application/pdf"
                  onChange={(e) => setKfsFile(e.target.files?.[0] || null)}
                  className="w-full text-[12px] text-[#6b7280] file:mr-3 file:py-1.5 file:px-3 file:rounded-lg file:border file:border-[#e5e7eb] file:text-[12px] file:font-medium file:bg-white file:text-[#374151] hover:file:bg-[#f3f4f6] cursor-pointer"
                />
                {kfsFile ? (
                  <p className="text-[12px] text-[#0d9f6e] font-semibold mt-2 flex items-center gap-1">
                    <CheckCircle2 className="h-3.5 w-3.5" />
                    {kfsFile.name}
                  </p>
                ) : (
                  <p className="text-[11px] text-[#9ca3af] mt-1">
                    Select Bandhan Bank KFS PDF (Housing Finance)
                  </p>
                )}
              </div>
            </div>

            {/* T&C Upload - OPTIONAL */}
            <div className="card p-5 space-y-3">
              <div className="flex items-center gap-2">
                <div className="h-8 w-8 rounded-lg bg-[#e8f0fe] flex items-center justify-center">
                  <FileText className="h-4 w-4 text-[#0052cc]" />
                </div>
                <div className="flex-1">
                  <div className="flex items-center justify-between">
                    <h3 className="text-[13px] font-semibold text-[#1a1d23]">
                      Terms & Conditions / Agreement
                    </h3>
                    <span className="badge-neutral text-[10px]">Optional</span>
                  </div>
                  <p className="text-[11px] text-[#9ca3af]">
                    For cross-document consistency checks
                  </p>
                </div>
              </div>
              <div className="border-2 border-dashed border-[#d1d5db] hover:border-[#0052cc] rounded-xl p-5 flex flex-col items-center justify-center text-center cursor-pointer transition-colors bg-[#f9fafb]">
                <Upload className="h-6 w-6 text-[#9ca3af] mb-2" />
                <input
                  type="file"
                  accept="application/pdf"
                  onChange={(e) => setTncFile(e.target.files?.[0] || null)}
                  className="w-full text-[12px] text-[#6b7280] file:mr-3 file:py-1.5 file:px-3 file:rounded-lg file:border file:border-[#e5e7eb] file:text-[12px] file:font-medium file:bg-white file:text-[#374151] hover:file:bg-[#f3f4f6] cursor-pointer"
                />
                {tncFile ? (
                  <p className="text-[12px] text-[#0d9f6e] font-medium mt-2 flex items-center gap-1">
                    <CheckCircle2 className="h-3.5 w-3.5" />
                    {tncFile.name}
                  </p>
                ) : (
                  <p className="text-[11px] text-[#9ca3af] mt-1">
                    Optional: Upload T&C if available
                  </p>
                )}
              </div>
            </div>
          </div>

          {/* Vernacular Language Selection & Workflow Notice */}
          <div className="card p-5 space-y-3">
            <div className="flex items-center justify-between flex-wrap gap-2">
              <label className="flex items-center gap-1.5 text-[13px] font-medium text-[#374151]">
                <Languages className="h-3.5 w-3.5 text-[#6b7280]" />
                Vernacular Declaration (Annexure D Languages)
              </label>
              <span className="badge-neutral text-[10px]">Optional</span>
            </div>
            <select
              value={targetLanguage}
              onChange={(e) => setTargetLanguage(e.target.value)}
              className="input-field w-full"
            >
              <option value="">English (Default)</option>
              <option value="hi">Hindi (हिंदी)</option>
              <option value="bn">Bengali (বাংলা) — Bandhan Bank Headquarter</option>
              <option value="mr">Marathi (मराठी)</option>
              <option value="gu">Gujarati (ગુજરાતી)</option>
              <option value="kn">Kannada (ಕನ್ನಡ)</option>
              <option value="te">Telugu (తెలుగు)</option>
              <option value="ta">Tamil (தமிழ்)</option>
              <option value="or">Odia (ଓଡ଼ିଆ)</option>
              <option value="pa">Punjabi (ਪੰਜਾਬੀ)</option>
              <option value="ml">Malayalam (മലയാളം)</option>
              <option value="as">Assamese (অসমীয়া)</option>
              <option value="ur">Urdu (اردو)</option>
            </select>
            <div className="p-3 rounded-xl bg-[#f8fafc] border border-[#e2e8f0] flex items-center justify-between gap-3 text-[11px] text-[#6b7280]">
              <div className="flex items-center gap-2">
                <Info className="h-4 w-4 text-[#0052cc] shrink-0" />
                <span>
                  <strong>Full Verification Report First:</strong> After clicking Execute, you will receive the complete compliance audit, calculation breakdown, and payoff graph. Serviceability and prepayment simulation are available right on the report screen.
                </span>
              </div>
            </div>
          </div>

          {/* Actions */}
          <div className="flex items-center justify-between pt-2">
            <button
              type="button"
              onClick={() => setStep(1)}
              className="btn-ghost"
            >
              <ArrowLeft className="h-4 w-4" />
              Back
            </button>
            <button
              type="submit"
              disabled={loading || (!tncFile && !kfsFile)}
              className="btn-primary"
            >
              {loading ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Running Verification Pipeline...
                </>
              ) : (
                <>
                  Execute Verification
                  <ArrowRight className="h-4 w-4" />
                </>
              )}
            </button>
          </div>
        </form>
      )}

      {/* ═══════ STEP 3: VERIFICATION REPORT ═══════ */}
      {step === 3 && pipelineResult && (
        <div className="space-y-5 animate-slide-up">
          {/* Compliance Banner */}
          <div
            className={`card-elevated p-6 flex items-start gap-4 ${
              pipelineResult.is_fully_compliant
                ? "border-[#a7f3d0] bg-gradient-to-r from-[#ecfdf5] to-white"
                : "border-[#fecaca] bg-gradient-to-r from-[#fef2f2] to-white"
            }`}
          >
            {pipelineResult.is_fully_compliant ? (
              <div className="h-12 w-12 rounded-xl bg-[#0d9f6e] flex items-center justify-center shrink-0 shadow-md shadow-green-200">
                <CheckCircle2 className="h-6 w-6 text-white" />
              </div>
            ) : (
              <div className="h-12 w-12 rounded-xl bg-[#dc2626] flex items-center justify-center shrink-0 shadow-md shadow-red-200">
                <AlertTriangle className="h-6 w-6 text-white" />
              </div>
            )}
            <div className="flex-1">
              <div className="flex items-center justify-between flex-wrap gap-2">
                <h3
                  className={`text-lg font-bold ${
                    pipelineResult.is_fully_compliant
                      ? "text-[#065f46]"
                      : "text-[#991b1b]"
                  }`}
                >
                  {pipelineResult.is_fully_compliant
                    ? "Audit Passed — Fully Compliant"
                    : "Regulatory Violations Detected"}
                </h3>
                <span className="badge-neutral text-[11px] flex items-center gap-1">
                  <Clock className="h-3 w-3" />
                  {pipelineResult.total_duration_ms?.toFixed(0) || "—"} ms
                </span>
              </div>
              <p className="text-[13px] text-[#6b7280] mt-1.5 leading-relaxed">
                {pipelineResult.summary}
              </p>
              {/* Warnings */}
              {pipelineResult.warnings?.length > 0 && (
                <div className="mt-3 space-y-2">
                  {pipelineResult.warnings.map((w: string, i: number) => (
                    <div
                      key={i}
                      className="flex items-center gap-2 p-2.5 rounded-lg bg-[#fffbeb] border border-[#fde68a] text-[12px] text-[#92400e]"
                    >
                      <AlertTriangle className="h-3.5 w-3.5 shrink-0" />
                      {w}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* ═══════ VERIFICATION CALCULATIONS & COMPLIANCE PROOFS ═══════ */}
          <LoanAnalytics
            kfs={kfs}
            apr={apr}
            pipelineResult={pipelineResult}
            loanId={loanId || undefined}
            lenderName={lenderName}
            loanName={loanName}
            mode="verification"
            onProceedToSimulator={() => setStep(4)}
          />

          {/* ═══════ UNIVERSAL RBI KEY FACT STATEMENT (KFS) SCHEDULE ═══════ */}
          <div className="card overflow-hidden border border-[#e5e7eb] shadow-sm">
            <div className="px-5 py-4 bg-gradient-to-r from-[#f8fafc] to-[#f1f5f9] border-b border-[#e5e7eb] flex items-center justify-between flex-wrap gap-2">
              <div className="flex items-center gap-2.5">
                <div className="h-8 w-8 rounded-lg bg-[#0052cc]/10 flex items-center justify-center">
                  <FileText className="h-4 w-4 text-[#0052cc]" />
                </div>
                <div>
                  <h4 className="text-[14px] font-bold text-[#1a1d23]">
                    Key Fact Statement (KFS) — Mandatory Disclosure Schedule
                  </h4>
                  <p className="text-[11px] text-[#6b7280]">
                    Standardized format prescribed by Reserve Bank of India (RBI/2024-25/18)
                  </p>
                </div>
              </div>
              <span className="badge-success text-[11px]">
                {kfs.bank_name || lenderName || "Regulated Entity"}
              </span>
            </div>

            {/* Part 1: Quantitative Disclosures */}
            <div className="p-5 space-y-4">
              <div className="flex items-center gap-1.5 text-[12px] font-bold text-[#1e40af] uppercase tracking-wider">
                <Banknote className="h-3.5 w-3.5" />
                Part 1: Interest Rate & Financial Charges
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
                <div className="p-3 rounded-xl bg-[#f9fafb] border border-[#f0f0f0]">
                  <p className="text-[11px] text-[#9ca3af] font-medium">1. Sanctioned Loan Amount</p>
                  <p className="text-[15px] font-bold text-[#1a1d23] mt-0.5">
                    ₹{(kfs.principal || apr?.principal || parseFloat(principal))?.toLocaleString("en-IN")}
                  </p>
                  <span className="text-[10px] text-[#059669] font-medium">Part 1 Item 2</span>
                </div>

                <div className="p-3 rounded-xl bg-[#f9fafb] border border-[#f0f0f0]">
                  <p className="text-[11px] text-[#9ca3af] font-medium">2. Loan Tenor</p>
                  <p className="text-[15px] font-bold text-[#1a1d23] mt-0.5">
                    {(kfs.tenure_months || apr?.tenure_months || parseInt(tenureMonths, 10))} Months
                  </p>
                  <span className="text-[10px] text-[#059669] font-medium">Part 1 Item 4</span>
                </div>

                <div className="p-3 rounded-xl bg-[#f9fafb] border border-[#f0f0f0]">
                  <p className="text-[11px] text-[#9ca3af] font-medium">3. Monthly EPI / EMI</p>
                  <p className="text-[15px] font-bold text-[#0052cc] mt-0.5">
                    ₹{(kfs.monthly_emi || apr?.monthly_emi)?.toLocaleString("en-IN") || "—"}
                  </p>
                  <span className="text-[10px] text-[#059669] font-medium">Part 1 Item 5 (EPI)</span>
                </div>

                <div className="p-3 rounded-xl bg-[#f9fafb] border border-[#f0f0f0]">
                  <p className="text-[11px] text-[#9ca3af] font-medium">4. Disclosed Interest Rate</p>
                  <p className="text-[15px] font-bold text-[#1a1d23] mt-0.5">
                    {(kfs.disclosed_rate || apr?.disclosed_rate || parseFloat(disclosedRate))}% p.a.
                  </p>
                  <span className="text-[10px] text-[#6b7280] font-medium">
                    {kfs.interest_type || "Floating / Fixed"} (Part 1 Item 6)
                  </span>
                </div>

                <div className="p-3 rounded-xl bg-[#f9fafb] border border-[#f0f0f0]">
                  <p className="text-[11px] text-[#9ca3af] font-medium">5. Upfront Fees & Charges</p>
                  <p className="text-[15px] font-bold text-[#1a1d23] mt-0.5">
                    ₹{(kfs.processing_fee ?? apr?.fees ?? parseFloat(fees))?.toLocaleString("en-IN")}
                  </p>
                  <span className="text-[10px] text-[#6b7280] font-medium">Itemized (Part 1 Item 8)</span>
                </div>

                <div className="p-3 rounded-xl bg-[#f9fafb] border border-[#f0f0f0]">
                  <p className="text-[11px] text-[#9ca3af] font-medium">6. Net Disbursed Amount</p>
                  <p className="text-[15px] font-bold text-[#0d9f6e] mt-0.5">
                    ₹{(kfs.net_disbursed_amount || apr?.disbursed_amount || ((kfs.principal || apr?.principal || parseFloat(principal)) - (kfs.processing_fee ?? apr?.fees ?? parseFloat(fees))))?.toLocaleString("en-IN")}
                  </p>
                  <span className="text-[10px] text-[#059669] font-medium">Annexure B Item 7</span>
                </div>

                <div className="p-3 rounded-xl bg-[#f9fafb] border border-[#f0f0f0]">
                  <p className="text-[11px] text-[#9ca3af] font-medium">7. True Annual Percentage Rate (APR)</p>
                  <p className="text-[15px] font-bold text-[#0052cc] mt-0.5">
                    {apr?.recomputed_apr ? `${apr.recomputed_apr.toFixed(2)}%` : `${kfs.apr || "—"}%`}
                  </p>
                  <span className="text-[10px] text-[#059669] font-medium">IRR on Net Disbursed</span>
                </div>

                <div className="p-3 rounded-xl bg-[#f9fafb] border border-[#f0f0f0]">
                  <p className="text-[11px] text-[#9ca3af] font-medium">8. Total Amount to be Repaid</p>
                  <p className="text-[15px] font-bold text-[#1a1d23] mt-0.5">
                    ₹{(kfs.total_repayment_amount || apr?.total_payment)?.toLocaleString("en-IN") || "—"}
                  </p>
                  <span className="text-[10px] text-[#6b7280] font-medium">Principal + Total Interest</span>
                </div>
              </div>

              {/* Part 2: Qualitative Disclosures & Regulatory Compliance */}
              <div className="pt-3 border-t border-[#e5e7eb] space-y-3">
                <div className="flex items-center gap-1.5 text-[12px] font-bold text-[#1e40af] uppercase tracking-wider">
                  <Scale className="h-3.5 w-3.5" />
                  Part 2: Contingent Charges & Regulatory Protections
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-[12px]">
                  {/* Prepayment Clause */}
                  <div className="p-3 rounded-xl bg-white border border-[#e5e7eb] space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-[#1a1d23]">Prepayment / Foreclosure Terms</span>
                      <span className="badge-success text-[10px]">RBI Compliant</span>
                    </div>
                    <p className="text-[#374151] text-[11px] leading-relaxed">
                      {kfs.prepayment_clause || "Floating rate term loans to individual borrowers carry NIL prepayment charges as per RBI mandate."}
                    </p>
                  </div>

                  {/* Penal Charges */}
                  <div className="p-3 rounded-xl bg-white border border-[#e5e7eb] space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-[#1a1d23]">Penal Charges on Default</span>
                      <span className="badge-neutral text-[10px]">Non-Compounding</span>
                    </div>
                    <p className="text-[#374151] text-[11px] leading-relaxed">
                      {kfs.penal_charges || "2.00% of overdue EMI amount + applicable GST. (No compounding penal interest permitted)."}
                    </p>
                  </div>

                  {/* Bounce Charges & Look-up */}
                  <div className="p-3 rounded-xl bg-white border border-[#e5e7eb] space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-[#1a1d23]">Bounce Charges & Cooling-Off Period</span>
                      <span className="badge-neutral text-[10px]">Statutory</span>
                    </div>
                    <p className="text-[#374151] text-[11px] leading-relaxed">
                      NACH / Cheque Bounce: ₹{kfs.bounce_charges ?? 500} + GST. Cooling-off: {kfs.cooling_off_period || "Look-up window allowed per Board policy"}.
                    </p>
                  </div>

                  {/* Nodal Grievance Contact */}
                  <div className="p-3 rounded-xl bg-white border border-[#e5e7eb] space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-[#1a1d23]">Grievance Redressal Nodal Officer</span>
                      <span className="badge-success text-[10px]">Escalation Contact</span>
                    </div>
                    <p className="text-[#374151] text-[11px] leading-relaxed font-mono">
                      Email: {kfs.grievance_email || "customercare@lender.bank"} | Tel: {kfs.grievance_phone || "1800-TollFree"}
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Consistency Check Card */}
          {cons && (
            <div className="card p-5 space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Scale className="h-4 w-4 text-[#be185d]" />
                  <h4 className="text-[14px] font-semibold text-[#1a1d23]">
                    3-Way Consistency Check
                  </h4>
                </div>
                <div className="flex items-center gap-2">
                  <span className="badge-success text-[10px]">{cons.match_count} Match</span>
                  {cons.mismatch_count > 0 && (
                    <span className="badge-danger text-[10px]">{cons.mismatch_count} Mismatch</span>
                  )}
                  {cons.missing_count > 0 && (
                    <span className="badge-warning text-[10px]">{cons.missing_count} Missing</span>
                  )}
                </div>
              </div>
              <div className="divide-y divide-[#f0f0f0] border border-[#e5e7eb] rounded-xl overflow-hidden">
                <div className="grid grid-cols-5 gap-0 bg-[#f9fafb] text-[10px] font-semibold text-[#6b7280] uppercase tracking-wider">
                  <div className="px-4 py-2.5">Field</div>
                  <div className="px-4 py-2.5">Manual</div>
                  <div className="px-4 py-2.5">T&C</div>
                  <div className="px-4 py-2.5">KFS</div>
                  <div className="px-4 py-2.5">Status</div>
                </div>
                {cons.checks?.map((c: any, i: number) => (
                  <div
                    key={i}
                    className={`grid grid-cols-5 gap-0 text-[12px] ${
                      c.match_status === "mismatch"
                        ? "bg-[#fef2f2]"
                        : c.match_status === "missing"
                        ? "bg-[#fffbeb]"
                        : "bg-white"
                    }`}
                  >
                    <div className="px-4 py-3 font-medium text-[#1a1d23]">
                      {c.field_name}
                    </div>
                    <div className="px-4 py-3 text-[#6b7280] font-mono">
                      {c.manual_value ?? "—"}
                    </div>
                    <div className="px-4 py-3 text-[#6b7280] font-mono">
                      {typeof c.tnc_value === "string" && c.tnc_value.length > 30
                        ? c.tnc_value.slice(0, 30) + "…"
                        : c.tnc_value ?? "—"}
                    </div>
                    <div className="px-4 py-3 text-[#6b7280] font-mono">
                      {typeof c.kfs_value === "string" && c.kfs_value.length > 30
                        ? c.kfs_value.slice(0, 30) + "…"
                        : c.kfs_value ?? "—"}
                    </div>
                    <div className="px-4 py-3">
                      <span
                        className={`text-[10px] font-semibold uppercase px-2 py-0.5 rounded-full ${
                          c.match_status === "match"
                            ? "badge-success"
                            : c.match_status === "mismatch"
                            ? "badge-danger"
                            : "badge-warning"
                        }`}
                      >
                        {c.match_status}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
              {cons.summary_explanation && (
                <p className="text-[12px] text-[#6b7280] leading-relaxed">
                  {cons.summary_explanation}
                </p>
              )}
            </div>
          )}

          {/* Vernacular Translation Card */}
          {vern && vern.length > 0 && (
            <div className="card p-5 space-y-4">
              <div className="flex items-center gap-2">
                <Globe className="h-4 w-4 text-[#7c3aed]" />
                <h4 className="text-[14px] font-semibold text-[#1a1d23]">
                  Vernacular Verification
                </h4>
              </div>
              <div className="space-y-3">
                {vern.map((v: any, i: number) => (
                  <div key={i} className="bg-[#f9fafb] p-4 rounded-xl border border-[#f0f0f0] space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="text-[12px] font-semibold text-[#1a1d23]">
                        {v.target_language === "hi" ? "Hindi (हिंदी)" : v.target_language === "mr" ? "Marathi (मराठी)" : v.target_language}
                      </span>
                      <span
                        className={`text-[10px] font-semibold uppercase px-2 py-0.5 rounded-full ${
                          v.verification_verdict === "grounded" ? "badge-success" : "badge-danger"
                        }`}
                      >
                        {v.verification_verdict}
                      </span>
                    </div>
                    <div className="space-y-2 text-[12px]">
                      <div>
                        <span className="text-[#9ca3af] text-[11px]">Translated:</span>
                        <p className="text-[#374151] mt-0.5">{v.translated_text}</p>
                      </div>
                      <div>
                        <span className="text-[#9ca3af] text-[11px]">Back-translated:</span>
                        <p className="text-[#374151] mt-0.5">{v.back_translated_text}</p>
                      </div>
                    </div>
                    {v.metrics && (
                      <div className="grid grid-cols-3 gap-2">
                        <div className="text-center p-2 bg-white rounded-lg border border-[#e5e7eb]">
                          <p className="text-[10px] text-[#9ca3af]">Numeric Preserved</p>
                          <p className="text-[13px] font-bold text-[#0d9f6e]">{v.metrics.numeric_preservation_rate}%</p>
                        </div>
                        <div className="text-center p-2 bg-white rounded-lg border border-[#e5e7eb]">
                          <p className="text-[10px] text-[#9ca3af]">Semantic Drift</p>
                          <p className="text-[13px] font-bold text-[#1a1d23]">{v.metrics.semantic_drift_score?.toFixed(3)}</p>
                        </div>
                        <div className="text-center p-2 bg-white rounded-lg border border-[#e5e7eb]">
                          <p className="text-[10px] text-[#9ca3af]">Clause Drop</p>
                          <p className="text-[13px] font-bold text-[#0d9f6e]">{v.metrics.clause_drop_rate}%</p>
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Verified Claims Table */}
          <div className="card overflow-hidden">
            <div className="px-5 py-4 border-b border-[#e5e7eb] flex items-center justify-between bg-[#f9fafb]">
              <div>
                <h4 className="text-[14px] font-semibold text-[#1a1d23]">
                  Verification Gate — Claim Analysis
                </h4>
                <p className="text-[11px] text-[#9ca3af] mt-0.5">
                  Each claim verified via RoBERTa-MNLI semantic + numeric check
                </p>
              </div>
              <span className="badge-info text-[11px]">
                {pipelineResult.verified_claims?.length || 0} Claims
              </span>
            </div>

            <div className="divide-y divide-[#f0f0f0]">
              {pipelineResult.verified_claims?.map(
                (claim: any, idx: number) => {
                  const isGrounded =
                    claim.verification_status === "grounded";
                  return (
                    <div
                      key={claim.claim_id || idx}
                      className="px-5 py-4 flex items-start gap-3.5 hover:bg-[#f9fafb] transition-colors"
                    >
                      <div className="mt-0.5">
                        {isGrounded ? (
                          <CheckCircle2 className="h-5 w-5 text-[#0d9f6e]" />
                        ) : (
                          <AlertTriangle className="h-5 w-5 text-[#dc2626]" />
                        )}
                      </div>
                      <div className="flex-1 space-y-2">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="badge-neutral text-[10px] uppercase font-mono">
                            {claim.source_module || "pipeline"}
                          </span>
                          <span
                            className={`text-[10px] font-semibold uppercase px-2 py-0.5 rounded-full ${
                              isGrounded
                                ? "badge-success"
                                : "badge-danger"
                            }`}
                          >
                            {claim.verification_status}
                          </span>
                          {claim.verification_result?.semantic_score !== undefined && (
                            <span className="text-[10px] text-[#9ca3af]">
                              Semantic: {(claim.verification_result.semantic_score * 100).toFixed(1)}%
                            </span>
                          )}
                        </div>
                        <p className="text-[13px] text-[#374151] leading-relaxed">
                          {claim.claim_text}
                        </p>
                        {claim.warning_message && (
                          <div className="flex items-center gap-2 p-3 rounded-lg bg-[#fef2f2] border border-[#fecaca] text-[12px] text-[#991b1b]">
                            <AlertTriangle className="h-3.5 w-3.5 shrink-0" />
                            {claim.warning_message}
                          </div>
                        )}
                      </div>
                    </div>
                  );
                }
              )}
            </div>
          </div>

          {/* Stage Timings */}
          {pipelineResult.timings?.length > 0 && (
            <div className="card p-5">
              <h4 className="text-[13px] font-semibold text-[#1a1d23] mb-3 flex items-center gap-2">
                <Clock className="h-4 w-4 text-[#6b7280]" />
                Pipeline Stage Timings
              </h4>
              <div className="flex flex-wrap gap-2">
                {pipelineResult.timings.map((t: any, i: number) => (
                  <div
                    key={i}
                    className="flex items-center gap-1.5 bg-[#f9fafb] border border-[#e5e7eb] px-3 py-1.5 rounded-lg text-[11px]"
                  >
                    <span className="font-medium text-[#374151]">
                      {t.stage?.replace(/_/g, " ")}
                    </span>
                    <span className="text-[#9ca3af] font-mono">
                      {t.duration_ms?.toFixed(0)}ms
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Action Footer */}
          <div className="flex flex-wrap items-center justify-between gap-3 pt-3 border-t border-[#e5e7eb]">
            <Link href="/" className="btn-ghost">
              <ArrowLeft className="h-4 w-4" />
              Back to Dashboard
            </Link>
            <div className="flex items-center gap-3">
              <Link
                href={`/disputes?loan_id=${loanId}`}
                className="btn-secondary"
              >
                <Scale className="h-4 w-4 text-[#d97706]" />
                File Dispute
              </Link>
              <Link
                href={`/chat?loan_id=${loanId}`}
                className="btn-secondary"
              >
                <MessageCircle className="h-4 w-4" />
                Chat with AI Advisor
              </Link>
              <button
                type="button"
                onClick={() => setStep(4)}
                className="btn-primary flex items-center gap-2 shadow-sm"
              >
                <span>Next: Serviceability & Simulator</span>
                <ArrowRight className="h-4 w-4" />
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ═══════ STEP 4: FINANCIAL SERVICEABILITY & AMORTIZATION SIMULATION ═══════ */}
      {step === 4 && pipelineResult && (
        <div className="space-y-6 animate-slide-up">
          {/* Section Breadcrumb Bar */}
          <div className="flex items-center justify-between flex-wrap gap-2 p-3 bg-white rounded-xl border border-[#e5e7eb]">
            <button
              type="button"
              onClick={() => setStep(3)}
              className="btn-ghost text-[12px] flex items-center gap-1.5 py-1 px-2.5 border border-[#e5e7eb]"
            >
              <ArrowLeft className="h-3.5 w-3.5" />
              Back to Verification Report
            </button>
            <div className="flex items-center gap-2">
              <span className="text-[12px] font-semibold text-[#1a1d23]">{loanName}</span>
              <span className="text-[#d1d5db]">·</span>
              <span className="badge-success text-[10px]">{lenderName}</span>
            </div>
          </div>

          {/* Dedicated Serviceability, Prepayment Simulator, Graph & Full Year-by-Year Table */}
          <LoanAnalytics
            kfs={kfs}
            apr={apr}
            pipelineResult={pipelineResult}
            loanId={loanId || undefined}
            lenderName={lenderName}
            loanName={loanName}
            mode="simulator"
          />

          {/* Step 4 Footer */}
          <div className="flex flex-wrap items-center justify-between gap-3 pt-3 border-t border-[#e5e7eb]">
            <button
              type="button"
              onClick={() => setStep(3)}
              className="btn-ghost"
            >
              <ArrowLeft className="h-4 w-4" />
              Back to Verification Report
            </button>
            <div className="flex items-center gap-3">
              <Link
                href={`/disputes?loan_id=${loanId}`}
                className="btn-secondary"
              >
                <Scale className="h-4 w-4 text-[#d97706]" />
                File Dispute
              </Link>
              <Link
                href={`/chat?loan_id=${loanId}`}
                className="btn-primary"
              >
                <MessageCircle className="h-4 w-4" />
                Chat with AI Advisor
              </Link>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
